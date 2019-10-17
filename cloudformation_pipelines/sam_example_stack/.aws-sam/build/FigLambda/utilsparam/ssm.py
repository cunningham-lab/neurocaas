import boto3
import os

#from .config import REGION, EXECUTION_TIMEOUT

# Boto3 Resources & Clients
ssm_client = boto3.client('ssm', region_name=os.environ['REGION']) 


def execute_commands_on_linux_instances(commands, 
                                        instance_ids, 
                                        working_dirs,
                                        log_bucket_name,
                                        log_path):
    """Runs commands on remote linux instances
    :param client: a boto/boto3 ssm client
    :param commands: a list of one string,  a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :param working_dires: a list of one directory (string) where commands are executed on each instance
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """
    return ssm_client.send_command(
        DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
        Parameters={'commands': commands, 
                    "workingDirectory":working_dirs,
                    "executionTimeout":[os.environ['SSM_TIMEOUT'] for command in commands]},
        InstanceIds=instance_ids,
        OutputS3BucketName=log_bucket_name,
        OutputS3KeyPrefix=log_path
    )
