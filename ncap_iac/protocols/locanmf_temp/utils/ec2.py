import time

import boto3

from .config import IAM_ROLE, KEY_NAME, SECURITY_GROUPS, SHUTDOWN_BEHAVIOR

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
        time.sleep(60)  # TODO: test if we really need this
        logger.append('Instance started!')


def launch_new_instance(instance_type, ami, logger):
    """ Script To Launch New Instance From Image """
    logger.append("Acquiring new {} instance from {} ...".format(instance_type, ami))
    instances = ec2_resource.create_instances(
        ImageId=ami,
        InstanceType=instance_type,
        IamInstanceProfile={'Name': IAM_ROLE},
        MinCount=1,
        MaxCount=1,
        KeyName=KEY_NAME,
        SecurityGroups=SECURITY_GROUPS,
        InstanceInitiatedShutdownBehavior=SHUTDOWN_BEHAVIOR
    )
    logger.append("New instance {} created!".format(instances[0]))
    return instances[0]
