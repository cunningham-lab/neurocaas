import time
import os
from math import ceil
#from .env_vars import *

import boto3
import botocore

#from .config import IAM_ROLE, KEY_NAME, SECURITY_GROUPS, SHUTDOWN_BEHAVIOR

# Boto3 Resources & Clients
ec2_resource = boto3.resource('ec2')

def get_instance(instanceid,logger):
    """ Gets the instance given an instance id.  """
    instance = ec2_resource.Instance(instanceid)
    logger.append("Acquiring instance with id {}".format(instanceid))

    return instance

def start_instance_if_stopped(instance, logger):
    """ Check instance state, start if stopped & wait until ready """
    
    # Check & Report Status
    state = instance.state['Name']
    logger.append("Instance State: {}...".format(state))
    
    # If not running, run:
    if state != 'running':
        logger.append("Starting Instance...")
        instance.start()
        instance.wait_until_running()
        time.sleep(60)
        logger.append('Instance started!')
        

def start_instances_if_stopped(instances, logger):
    """ Check instance state, start if stopped & wait until ready """
    for instance in instances: 
        
        # Check & Report Status
        state = instance.state['Name']
        logger.append("Instance State: {}...".format(state))
        
        # If not running, run:
        if state != 'running':
            try:
                logger.append("Starting Instance...")
                instance.start()
                instance.wait_until_running()
                logger.append('Instance started!')
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "UnsupportedOperation":
                    logger.append("Spot Instance, cannot be started manually. .")
                    ##TODO: figure out if you have to wait for this additionally. 
                    instance.wait_until_running()
                    logger.append('Instance started!')
                else:
                    print("unhandled error, quitting")
                    logger.append("unhandled error during job start, quitting")
                    logger.write()
                    raise
    time.sleep(60)
    logger.append("Instances Initialized")

def launch_new_instance(instance_type, ami, logger):
    """ Script To Launch New Instance From Image """
    logger.append("Acquiring new {} instance from {} ...".format(instance_type, ami))
    
    instances = ec2_resource.create_instances(
        ImageId=ami,
        InstanceType=instance_type,
        IamInstanceProfile={'Name': os.environ['IAM_ROLE']},
        MinCount=1,
        MaxCount=1,
        KeyName=os.environ['KEY_NAME'],
        SecurityGroups=[os.environ['SECURITY_GROUPS']],
        InstanceInitiatedShutdownBehavior=os.environ['SHUTDOWN_BEHAVIOR']
    )
    logger.append("New instance {} created!".format(instances[0]))
    return instances[0]

def launch_new_instances(instance_type, ami, logger, number, duration = None):
    """ Script To Launch New Instance From Image
    If duration parameter is specified, will launch the appropriate cost instance
    If number parameter is specified, will try to launch the requested number of instances. If not available, then will return none. 
    """
    logger.append("Acquiring new {} instances from {} ...".format(instance_type, ami))

    ## First parse the duration and figure out if there's anything we can do for it. 
    ## The duration should be given as the max number of minutes the job is expected to take. 
    if type(duration) == int:
        hours = ceil(duration/60)
        minutes_rounded = hours*60
        if minutes_rounded > 360:
            spot_duration = None
        else:
            spot_duration = minutes_rounded 
    elif duration is None:
        spot_duration = None
    else:
        logger.append("duration parameter is not valid. Must be an integer representing max number of minutes expected.")
        logger.write()
        raise ValueError("duration not valid.")

    ## Now we will take the parsed duration and use it to launch instances.  
    
    if spot_duration is None:
        logger.append("save not available (duration not given or greater than 6 hours). Launching standard instance.")
        logger.write()
        instances = ec2_resource.create_instances(
            ImageId=ami,
            InstanceType=instance_type,
            IamInstanceProfile={'Name': os.environ['IAM_ROLE']},
            MinCount=number,
            MaxCount=number,
            KeyName=os.environ['KEY_NAME'],
            SecurityGroups=[os.environ['SECURITY_GROUPS']],
            InstanceInitiatedShutdownBehavior=os.environ['SHUTDOWN_BEHAVIOR']
        )

    else:
        logger.append("reserving save instance with for {} minutes".format(spot_duration))
        marketoptions = {"MarketType":'spot',
                "SpotOptions":{
                    "SpotInstanceType":"one-time",
                    "BlockDurationMinutes":spot_duration,
                    }
                
                }
        try:
            instances = ec2_resource.create_instances(
                ImageId=ami,
                InstanceType=instance_type,
                IamInstanceProfile={'Name': os.environ['IAM_ROLE']},
                MinCount=number,
                MaxCount=number,
                KeyName=os.environ['KEY_NAME'],
                SecurityGroups=[os.environ['SECURITY_GROUPS']],
                InstanceInitiatedShutdownBehavior=os.environ['SHUTDOWN_BEHAVIOR'],
                InstanceMarketOptions = marketoptions
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "InsufficientInstanceCapacity":
                logger.append("save not available (beyond available aws capacity). Launching standard instance.")
                logger.write()
                instances = ec2_resource.create_instances(
                    ImageId=ami,
                    InstanceType=instance_type,
                    IamInstanceProfile={'Name': os.environ['IAM_ROLE']},
                    MinCount=number,
                    MaxCount=number,
                    KeyName=os.environ['KEY_NAME'],
                    SecurityGroups=[os.environ['SECURITY_GROUPS']],
                    InstanceInitiatedShutdownBehavior=os.environ['SHUTDOWN_BEHAVIOR']
                )
            else:
                logger.append("unhandled error while launching save instances. contact admin.")
                raise ValueError("Unhandled exception")

    [logger.append("New instance {} created!".format(instances[i])) for i in range(number)]
    logger.write()
    return instances

def count_active_instances(instance_type):
    """
    Counts how many active [including transition in and out] isntances there are of a certain type. 
    Inputs:
    instance_type (str): string specifying instance type
    Outputs: 
    (int): integer giving number of instances currently active. 
    """
    instances = ec2_resource.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running','pending','stopping','shutting-down']},{'Name':'instance-type',"Values":[instance_type]}])
    return len([i for i in instances])
