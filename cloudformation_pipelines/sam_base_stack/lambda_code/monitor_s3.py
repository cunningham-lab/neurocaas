import boto3
from botocore.errorfactory import ClientError
import os
import time
## Script to run code on shell in instance (from https://stackoverflow.com/questions/42645196/how-to-ssh-and-run-commands-in-ec2-using-boto3):
def execute_commands_on_linux_instances(client, commands, wd, instance_ids):
    """Runs commands on remote linux instances
    :param client: a boto/boto3 ssm client
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """

    resp = client.send_command(
        DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
        Parameters={'commands': commands,"workingDirectory":wd,"executionTimeout":['172800']},
        InstanceIds=instance_ids,
        OutputS3BucketName='uploaddetect',
    )
    return resp
    
## Script to start an ec2 instance if not running already:
## Check relevant ec2 instance state: 
def start_instance_if_stopped(instance):
    state = instance.state['Name']
    print(state)
    ## If not running, run:
    if state != 'running':
        instance.start()
        ## Wait for the instance to start and pass checks.
        instance.wait_until_running()
        time.sleep(60)
        print('started instance')

## We want case by case handling of the upload flow.
def process_upload(key,bucket):
    ### Declaration of relevant things:
    # Declare resources
    s3 = boto3.resource('s3')
    ec2 = boto3.resource('ec2')
    
    # Declare clients:
    s3_client = boto3.client('s3',region_name = 'us-east-1')
    ec2_client = boto3.client('ec2',region_name = 'us-east-1')
    ssm_client = boto3.client('ssm',region_name = 'us-east-1')
    
    # Declare things within these resources
    my_bucket = s3.Bucket(bucket)
    vidinstance_id = 'i-085f9a367c3ff3c5b'
    gpuinstance_id = 'i-083da740fce33e2df'
    video_instance = ec2.Instance(vidinstance_id)
    gpu_instance = ec2.Instance(gpuinstance_id)
    
    ### Processing starts here: 
    
    ## Handle folder creation. 
    if key[-1] == '/':
        if key.split('/')[-2] == 'analysis_folder':
            print('analysis folder created')
        else:
            print('new folder created, please upload config file')
        return
        
    ## "Folder structure" of the bucket: 
    keyfolds = key.split('/')
    ## Get the object name: 
    object = keyfolds[-1]
    ## Get the "local directory" we are in:
    local = keyfolds[-2]
    local_full = os.path.join(*keyfolds[:-1])
    
    ## Handle config file requirements: 
    if object == 'config.py':
        print('config file added, ready to accept data input')
        return
        
    ## Handle video uploads:
    print(object.split('.'))
    if object.split('.')[-1] in ['mp4','avi']:
        if local == 'analysis_folder':
            ## Call routine for gpu
            start_instance_if_stopped(gpu_instance)
            
            ## Send command to EC2: 
            commands = ['cd ../../../../home/ubuntu; bin/run.sh '+key+';']
            wd = ['~/bin']
            # commands = ['ls; bin/run.sh '+key+';']
            instance_ids = [gpuinstance_id]
            print('running gpu analysis')
            out = execute_commands_on_linux_instances(ssm_client,commands,wd,instance_ids)
            print(out)
        else:
            ## We should analyze it! 
            ## Check if there is a config file: 
            local_contents = [objname.key for objname in my_bucket.objects.filter(Prefix = local_full)]
            assert (local_full+'/'+'config.py' in local_contents), 'We need a config file to analyze data.'
            
            ## Check relevant ec2 instance state: 
            start_instance_if_stopped(video_instance)
                
            ## Make analysis folder if does not exist already: 
            analysis_path = local_full+'/'+'analysis_folder/'
            try:
                s3_client.head_object(Bucket = bucket,Key = analysis_path)
            
            except ClientError:
                s3_client.put_object(Bucket = bucket,Key = analysis_path)
            
            ## Send command to EC2: 
            
            commands = ['echo $PWD; cd home/ec2-user/; ls; bin/run.sh '+key+';']
            wd = ['~/bin']
            instance_ids = [vidinstance_id]
            print('running video analysis')
            out = execute_commands_on_linux_instances(ssm_client,commands, wd, instance_ids)
            print(out)
  
            
            
            
            
            

    
        
    
    # ## We want to check if there are unanalyzed videos and a config file in the local directory. 

    # ## Look at the other files in the local directory: 
    # local_contents = [objname.key for objname in my_bucket.objects.filter(Prefix = local_full)]

    # ## Check if there is a config file: 
    # assert ('config.py' in local_contents), 'We need a config file to analyze data.'
    
    # ## Check if there is an analysis subdirectory: 
    
    
    

def handler(event,context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        process_upload(key,bucket)

