## A module to work with AMIs for the purpose of debugging and updating.
import boto3
import sys
import time
import os
import re
import datetime
import json

def launch_default_ami(path):
    """
    This function reads the configuration file of a given pipeline, extracts the default ami, and launches it on the default instance type.

    Inputs:
    path (string): the path to the folder representing the pipeline that you would like to edit.
    """
    ## Get the configuration file from the current pipeline:
    config_filepath = 'stack_config_template.json'
    config_fullpath = os.path.join(path,config_filepath)
    ## Load in:
    with open(config_fullpath,'r') as f:
        config = json.load(f)
    ## Get ami id
    ami_id = config['Lambda']['LambdaConfig']['AMI']
    ## Get default instance type:
    instance_type = config['Lambda']['LambdaConfig']['INSTANCE_TYPE']
    ec2_resource = boto3.resource('ec2')
    out = ec2_resource.create_instances(ImageId=ami_id,
            InstanceType = instance_type,
            MinCount=1,
            MaxCount=1,
            DryRun=False,
            KeyName = "ta_testkey",
            SecurityGroups=['launch-wizard-34'],
            IamInstanceProfile={
                'Name':'ec2_ssm'})
    ## Now get the instance id:
    instance = out[0]
    ami_instance_id = instance.instance_id

    ## Wait until this thing is started:
    started = False
    while not started:
        instance.load()
        state = instance.state
        print("current state is: "+str(state))

        started = state['Name'] == 'running'
        time.sleep(1)
    print('initializing instance')
    time.sleep(60) ## We need to wait until the instance gets set up.
    response = "Instance {} is running"
    print(response.format(ami_instance_id))


def test_instance(instance_id,pipelinepath,submitpath):
    """
    Uses SSM manager to send a RunCommand document to a given instance, mimicking the way jobs would be sent to the instance by the user. Assumes that there is data at the S3 path referenced by the submit file that you give.


    Inputs:
    instance_id (str): the id of the instance (starts with i-) that you would like to send a command to. The instance must have ssm manager installed in order to run commands.
    pipelinepath (str): the path to the folder representing the pipeline that you would like to edit.
    submitpath (str): the path to the submit file that references data to be analyzed, and configurations to be used
    """

    ## Load in the json submit file:
    with open(submitpath,'r') as f:
        submit_config = json.load(f)
    data_filename = submit_config['filename']

    ## Load in the configuration file
    config_filepath = 'stack_config_template.json'
    config_fullpath = os.path.join(pipelinepath,config_filepath)
    ## Load in:
    with open(config_fullpath,'r') as f:
        config = json.load(f)

    ## Now get the command we want to send properly formatted:
    command_unformatted = config['Lambda']['LambdaConfig']['COMMAND']
    ## Get relevant parameters:
    bucketname_test = config['PipelineName']
    outdir = config['Lambda']['LambdaConfig']['OUTDIR']

    command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir)]
    working_directory = [config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
    timeout = [str(config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

    print('sending command: '+command_formatted[0] +' to instance '+instance_id)
    ## Get the ssm client:
    ssm_client = boto3.client('ssm',region_name = config['Lambda']['LambdaConfig']['REGION'])
    response = ssm_client.send_command(
        DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
        Parameters={'commands': command_formatted,
                    "workingDirectory":working_directory,
                    "executionTimeout":timeout},
        InstanceIds=[instance_id])
        #OutputS3BucketName=log_bucket_name,
        #OutputS3KeyPrefix=log_path
    #)
    commandid = response['Command']['CommandId']

    for i in range(30):
        updated = ssm_client.list_commands(CommandId=commandid)
        time.sleep(5)
        status = updated['Commands'][0]['Status']
        print(updated,status)

## New class to develop an ami.

class DevAMI(object):
    """
    This class streamlines the experience of developing an ami within an existing pipeline. It has three main functions:
    1) to launch a development instance from amis associated with a particular algorithm or pipeline,
    2) to test said amis with simulated job submission events, and
    3) to create new images once development instances are stable and ready for deployment.  

    The current instantiation of this class only allows for one development instance to be launched at a time to encourage responsible usage.

    Inputs:
    path (str): the path to the directory for a given pipeline.


    Example Usage:
    ```python
    devenv = DevAMI("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
    devenv.launch_ami() ## function 1 referenced above
    ### Do some development on the remote instance
    devenv.submit_job("/path/to/submit/file") ## function 2 referenced above
    ### Monitor the remote instance to make sure that everything is running as expected, outputs are returned
    devenv.create_devami("new_ami") ## function 3 referenced above
    devenv.terminate_devinstance() ## clean up after done developing
    ```
    """
    def __init__(self,path):
        config_filepath = 'stack_config_template.json'
        config_fullpath = os.path.join(path,config_filepath)
        ## Load in:
        with open(config_fullpath,'r') as f:
            config = json.load(f)
        self.config = config

        ## Initialize dev state variables.
        ## Active instance:
        self.instance = None
        ## Instance history:
        self.instance_hist = []

        ## Initialize dev history tracking.
        self.commands = []

        ## Initialize ami creation history tracking.
        self.ami_hist = []
        self.instance_saved = False


    ## Check if we are clear to deploy another dev instance.
    def get_instance_state(self):
        """
        Checks the instance associated with the DevAMI object, and determines its state. Used to maintain a limit of one live instance at a time during development.

        Outputs:
        (dict): a dictionary returning the status of the instance asso



        """

        self.instance.load()
        return self.instance.state
    def check_running(self):
        """
        A function to check if the instance associated with this object is live.

        Outputs:
        (bool): a boolean representing if the current instance is in the state "running" or not.
        """

        if self.instance is None:
            condition = False
            print("No instance declared")
        else:
            self.instance.load()
            if self.instance.state["Name"] == "running":
                condition = True
                print("Instance {} exists and is active, safe to test".format(self.instance.instance_id))
            else:
                condition = False
                print("Instance {} is {}, not safe to test.".format(self.instance.instance_id,self.instance.state["Name"]))
        return condition

    def check_clear(self):
        """
        A function to check if the current instance is live and can be actively developed. Prevents rampant instance propagation. Related to check_running, but not direct negations of each other.

        Outputs:
        (bool): a boolean representing if the current instance is inactive, and can be replaced by an active one.
        """

        if self.instance is None:
            condition = True
            print("No instance declared, safe to deploy.")
        else:
            self.instance.load()
            if self.instance.state["Name"] == "stopped" or self.instance.state["Name"] == "terminated" or self.instance.state["Name"] == "shutting-down":
                condition = True
                print("Instance {} exists, but is not active, safe to deploy".format(self.instance.instance_id))
            else:
                condition = False
                print("Instance {} is {}, not safe to deploy another.".format(self.instance.instance_id,self.instance.state["Name"]))
        return condition

    def launch_ami(self,ami = None):
        """
        Launches an instance from an ami. If ami is not given, launches the default ami of the pipeline as indicated in the stack configuration file. Launches on the instance type given in this same stack configuration file.

        Inputs:
        ami (str): (Optional) if not given, will be the default ami of the path.
        """
        ## Get ami id
        if ami is None:
            ami_id = self.config['Lambda']['LambdaConfig']['AMI']
        else:
            ami_id = ami
        ## Get default instance type:
        instance_type = self.config['Lambda']['LambdaConfig']['INSTANCE_TYPE']
        ec2_resource = boto3.resource('ec2')
        assert self.check_clear()
        out = ec2_resource.create_instances(ImageId=ami_id,
                InstanceType = instance_type,
                MinCount=1,
                MaxCount=1,
                DryRun=False,
                KeyName = "ta_testkey",
                SecurityGroups=['launch-wizard-34'],
                IamInstanceProfile={
                    'Name':'ec2_ssm'})
        ## Now get the instance id:
        self.instance = out[0]
        ## Add to the history:
        self.instance_hist.append(out[0])
        ami_instance_id = self.instance.instance_id

        ## Wait until this thing is started:
        started = False
        time.sleep(1)
        while not started:
            self.instance.load()
            state = self.instance.state["Name"]
            print("current state is: "+str(state))

            started = state == 'running'
            self.deployed = state == 'running'
            time.sleep(1)

        print('initializing instance')
        time.sleep(60) ## We need to wait until the instance gets set up.
        response = "Instance {} is running".format(self.instance.instance_id)
        print(response)

        ## Now associate a public ip address:
        ec2_client = boto3.client("ec2")

        #allocation = ec2_client.allocate_address(Domain="vpc")
        #response = ec2_client.associate_address(AllocationId=allocation["AllocationId"],InstanceId=self.instance.instance_id)
        #self.ip = allocation['PublicIp']
        self.ip = self.instance.public_ip_address
        print("instance running at {}".format(self.ip))
        self.instance_saved = False


    def submit_job(self,submitpath):
        """
        Submit a submit file json to a currently active development instance. Will not work if the current instance is not live.
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        """
        ## First make sure we have an instance to send to.
        assert self.check_running()
        ## Now get the submit configuration:
        with open(submitpath,'r') as f:
            submit_config = json.load(f)

        ## Get the datasets we want to use.
        data_allname = submit_config['dataname']

        ## Now get the command we want to send properly formatted:
        command_unformatted = self.config['Lambda']['LambdaConfig']['COMMAND']
        ## Get relevant parameters:
        bucketname_test = self.config['PipelineName']
        outdir = self.config['Lambda']['LambdaConfig']['OUTDIR']

        ## Now get a represetative dataset:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname_test)
        objgen = bucket.objects.filter(Prefix = data_allname)
        file_list = [obj.key for obj in objgen if obj.key[-1]!="/"]
        data_filename = file_list[0]

        command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir)]
        working_directory = [self.config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
        timeout = [str(self.config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

        print('sending command: '+command_formatted[0] +' to instance '+self.instance.instance_id)
        ## Get the ssm client:
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ssm_client.send_command(
            DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
            Parameters={'commands': command_formatted,
                        "workingDirectory":working_directory,
                        "executionTimeout":timeout},
            InstanceIds=[self.instance.instance_id],
            OutputS3BucketName=bucketname_test,
            OutputS3KeyPrefix="debug_direct/"
        )

        commandid = response['Command']['CommandId']

        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})

        for i in range(30):
            updated = ssm_client.list_commands(CommandId=commandid)
            time.sleep(5)
            status = updated['Commands'][0]['Status']
            print(status)


    def job_status(self,jobind = -1):
        """
        method to get out stdout and stderr from the jobs that were run on the instance.
        Inputs:
        jobind (int): index giving which job we should be paying attention to. Defaults to -1
        """

        ### Get the command we will analyze:
        try:
            command = self.commands[jobind]
        except IndexError as ie:
            print(ie," index {} does not exist for this object, exiting".format(jobind))
            raise
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        updated = ssm_client.list_commands(CommandId=command["commandid"])
        status = updated['Commands'][0]['Status']
        return status

    def job_output(self,jobind = -1):
        """
        method to get out stdout and stderr from the jobs that were run on the instance.
        Inputs:
        jobind (int): index giving which job we should be paying attention to. Defaults to -1
        """

        ### Get the command we will analyze:
        try:
            command = self.commands[jobind]
        except IndexError as ie:
            print(ie," index {} does not exist for this object, exiting".format(jobind))
            raise
        ### Get the s3 resource.
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(self.config["PipelineName"])
        path = os.path.join("debug_direct/",command['commandid'],command['instance'],'awsrunShellScript','0.awsrunShellScript/')
        output = {"stdout":"not loaded","stderr":"not loaded"}
        for key in output.keys():
            try:
                keypath =os.path.join(path,key)
                obj = s3.Object(self.config["PipelineName"],keypath)
                output[key] = obj.get()['Body'].read().decode("utf-8")
            except Exception as e:
                output[key] = "{} not found. may not be updated yet.".format(keypath)
        print(output['stdout'])
        print(output['stderr'])

        return output






    def start_devinstance(self):
        """
        method to stop the current development instance.
        """
        assert not self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.start_instances(InstanceIds = [self.instance.instance_id])
        print("instance {} is starting".format(self.instance.instance_id))
        ## Now wait until running.
        time.sleep(1)
        self.instance.load()
        while self.instance.state["Name"] == "pending":
            print("Instance starting: please wait")
            self.instance.load()
            time.sleep(10)
        self.ip = self.instance.public_ip_address
        print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def stop_devinstance(self):
        """
        method to stop the current development instance.
        """
        assert self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.stop_instances(InstanceIds = [self.instance.instance_id])
        print("instance {} is stopping".format(self.instance.instance_id))
        ## Now wait until stopped
        time.sleep(1)
        self.instance.load()
        while self.instance.state["Name"] == "stopping":
            print("Instance stopping: please wait")
            self.instance.load()
            time.sleep(10)
        print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def terminate_devinstance(self,force = False):
        """
        Method to terminate the current development instance.
        Inputs:
        force (bool): if set to true, will terminate even if results have not been saved into an ami.
        """

        ## Check if ami has been saved:
        if force == False:
            if self.instance_saved == False:
                print("dev history not saved as ami, will not delete (override with force = True)")
                proceed = False
            else:
                proceed = True
        else:
            proceed = True

        if proceed == True:
            ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
            response = ec2_client.terminate_instances(InstanceIds = [self.instance.instance_id])
            print("Instance {} is terminating".format(self.instance.instance_id))
            ## Now wait until terminated:
            time.sleep(1)
            self.instance.load()
            while self.instance.state["Name"] == "shutting-down":
                print("Instances terminating: please wait")
                self.instance.load()
                time.sleep(10)
            print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def create_devami(self,name):
        """
        Method to create a new ami from the current development instance.

        Inputs:
        name (str): the name to give to the new ami.
        """
        ## first get the ec2 client:
        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])

        ## Now create an image
        response = ec2_client.create_image(InstanceId=self.instance.instance_id,Name=name,Description = "AMI created at {}".format(str(datetime.datetime.now())))

        self.ami_hist.append(response)
        self.instance_saved = True
        print(response)

class DevAMI_full(DevAMI):
    def submit_job(self,submitpath):
        """
        Submit a submit file json to a currently active development instance. Will not work if the current instance is not live. Modified to the take config file, and create logging.
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        Output:
        (str): path to the output directory created by this function.
        (str): path to the data file analyzed by this function. 
        (str): id of the command issued to the instance. 

        """
        ## First make sure we have an instance to send to.
        assert self.check_running()
        ## Now get the submit configuration:
        with open(submitpath,'r') as f:
            submit_config = json.load(f)

        ## Get the datasets we want to use.
        data_allname = submit_config['dataname']
        config_name = submit_config['configname']

        ## Now get the command we want to send properly formatted:
        command_unformatted = self.config['Lambda']['LambdaConfig']['COMMAND']
        ## Get relevant parameters:
        bucketname_test = self.config['PipelineName']
        outdir = os.path.join(self.config['Lambda']['LambdaConfig']['OUTDIR'],"debugjob{}".format(str(datetime.datetime.now())))

        ## Now get a represetative dataset:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname_test)
        objgen = bucket.objects.filter(Prefix = data_allname)
        file_list = [obj.key for obj in objgen if obj.key[-1]!="/"]
        data_filename = file_list[0]


        command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir,config_name)]
        working_directory = [self.config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
        timeout = [str(self.config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

        print('sending command: '+command_formatted[0] +' to instance '+self.instance.instance_id)
        ## Get the ssm client:
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ssm_client.send_command(
            DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
            Parameters={'commands': command_formatted,
                        "workingDirectory":working_directory,
                        "executionTimeout":timeout},
            InstanceIds=[self.instance.instance_id],
            OutputS3BucketName=bucketname_test,
            OutputS3KeyPrefix="debug_direct/"
        )
        commandid = response['Command']['CommandId']
        time.sleep(5)
        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})
        return outdir,data_filename,commandid

    def submit_job_log(self,submitpath):
        """
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        """

        outdir,filename,commandid = self.submit_job(submitpath)
        s3_resource = boto3.resource("s3")
        ## Now create a job log. 
        ### The below mimics the structure of initialize_datasets_dev that is used by the lambda function. 
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","input":filename,"instance":self.instance.instance_id,"command":commandid}
        dataset_basename = os.path.basename(filename)
        status_name = "DATASET_NAME:{}_STATUS.txt".format(dataset_basename)
        status_path = os.path.join(outdir,self.config['Lambda']['LambdaConfig']['LOGDIR'],status_name)
        print(self.config["PipelineName"],status_path)
        statusobj = s3_resource.Object(self.config['PipelineName'],status_path)
        statusobj.put(Body = (bytes(json.dumps(template_dict).encode("UTF-8"))))



## A module to work with AMIs for the purpose of debugging and updating.
import boto3
import sys
import time
import os
import datetime
import json

def launch_default_ami(path):
    """
    This function reads the configuration file of a given pipeline, extracts the default ami, and launches it on the default instance type.

    Inputs:
    path (string): the path to the folder representing the pipeline that you would like to edit.
    """
    ## Get the configuration file from the current pipeline:
    config_filepath = 'stack_config_template.json'
    config_fullpath = os.path.join(path,config_filepath)
    ## Load in:
    with open(config_fullpath,'r') as f:
        config = json.load(f)
    ## Get ami id
    ami_id = config['Lambda']['LambdaConfig']['AMI']
    ## Get default instance type:
    instance_type = config['Lambda']['LambdaConfig']['INSTANCE_TYPE']
    ec2_resource = boto3.resource('ec2')
    out = ec2_resource.create_instances(ImageId=ami_id,
            InstanceType = instance_type,
            MinCount=1,
            MaxCount=1,
            DryRun=False,
            KeyName = "ta_testkey",
            SecurityGroups=['launch-wizard-34'],
            IamInstanceProfile={
                'Name':'ec2_ssm'})
    ## Now get the instance id:
    instance = out[0]
    ami_instance_id = instance.instance_id

    ## Wait until this thing is started:
    started = False
    while not started:
        instance.load()
        state = instance.state
        print("current state is: "+str(state))

        started = state['Name'] == 'running'
        time.sleep(1)
    print('initializing instance')
    time.sleep(60) ## We need to wait until the instance gets set up.
    response = "Instance {} is running"
    print(response.format(ami_instance_id))


def test_instance(instance_id,pipelinepath,submitpath):
    """
    Uses SSM manager to send a RunCommand document to a given instance, mimicking the way jobs would be sent to the instance by the user. Assumes that there is data at the S3 path referenced by the submit file that you give.


    Inputs:
    instance_id (str): the id of the instance (starts with i-) that you would like to send a command to. The instance must have ssm manager installed in order to run commands.
    pipelinepath (str): the path to the folder representing the pipeline that you would like to edit.
    submitpath (str): the path to the submit file that references data to be analyzed, and configurations to be used
    """

    ## Load in the json submit file:
    with open(submitpath,'r') as f:
        submit_config = json.load(f)
    data_filename = submit_config['filename']

    ## Load in the configuration file
    config_filepath = 'stack_config_template.json'
    config_fullpath = os.path.join(pipelinepath,config_filepath)
    ## Load in:
    with open(config_fullpath,'r') as f:
        config = json.load(f)

    ## Now get the command we want to send properly formatted:
    command_unformatted = config['Lambda']['LambdaConfig']['COMMAND']
    ## Get relevant parameters:
    bucketname_test = config['PipelineName']
    outdir = config['Lambda']['LambdaConfig']['OUTDIR']

    command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir)]
    working_directory = [config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
    timeout = [str(config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

    print('sending command: '+command_formatted[0] +' to instance '+instance_id)
    ## Get the ssm client:
    ssm_client = boto3.client('ssm',region_name = config['Lambda']['LambdaConfig']['REGION'])
    response = ssm_client.send_command(
        DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
        Parameters={'commands': command_formatted,
                    "workingDirectory":working_directory,
                    "executionTimeout":timeout},
        InstanceIds=[instance_id])
        #OutputS3BucketName=log_bucket_name,
        #OutputS3KeyPrefix=log_path
    #)
    commandid = response['Command']['CommandId']

    for i in range(30):
        updated = ssm_client.list_commands(CommandId=commandid)
        time.sleep(5)
        status = updated['Commands'][0]['Status']
        print(updated,status)

## New class to develop an ami.

class DevAMI(object):
    """
    This class streamlines the experience of developing an ami within an existing pipeline. It has three main functions:
    1) to launch a development instance from amis associated with a particular algorithm or pipeline,
    2) to test said amis with simulated job submission events, and
    3) to create new images once development instances are stable and ready for deployment.  

    The current instantiation of this class only allows for one development instance to be launched at a time to encourage responsible usage.

    Inputs:
    path (str): the path to the directory for a given pipeline.


    Example Usage:
    ```python
    devenv = DevAMI("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
    devenv.launch_ami() ## function 1 referenced above
    ### Do some development on the remote instance
    devenv.submit_job("/path/to/submit/file") ## function 2 referenced above
    ### Monitor the remote instance to make sure that everything is running as expected, outputs are returned
    devenv.create_devami("new_ami") ## function 3 referenced above
    devenv.terminate_devinstance() ## clean up after done developing
    ```
    """
    def __init__(self,path):
        config_filepath = 'stack_config_template.json'
        config_fullpath = os.path.join(path,config_filepath)
        ## Load in:
        with open(config_fullpath,'r') as f:
            config = json.load(f)
        self.config = config

        ## Initialize dev state variables.
        ## Active instance:
        self.instance = None
        ## Instance history:
        self.instance_hist = []

        ## Initialize dev history tracking.
        self.commands = []

        ## Initialize ami creation history tracking.
        self.ami_hist = []
        self.instance_saved = False


    ## Check if we are clear to deploy another dev instance.
    def get_instance_state(self):
        """
        Checks the instance associated with the DevAMI object, and determines its state. Used to maintain a limit of one live instance at a time during development.

        Outputs:
        (dict): a dictionary returning the status of the instance asso



        """

        self.instance.load()
        return self.instance.state
    def check_running(self):
        """
        A function to check if the instance associated with this object is live.

        Outputs:
        (bool): a boolean representing if the current instance is in the state "running" or not.
        """

        if self.instance is None:
            condition = False
            print("No instance declared")
        else:
            self.instance.load()
            if self.instance.state["Name"] == "running":
                condition = True
                print("Instance {} exists and is active, safe to test".format(self.instance.instance_id))
            else:
                condition = False
                print("Instance {} is {}, not safe to test.".format(self.instance.instance_id,self.instance.state["Name"]))
        return condition

    def check_clear(self):
        """
        A function to check if the current instance is live and can be actively developed. Prevents rampant instance propagation. Related to check_running, but not direct negations of each other.

        Outputs:
        (bool): a boolean representing if the current instance is inactive, and can be replaced by an active one.
        """

        if self.instance is None:
            condition = True
            print("No instance declared, safe to deploy.")
        else:
            self.instance.load()
            if self.instance.state["Name"] == "stopped" or self.instance.state["Name"] == "terminated" or self.instance.state["Name"] == "shutting-down":
                condition = True
                print("Instance {} exists, but is not active, safe to deploy".format(self.instance.instance_id))
            else:
                condition = False
                print("Instance {} is {}, not safe to deploy another.".format(self.instance.instance_id,self.instance.state["Name"]))
        return condition

    def launch_ami(self,ami = None):
        """
        Launches an instance from an ami. If ami is not given, launches the default ami of the pipeline as indicated in the stack configuration file. Launches on the instance type given in this same stack configuration file.

        Inputs:
        ami (str): (Optional) if not given, will be the default ami of the path.
        """
        ## Get ami id
        if ami is None:
            ami_id = self.config['Lambda']['LambdaConfig']['AMI']
        else:
            ami_id = ami
        ## Get default instance type:
        instance_type = self.config['Lambda']['LambdaConfig']['INSTANCE_TYPE']
        ec2_resource = boto3.resource('ec2')
        assert self.check_clear()
        out = ec2_resource.create_instances(ImageId=ami_id,
                InstanceType = instance_type,
                MinCount=1,
                MaxCount=1,
                DryRun=False,
                KeyName = "ta_testkey",
                SecurityGroups=['launch-wizard-34'],
                IamInstanceProfile={
                    'Name':'ec2_ssm'})
        ## Now get the instance id:
        self.instance = out[0]
        ## Add to the history:
        self.instance_hist.append(out[0])
        ami_instance_id = self.instance.instance_id

        ## Wait until this thing is started:
        started = False
        time.sleep(1)
        while not started:
            self.instance.load()
            state = self.instance.state["Name"]
            print("current state is: "+str(state))

            started = state == 'running'
            self.deployed = state == 'running'
            time.sleep(1)

        print('initializing instance')
        time.sleep(60) ## We need to wait until the instance gets set up.
        response = "Instance {} is running".format(self.instance.instance_id)
        print(response)

        ## Now associate a public ip address:
        ec2_client = boto3.client("ec2")

        #allocation = ec2_client.allocate_address(Domain="vpc")
        #response = ec2_client.associate_address(AllocationId=allocation["AllocationId"],InstanceId=self.instance.instance_id)
        #self.ip = allocation['PublicIp']
        self.ip = self.instance.public_ip_address
        print("instance running at {}".format(self.ip))
        self.instance_saved = False


    def submit_job(self,submitpath):
        """
        Submit a submit file json to a currently active development instance. Will not work if the current instance is not live.
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        """
        ## First make sure we have an instance to send to.
        assert self.check_running()
        ## Now get the submit configuration:
        with open(submitpath,'r') as f:
            submit_config = json.load(f)

        ## Get the datasets we want to use.
        data_allname = submit_config['dataname']

        ## Now get the command we want to send properly formatted:
        command_unformatted = self.config['Lambda']['LambdaConfig']['COMMAND']
        ## Get relevant parameters:
        bucketname_test = self.config['PipelineName']
        outdir = self.config['Lambda']['LambdaConfig']['OUTDIR']

        ## Now get a represetative dataset:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname_test)
        objgen = bucket.objects.filter(Prefix = data_allname)
        file_list = [obj.key for obj in objgen if obj.key[-1]!="/"]
        data_filename = file_list[0]

        command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir)]
        working_directory = [self.config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
        timeout = [str(self.config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

        print('sending command: '+command_formatted[0] +' to instance '+self.instance.instance_id)
        ## Get the ssm client:
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ssm_client.send_command(
            DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
            Parameters={'commands': command_formatted,
                        "workingDirectory":working_directory,
                        "executionTimeout":timeout},
            InstanceIds=[self.instance.instance_id],
            OutputS3BucketName=bucketname_test,
            OutputS3KeyPrefix="debug_direct/"
        )

        commandid = response['Command']['CommandId']

        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})

        for i in range(30):
            updated = ssm_client.list_commands(CommandId=commandid)
            time.sleep(5)
            status = updated['Commands'][0]['Status']
            print(status)


    def job_status(self,jobind = -1):
        """
        method to get out stdout and stderr from the jobs that were run on the instance.
        Inputs:
        jobind (int): index giving which job we should be paying attention to. Defaults to -1
        """

        ### Get the command we will analyze:
        try:
            command = self.commands[jobind]
        except IndexError as ie:
            print(ie," index {} does not exist for this object, exiting".format(jobind))
            raise
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        updated = ssm_client.list_commands(CommandId=command["commandid"])
        status = updated['Commands'][0]['Status']
        return status

    def job_output(self,jobind = -1):
        """
        method to get out stdout and stderr from the jobs that were run on the instance.
        Inputs:
        jobind (int): index giving which job we should be paying attention to. Defaults to -1
        """

        ### Get the command we will analyze:
        try:
            command = self.commands[jobind]
        except IndexError as ie:
            print(ie," index {} does not exist for this object, exiting".format(jobind))
            raise
        ### Get the s3 resource.
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(self.config["PipelineName"])
        path = os.path.join("debug_direct/",command['commandid'],command['instance'],'awsrunShellScript','0.awsrunShellScript/')
        output = {"stdout":"not loaded","stderr":"not loaded"}
        for key in output.keys():
            try:
                keypath =os.path.join(path,key)
                obj = s3.Object(self.config["PipelineName"],keypath)
                output[key] = obj.get()['Body'].read().decode("utf-8")
            except Exception as e:
                output[key] = "{} not found. may not be updated yet.".format(keypath)
        print(output['stdout'])
        print(output['stderr'])

        return output






    def start_devinstance(self):
        """
        method to stop the current development instance.
        """
        assert not self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.start_instances(InstanceIds = [self.instance.instance_id])
        print("instance {} is starting".format(self.instance.instance_id))
        ## Now wait until running.
        time.sleep(1)
        self.instance.load()
        while self.instance.state["Name"] == "pending":
            print("Instance starting: please wait")
            self.instance.load()
            time.sleep(10)
        self.ip = self.instance.public_ip_address
        print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def stop_devinstance(self):
        """
        method to stop the current development instance.
        """
        assert self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.stop_instances(InstanceIds = [self.instance.instance_id])
        print("instance {} is stopping".format(self.instance.instance_id))
        ## Now wait until stopped
        time.sleep(1)
        self.instance.load()
        while self.instance.state["Name"] == "stopping":
            print("Instance stopping: please wait")
            self.instance.load()
            time.sleep(10)
        print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def terminate_devinstance(self,force = False):
        """
        Method to terminate the current development instance.
        Inputs:
        force (bool): if set to true, will terminate even if results have not been saved into an ami.
        """

        ## Check if ami has been saved:
        if force == False:
            if self.instance_saved == False:
                print("dev history not saved as ami, will not delete (override with force = True)")
                proceed = False
            else:
                proceed = True
        else:
            proceed = True

        if proceed == True:
            ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
            response = ec2_client.terminate_instances(InstanceIds = [self.instance.instance_id])
            print("Instance {} is terminating".format(self.instance.instance_id))
            ## Now wait until terminated:
            time.sleep(1)
            self.instance.load()
            while self.instance.state["Name"] == "shutting-down":
                print("Instances terminating: please wait")
                self.instance.load()
                time.sleep(10)
            print("Instance is now in state: {}".format(self.instance.state["Name"]))

    def create_devami(self,name):
        """
        Method to create a new ami from the current development instance.

        Inputs:
        name (str): the name to give to the new ami.
        """
        ## first get the ec2 client:
        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])

        ## Now create an image
        response = ec2_client.create_image(InstanceId=self.instance.instance_id,Name=name,Description = "AMI created at {}".format(str(datetime.datetime.now())))

        self.ami_hist.append(response)
        self.instance_saved = True
        print(response)

class DevAMI_full(DevAMI):
    """
    ## UPDATE of DevAMI to account for new infrastructure 11/18/19.
    This class streamlines the experience of developing an ami within an existing pipeline. It has three main functions:
    1) to launch a development instance from amis associated with a particular algorithm or pipeline,
    2) to test said amis with simulated job submission events, and
    3) to create new images once development instances are stable and ready for deployment.  

    The current instantiation of this class only allows for one development instance to be launched at a time to encourage responsible usage.

    Inputs:
    path (str): the path to the directory for a given pipeline.


    Example Usage:
    ```python
    devenv = DevAMI_full("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
    devenv.launch_ami() ## function 1 referenced above
    ### Do some development on the remote instance
    devenv.submit_job_log("/path/to/submit/file") ## function 2 referenced above
    ### Monitor the remote instance to make sure that everything is running as expected, outputs are returned
    devenv.job_status(-1) ## Get the status of the last submitted job (-1)
    devenv.job_output(-1) ## Get the stdout and stderr of the last submitted job (-1)
    devenv.create_devami("new_ami") ## function 3 referenced above
    devenv.terminate_devinstance() ## clean up after done developing
    ```
    """
    def submit_job(self,submitpath):
        """
        Submit a submit file json to a currently active development instance. Will not work if the current instance is not live. Modified to the take config file, and create logging.
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        Output:
        (str): path to the output directory created by this function.
        (str): path to the data file analyzed by this function. 
        (str): id of the command issued to the instance. 

        """
        ## First make sure we have an instance to send to.
        assert self.check_running()
        ## Now get the submit configuration:
        with open(submitpath,'r') as f:
            submit_config = json.load(f)

        ## Get the datasets we want to use.
        data_allname = submit_config['dataname']
        config_name = submit_config['configname']

        ## Now get the command we want to send properly formatted:
        command_unformatted = self.config['Lambda']['LambdaConfig']['COMMAND']
        ## Get relevant parameters:
        bucketname_test = self.config['PipelineName']
        outdir = os.path.join(self.config['Lambda']['LambdaConfig']['OUTDIR'],"debugjob{}".format(str(datetime.datetime.now())))

        ## Now get a represetative dataset:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname_test)
        objgen = bucket.objects.filter(Prefix = data_allname)
        file_list = [obj.key for obj in objgen if obj.key[-1]!="/"]
        data_filename = file_list[0]


        command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir,config_name)]
        working_directory = [self.config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
        timeout = [str(self.config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

        print('sending command: '+command_formatted[0] +' to instance '+self.instance.instance_id)
        ## Get the ssm client:
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ssm_client.send_command(
            DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
            Parameters={'commands': command_formatted,
                        "workingDirectory":working_directory,
                        "executionTimeout":timeout},
            InstanceIds=[self.instance.instance_id],
            OutputS3BucketName=bucketname_test,
            OutputS3KeyPrefix="debug_direct/"
        )
        commandid = response['Command']['CommandId']
        time.sleep(5)
        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})
        return outdir,data_filename,commandid

    def submit_job_log(self,submitpath):
        """
        Inputs:
        submitpath:(str) path to a submit.json formatted file.
        """

        ## First make sure we have an instance to send to.
        assert self.check_running()
        ## Now get the submit configuration:
        with open(submitpath,'r') as f:
            submit_config = json.load(f)

        ## Get the datasets we want to use.
        data_allname = submit_config['dataname']
        config_name = submit_config['configname']

        ## Now get the command we want to send properly formatted:
        command_unformatted = self.config['Lambda']['LambdaConfig']['COMMAND']
        ## Get relevant parameters:
        bucketname_test = self.config['PipelineName']
        outdir = os.path.join(self.config['Lambda']['LambdaConfig']['OUTDIR'],"debugjob{}".format(str(datetime.datetime.now())))

        ## Now get a represetative dataset:
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(bucketname_test)
        objgen = bucket.objects.filter(Prefix = data_allname)
        file_list = [obj.key for obj in objgen if obj.key[-1]!="/"]
        data_filename = file_list[0]


        command_formatted = [command_unformatted.format(bucketname_test,data_filename,outdir,config_name)]
        working_directory = [self.config['Lambda']['LambdaConfig']['WORKING_DIRECTORY']]
        timeout = [str(self.config['Lambda']['LambdaConfig']['SSM_TIMEOUT'])]

        print('sending command: '+command_formatted[0] +' to instance '+self.instance.instance_id)
        ## Get the ssm client:
        ssm_client = boto3.client('ssm',region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ssm_client.send_command(
            DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
            Parameters={'commands': command_formatted,
                        "workingDirectory":working_directory,
                        "executionTimeout":timeout},
            InstanceIds=[self.instance.instance_id],
            OutputS3BucketName=bucketname_test,
            OutputS3KeyPrefix="debug_direct/"
        )
        commandid = response['Command']['CommandId']
        ## race condition? 
        s3_resource = boto3.resource("s3")
        ## Now create a job log. 
        ### The below mimics the structure of initialize_datasets_dev that is used by the lambda function. 
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","input":data_filename,"instance":self.instance.instance_id,"command":commandid}
        dataset_basename = os.path.basename(data_filename)
        dataset_dir = re.findall("(.+)/{}/".format(self.config['Lambda']['LambdaConfig']['INDIR']),data_filename)[0]
        status_name = "DATASET_NAME:{}_STATUS.txt".format(dataset_basename)
        status_path = os.path.join(dataset_dir,outdir,self.config['Lambda']['LambdaConfig']['LOGDIR'],status_name)
        statusobj = s3_resource.Object(self.config['PipelineName'],status_path)
        statusobj.put(Body = (bytes(json.dumps(template_dict).encode("UTF-8"))))

        time.sleep(5)
        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})



