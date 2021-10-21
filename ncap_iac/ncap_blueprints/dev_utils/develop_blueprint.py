## A module to work with AMIs for the purpose of debugging and updating.
import boto3
from botocore.exceptions import ClientError
import sys
import time
import os
import re
import datetime
import subprocess
import json
import pathlib

ec2_resource = boto3.resource('ec2')
ec2_client = boto3.client("ec2")

## Get global parameters:
utildir = pathlib.Path(__file__).parent.absolute()
basedir = os.path.dirname(os.path.dirname(utildir))
with open(os.path.join(basedir,"global_params_initialized.json")) as gp:
    gpdict = json.load(gp)

def return_tags(timeout):    
    """Formats tags to launch instances in a way that will not be shut down by neurocaas AWS account monitoring. 

    :param timeout: The amount of time, in minutes, for which you are requesting this instance to be up. Should be given as an integer. 
    """
    assert type(timeout) == int, "timeout must be a positive integer."
    assert timeout > 0, "timeout must be a positive integer."
    arn = boto3.client("sts").get_caller_identity()["Arn"]
    tags = [
                {
                    "ResourceType":"volume",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":str(timeout),
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":arn,
                    }
                    ]
                },
                {
                    "ResourceType":"instance",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":str(timeout),
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":arn,
                    }
                    ]
                }
            ]
    return tags

## New class to develop an ami.
class NeuroCaaSAMI(object):
    """
    This class streamlines the experience of building an ami for a new pipeline, or impriving one within an existing pipeline. It has three main functions:
    1) to launch a development instance from amis associated with a particular algorithm or pipeline,
    2) to test said amis with simulated job submission events, and
    3) to create new images once development instances are stable and ready for deployment.  

    This class only allows for one development instance to be launched at a time to encourage responsible usage.

    This class assumes that you have already configured a pipeline, having created a folder for it, and filled out the template with relevant details [not the ami, as this is what we will build here.]   

    Inputs:
    path (str): the path to the directory for a given pipeline.


    Example Usage:
    ```python
    devenv = NeuroCaaSAMI("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
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
        self.config_filepath = config_filepath
        self.config_fullpath = config_fullpath
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

    def assign_instance(self,instance_id):
        """Add a method to assign instances instances as the indicated development instance.  

        :param instance_id: takes the instance id as a string.

        """
        if self.instance is not None:
            self.instance_hist.append(self.instance)
            self.instance_saved = False ## Defaults to assuming the instance has not been saved. 
        instance = ec2_resource.Instance(instance_id)
        try:
            instance.state
        except ClientError:
            print("Instance with id {} can't be loaded".format(instance_id))
            raise
        self.instance = instance
    

    def launch_devinstance(self,ami = None,volume_size = None,timeout = 60,DryRun = False):
        """
        Launches an instance from an ami. If ami is not given, launches the default ami of the pipeline as indicated in the stack configuration file. Launches on the instance type given in this same stack configuration file.

        Inputs:
        :param ami (str): (Optional) if not given, will be the default ami of the path. This has several text options to be maximally useful. 
            [amis recent as of 3/16]
            ubuntu18: ubuntu linux 18.06, 64 bit x86 (ami-07ebfd5b3428b6f4d)
            ubuntu16: ubuntu linux 16.04, 64 bit x86 (ami-08bc77a2c7eb2b1da)
            dlami18: ubuntu 18.06 version 27 (ami-0dbb717f493016a1a)
            dlami16: ubuntu 16.04 version 27 (ami-0a79b70001264b442)
        :param volume_size (int): (Optional) the size of the volume to attach to this devinstance.      
        timeout (int): (Optional) the amount of time for which you are requesting this instance, in minutes. default is 1 hour. INTANCE WILL BE STOPPED AFTER THIS TIMEOUT COMPLETES.
        :param DryRun (bool): for debugging. if dryrun will not launch an instance.
        """
        ## Get ami id
        ami_mapping = {
                "ubuntu18":"ami-07ebfd5b3428b6f4d",
                "ubuntu16":"ami-08bc77a2c7eb2b1da",
                "dlami18":"ami-0dbb717f493016a1a",
                "dlami16":"ami-0a79b70001264b442"
                }


        if ami is None:
            ami_id = self.config['Lambda']['LambdaConfig']['AMI']
            print("checking image is available...")
            waiter = ec2_client.get_waiter("image_available")
            waiter.wait(ImageIds = [ami_id])
            proceed = True

        elif ami in ami_mapping.keys():    
            ami_id = ami_mapping[ami]
        else:
            # Assume this is a real id: let boto3 handle this error when it comes. 
            ami_id = ami

        ## Get default instance type:
        instance_type = self.config['Lambda']['LambdaConfig']['INSTANCE_TYPE']
        assert self.check_clear()
        argdict = {
                 "ImageId":ami_id,
                 "InstanceType":instance_type,
                 "MinCount":1,
                 "MaxCount":1,
                 "DryRun":DryRun,
                 "KeyName": "testkeystack-custom-dev-key-pair",
                 "SecurityGroups":[gpdict["securitygroupdevname"]],
                 "IamInstanceProfile":{'Name':self.config["Lambda"]["LambdaConfig"]["IAM_ROLE"]},
                 "TagSpecifications" : return_tags(timeout)
                 }
        if volume_size is None:
            pass
        else: 
            argdict["BlockDeviceMappings"]= [
                            {
                                "DeviceName": "/dev/sda1",
                                "Ebs": {
                                    "DeleteOnTermination": True,
                                    "VolumeSize":volume_size,
                                    "VolumeType":"gp2",
                                    "Encrypted": False
                                    }
                            }]

        out = ec2_resource.create_instances(**argdict)    

# Now get the instance id:
        self.instance = out[0]
        ## Add to the history:
        self.instance_hist.append(out[0])
        ami_instance_id = self.instance.instance_id

        ## Wait until this thing is started:
        waiter = ec2_client.get_waiter('instance_status_ok')
        print("Instance starting up: please wait")
        waiter.wait(InstanceIds = [self.instance.instance_id])
        self.instance.load()
        response = "Instance {} is running".format(self.instance.instance_id)
        print(response)

        ## Now associate a public ip address:

        self.ip = self.instance.public_ip_address
        print("instance running at {}".format(self.ip))
        self.instance_saved = False

    def get_lifetime(self):
        """Describe the amount of time remaining on this instance. 

        """
        instance_info = ec2_client.describe_instances(InstanceIds=[self.instance.instance_id])
        info_dict = instance_info["Reservations"][0]["Instances"][0]
        launch_time = info_dict["LaunchTime"]
        current_time = datetime.datetime.now(datetime.timezone.utc)
        ## get current elapsed time. 
        diff = current_time-launch_time
        seconds_in_day = 24 * 60 * 60
        currmins,currsecs = divmod(diff.days*seconds_in_day+diff.seconds,60)
        ## get assigned time: 
        try:
            tags = info_dict["Tags"]
            tagdict = {d["Key"]:d["Value"] for d in tags}
            timeout = tagdict["Timeout"]
        except KeyError:    
            raise Exception("Timeout not give; not a valid development instance.")
        expiretime = launch_time + datetime.timedelta(minutes=int(timeout))
        tildiff = expiretime - current_time 
        tilmins,tilsecs = divmod(tildiff.days*seconds_in_day+tildiff.seconds,60)
        message = "Instance has been on for {} minutes and {} seconds. Will be stopped in {} minutes and {} seconds with the current timeout.".format(currmins,currsecs,tilmins,tilsecs)

        return message 

    def change_owner(self,owner,DryRun = True):
        """Change the owner of a pipeline. Currently does not work with testdev permissions; included for testing purposes
        """
        resp = ec2_client.create_tags(Resources = [self.instance.instance_id],
                Tags = [
                    {
                        "Key":"OwnerArn",
                        "Value":owner
                        }
                    ],
                DryRun = DryRun)
        return resp        

    def extend_lifetime(self,additional_time,DryRun = False):
        """If you need more time to develop, extend the requested lifetime of your instance by `additional_time minutes.`

        :param additional_time (additional_time): The amount of time that you woul 
        """
        instance_info = ec2_client.describe_instances(InstanceIds=[self.instance.instance_id])
        info_dict = instance_info["Reservations"][0]["Instances"][0]
        try:
            tags = info_dict["Tags"]
            tagdict = {d["Key"]:d["Value"] for d in tags}
            timeout = int(tagdict["Timeout"])
        except KeyError:    
            raise Exception("Timeout not give; not a valid development instance.")
        new_timeout = timeout + additional_time
        resp = ec2_client.create_tags(Resources = [self.instance.instance_id],
                Tags = [
                    {
                        "Key":"Timeout",
                        "Value":str(new_timeout)
                        }
                    ],
                DryRun = DryRun)
        return resp        

    def submit_job(self,submitpath):
        """
        Submit a test job with a submit.json file. 
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
        outdir = os.path.join(gpdict["output_directory"],"debugjob{}".format(str(datetime.datetime.now())))

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
        dataset_dir = re.findall("(.+)/{}/".format(gpdict["input_directory"]),data_filename)[0]
        status_name = "DATASET_NAME:{}_STATUS.txt".format(dataset_basename)
        status_path = os.path.join(dataset_dir,outdir,gpdict["log_directory"],status_name)
        statusobj = s3_resource.Object(self.config['PipelineName'],status_path)
        statusobj.put(Body = (bytes(json.dumps(template_dict).encode("UTF-8"))))

        time.sleep(5)
        self.commands.append({"instance":self.instance.instance_id,"time":str(datetime.datetime.now()),"commandid":commandid,"commandinfo":ssm_client.get_command_invocation(CommandId=commandid,InstanceId=self.instance.instance_id)})

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


    def start_devinstance(self,timeout = 60):
        """
        method to stop the current development instance. Specify a timeout for how long you expect the instance to be active. 

        """
        assert not self.check_running()

        response = ec2_client.start_instances(InstanceIds = [self.instance.instance_id])
        resp = ec2_client.create_tags(Resources = [self.instance.instance_id],
                Tags = [
                    {
                        "Key":"Timeout",
                        "Value":str(timeout)
                        }
                    ],
                )
        print("instance {} is starting".format(self.instance.instance_id))
        ## Now wait until running.
        waiter = ec2_client.get_waiter('instance_running')
        print("Instance starting: please wait")
        waiter.wait(InstanceIds = [self.instance.instance_id])
        self.instance.load()
        self.ip = self.instance.public_ip_address
        message = "Instance is now in state: {}".format(self.instance.state["Name"])
        print(message)
        return message

    def stop_devinstance(self):
        """
        method to stop the current development instance.
        """
        assert self.check_running()

        response = ec2_client.stop_instances(InstanceIds = [self.instance.instance_id])
        print("instance {} is stopping".format(self.instance.instance_id))
        ## Now wait until stopped
        print("Instance stopping: please wait")
        waiter = ec2_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds = [self.instance.instance_id])
        self.instance.load()
        message = "Instance is now in state: {}".format(self.instance.state["Name"])
        print(message)
        return message

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
                ## Check that the most recent ami is available before deleting:  
                print("waiting for created image to become available...")
                imageid = self.ami_hist[-1]["ImageId"]
                waiter = ec2_client.get_waiter("image_available")
                waiter.wait(ImageIds = [imageid])
                proceed = True
        else:
            proceed = True

        if proceed == True:
            response = ec2_client.terminate_instances(InstanceIds = [self.instance.instance_id])
            print("Instance {} is terminating".format(self.instance.instance_id))
            ## Now wait until terminated:
            waiter = ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds = [self.instance.instance_id])
            self.instance.load()
            message = "Instance is now in state: {}".format(self.instance.state["Name"])
            print(message)
            return message 
        else:
            message = "No state change."
            print(message)
            return message 

    def create_devami(self,name):
        """
        Method to create a new ami from the current development instance.

        Inputs:
        name (str): the name to give to the new ami.
        """
        ## first get the ec2 client:

        ## Now create an image
        response = ec2_client.create_image(InstanceId=self.instance.instance_id,Name=name,Description = "AMI created at {}".format(str(datetime.datetime.now())))

        self.ami_hist.append(response)
        self.instance_saved = True

    def update_blueprint(self,ami_id=None,message=None):
        """
        Method to take more recently developed amis, and assign them to the stack_config_template of the relevant instance, and create a git commit to document this change. 

        Inputs: 
        ami_id:(str) the ami id with which to update the blueprint for the pipeline in question. If none is given, defaults to the most recent ami in the ami_hist list. 
        message:(str) (Optional) the message we associate with this particular commit. 
        """
        ## First, get the ami we want to use:
        if ami_id is None:
            ami_id = self.ami_hist[-1]["ImageId"]
        else:
            pass

        ## Now parse the message:
        if message is None:
            message = "Not given"
        else:
            pass
        ## now, commit the current version of the stack config template and indicate this as the Parent ID in the template. 
        subprocess.call(["git","add",self.config_fullpath])
        subprocess.call(["git","commit","-m","automatic commit to document pipeline {} before update at {}".format(self.config_filepath,str(datetime.datetime.now()))])
        old_hash = subprocess.check_output(["git","rev-parse","HEAD"]).decode("utf-8")
        print("old commit has hash: {}".format(old_hash))

        ## now change the config to reflect your most recent ami edits:
        if self.config["Lambda"]["LambdaConfig"]["AMI"] == ami_id:
            print("Blueprint already up to date, aborting new commit.")
        else:
            self.config["Lambda"]["LambdaConfig"]["AMI"] = ami_id

            ## now open and write to the stack config file:
            with open(self.config_fullpath,"w") as configfile:
                json.dump(self.config,configfile,indent = 4)
                print("Blueprint updated with ami {}".format(ami_id))
            
            subprocess.call(["git","add",self.config_fullpath])
            subprocess.call(["git","commit","-m","automatic commit to document pipeline {} after update at {}. Purpose: {}".format(self.config_filepath,str(datetime.datetime.now()),message)])
            new_hash = subprocess.check_output(["git","rev-parse","HEAD"]).decode("utf-8")
            print("new commit has hash: {}".format(new_hash))



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
            try:
                if self.instance.state["Name"] == "stopped" or self.instance.state["Name"] == "terminated" or self.instance.state["Name"] == "shutting-down":
                    condition = True
                    print("Instance {} exists, but is not active, safe to deploy".format(self.instance.instance_id))
                else:
                    condition = False
                    print("Instance {} is {}, not safe to deploy another.".format(self.instance.instance_id,self.instance.state["Name"]))

            ## Handle the case where the instance is terminated and cannot be gotten. 
            except AttributeError as atterr: 
                if str(atterr) == "'NoneType' object has no attribute 'get'":
                    print("Instance is terminated and no trace exists")
                    condition = True
                else:
                    print("Unknown error. Try again. ")
                    condition = False
                

        return condition




