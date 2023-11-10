## test if ssm list commands correctly picks up unmanaged, managed running and completed run command jobs. 
## CAUTION: EXTREMELY SLOW. About 2 minutes per test, about 
import time
import os
import pytest
import boto3 
env_vars = {
            "graceperiod":"10",     
            "exemptlist":"i-029339d0ff4fa4318,i-0c366d0e991bc6fde,i-04a5f4794bafda3b1,i-0a7b60fe2661444da",     
            "dryrun":"1",
            "topicarn": "arn:aws:sns:us-east-1:739988523141:EC2_Instance_Sweeper",
            "localstack":"0",
            "AWS_ACCCESS_KEY_ID":"foo",
            "AWS_SECRET_ACCESS_KEY":"bar",
            "LOCALSTACK_HOSTNAME": "localhost"
            }
for var in env_vars.items():
    os.environ[var[0]] = var[1]
import ncap_iac.permissions.management_lambdas.lambda_function_imported as lambda_function_imported

ec2_resource = boto3.resource("ec2") ## These can be created with default profile
ec2_client= boto3.client("ec2")
ssm_client = boto3.client("ssm")

timeout = 100

@pytest.fixture
def get_uncommanded_instance():
    """Get an instance not commanded by ssm. 

    """
    instances = ec2_resource.create_instances(ImageId="ami-0bd85124dbe51618d",
            InstanceType= "t2.micro",
            MinCount = 1,
            MaxCount = 1,
            TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout)}]}]
            )
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds = [instances[0].instance_id],WaiterConfig={"Delay":5})
    yield instances
    instance_id = instances[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id])

@pytest.fixture
def get_commanded_instance_running():
    instances = ec2_resource.create_instances(
        ImageId="ami-0bd85124dbe51618d",
        InstanceType="t2.micro",
        IamInstanceProfile={'Name':"SSMRole"},
        MinCount=1,
        MaxCount=1,
        TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout)}]}],
        InstanceInitiatedShutdownBehavior="terminate"
        )
    waiter = ec2_client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds = [instances[0].instance_id],WaiterConfig={"Delay":5})
    ssm_client.send_command(
            DocumentName = "AWS-RunShellScript",
            InstanceIds = [instances[0].instance_id],
            Parameters={'commands': ["sleep 100"], 
                        "executionTimeout":[str(200)]},
            )
    yield instances
    instance_id = instances[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id])

@pytest.fixture
def get_commanded_instance_done():
    instances = ec2_resource.create_instances(
        ImageId="ami-0bd85124dbe51618d",
        InstanceType="t2.micro",
        IamInstanceProfile={'Name':"SSMRole"},
        MinCount=1,
        MaxCount=1,
        TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout)}]}],
        InstanceInitiatedShutdownBehavior="terminate"
        )
    waiter = ec2_client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds = [instances[0].instance_id],WaiterConfig={"Delay":5})
    ssm_client.send_command(
            DocumentName = "AWS-RunShellScript",
            InstanceIds = [instances[0].instance_id],
            Parameters={'commands': ["ls"], 
                        "executionTimeout":[str(10)]},
            )
    yield instances
    instance_id = instances[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id],WaiterConfig={"Delay":5})

@pytest.fixture
def get_commanded_instance_timeout():
    """Tests associated with this timeout don't terminate. 

    """
    instances = ec2_resource.create_instances(
        ImageId="ami-0bd85124dbe51618d",
        InstanceType="t2.micro",
        IamInstanceProfile={'Name':"SSMRole"},
        MinCount=1,
        MaxCount=1,
        TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout)}]}],
        InstanceInitiatedShutdownBehavior="terminate"
        )
    waiter = ec2_client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds = [instances[0].instance_id],WaiterConfig={"Delay":5})
    ssm_client.send_command(
            DocumentName = "AWS-RunShellScript",
            TimeoutSeconds = 30,
            InstanceIds = [instances[0].instance_id],
            Parameters={'commands': ["sleep 100; sleep 10"], 
                        "executionTimeout":[str(1)]},
            )
    time.sleep(60)
    yield instances
    instance_id = instances[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id])


def test_nocommand_running(get_commanded_instance_running):    
    """Test the nocommand settings with real aws. 

    """
    running_command = ec2_client.describe_instances(InstanceIds=[get_commanded_instance_running[0].id])["Reservations"][0]["Instances"][0]

    assert not lambda_function_imported.no_command(running_command)

def test_nocommand_done(get_commanded_instance_done,get_uncommanded_instance,get_commanded_instance_timeout):    
    """Test the nocommand settings with real aws. 

    """
    done_command = ec2_client.describe_instances(InstanceIds=[get_commanded_instance_done[0].id])["Reservations"][0]["Instances"][0]

    assert lambda_function_imported.no_command(done_command)

def test_nocommand_uncommanded(get_uncommanded_instance):    
    """Test the nocommand settings with real aws. 

    """
    no_command = ec2_client.describe_instances(InstanceIds=[get_uncommanded_instance[0].id])["Reservations"][0]["Instances"][0]

    assert lambda_function_imported.no_command(no_command)

def test_nocommand_timeout(get_commanded_instance_timeout):    
    """Test the nocommand settings with real aws. 

    """
    timeout_command = ec2_client.describe_instances(InstanceIds=[get_commanded_instance_timeout[0].id])["Reservations"][0]["Instances"][0]

    assert lambda_function_imported.no_command(timeout_command)
    
