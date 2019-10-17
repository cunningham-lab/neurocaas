## A module to work with AMIs for the purpose of debugging and updating. 
import boto3 
import sys 
import time
import os 
import datetime
import json 

## Given the path to a pipeline, launches an instance of the ami currently tethered to that ami as the default.  
def launch_default_ami(path):
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

## Uses SSM manager to send a RunCommand document to a given instance. Does so in a way that mimics the protocol of the submit file.  
## We could make this all part of a debug workflow
def test_instance(instance_id,pipelinepath,submitpath):
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
    def __init__(self,path):
        """
        Inputs: 
        path :(str) the path to the directory for a given pipeline. 

        """
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


    ## Check if we are clear to deploy another dev instance. 
    def get_instance_state(self):
    
        self.instance.load()
        return self.instance.state
    def check_running(self):
        """
        A mini function to check if there is an ami being actively developed. This one checks for running only. 
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
        A mini function to check if there is an ami being actively developed. Prevents rampant instance propagation. 
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
        launches the default ami of this analysis pipeline. 
        Inputs: 
        ami (str): Optional: if not given, will be the default ami of the path.
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

        allocation = ec2_client.allocate_address(Domain="vpc")
        response = ec2_client.associate_address(AllocationId=allocation["AllocationId"],InstanceId=self.instance.instance_id)
        self.ip = allocation['PublicIp'] 
        print("Instance running at {}".format(self.ip))
 

    def submit_job(self,submitpath):
        """
        Submit a submit file json to the currently active development instance. 
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
            InstanceIds=[self.instance.instance_id])
            #OutputS3BucketName=log_bucket_name,
            #OutputS3KeyPrefix=log_path
        #)
        commandid = response['Command']['CommandId']
        
        for i in range(30):
            updated = ssm_client.list_commands(CommandId=commandid)
            time.sleep(5)
            status = updated['Commands'][0]['Status']
            print(updated,status)

        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})

    def stop_devinstance(self):
        """
        If there is a development instance running, stop it. 
        """
        assert self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.stop_instances(InstanceIds = [self.instance.instance_id])
        print("Instance {} is stopping".format(self.instance.instance_id))

    def terminate_devinstance(self):
        """
        If there is a development instance running, terminate it. 
        """
        assert self.check_running()

        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])
        response = ec2_client.terminate_instances(InstanceIds = [self.instance.instance_id])
        print("Instance {} is terminating".format(self.instance.instance_id))

    def create_devami(self,name):
        """
        Inputs:
        name (str): the name to give to the new ami. 
        """
        ## first get the ec2 client:
        ec2_client = boto3.client("ec2",region_name = self.config['Lambda']['LambdaConfig']['REGION'])

        ## Now create an image
        response = ec2_client.create_image(InstanceId=self.instance.instance_id,Name=name,Description = "AMI created at {}".format(str(datetime.datetime.now())))

        self.ami_hist.append(response)
        print(response)


