import pytest
import time
import localstack_client.session
import boto3
from botocore.exceptions import ClientError
import ncap_iac.ncap_blueprints.dev_utils.develop_blueprint as develop_blueprint
import os

timeout_init = 5
real_test_instance = "i-0ce3833f4cce8fcdf"
session = localstack_client.session.Session()
ec2_resource_local = session.resource("ec2")  
ec2_client_local = session.client("ec2")  

@pytest.fixture()
def use_devcred(monkeypatch):
    monkeypatch.setattr(develop_blueprint,"ec2_resource",boto3.Session(profile_name = "testdev").resource("ec2"))
    monkeypatch.setattr(develop_blueprint,"ec2_client",boto3.Session(profile_name = "testdev").client("ec2"))

loc = os.path.dirname(os.path.abspath(__file__))
fixturetemplate = os.path.join(loc,"fixtures")

@pytest.fixture()
def create_realinstance(monkeypatch):
    """Creates a real instance for the purpose of getting and modifying tags 

    """
    ec2_resource = boto3.resource("ec2") ## These can be created with default profile
    ec2_client= boto3.client("ec2")
    output = ec2_resource.create_instances(ImageId="ami-0bd85124dbe51618d",
            InstanceType= "t2.micro",
            MinCount = 1,
            MaxCount = 1,
            TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout_init)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout_init)}]}]
            )
    waiter = ec2_client.get_waiter('instance_exists')
    waiter.wait(InstanceIds = [output[0].instance_id])

    yield output
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id])

@pytest.fixture()
def create_mockinstance(monkeypatch):
    """Creates a mock instance for the purpose of getting and modifying tags. BEWARE: As this spins up a localstack instance, is a check of function only, not permissions. 

    """
    session = localstack_client.session.Session()
    ec2_resource = session.resource("ec2")  
    ec2_client = session.client("ec2")  
    monkeypatch.setattr(develop_blueprint,"ec2_resource",session.resource("ec2"))
    monkeypatch.setattr(develop_blueprint,"ec2_client",session.client("ec2"))
    output = ec2_resource.create_instances(ImageId="garbage",
            InstanceType= "t2.micro",
            MinCount = 1,
            MaxCount = 1,
            TagSpecifications= [{"ResourceType":"volume","Tags":[{"Key":"Timeout","Value":str(timeout_init)}]},{"ResourceType":"instance","Tags":[{"Key":"Timeout","Value":str(timeout_init)}]}]
            )
    yield output
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds = [instance_id])
    
def test_get_time(create_mockinstance):
    inst_id = create_mockinstance[0].instance_id
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(inst_id)
    time.sleep(2)
    lifetime = devami.get_lifetime()
    phrases = ["Instance has been on for","minutes and","seconds. Will be stopped in","minutes and","seconds with the current timeout"] 
    for p in phrases:
        assert p in lifetime

def test_extend_time(create_mockinstance):
    inst_id = create_mockinstance[0].instance_id
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(inst_id)
    time.sleep(2)
    lifetime = devami.extend_lifetime(10)
    instance_info = ec2_client_local.describe_instances(InstanceIds=[devami.instance.instance_id])
    info_dict = instance_info["Reservations"][0]["Instances"][0]
    tags = info_dict["Tags"]
    tagdict = {d["Key"]:d["Value"] for d in tags}
    timeout = int(tagdict["Timeout"])
    assert timeout == 10+timeout_init
       
def test_addtag_permissions_unauth(use_devcred,create_realinstance):       
    """In this test, we care about user permissions. So, we will use dryrun to simulate attaching tags to an existing instance in this account. We will not use localstack. 

    """
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_realinstance[0].instance_id) 
    try:
        devami.change_owner("arn:/user",DryRun=True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "UnauthorizedOperation"

def test_addtag_permissions_auth(use_devcred,create_realinstance):       
    """In this test, we care about user permissions. So, we will use dryrun to simulate attaching tags to an existing instance in this account. We will not use localstack. 

    """
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_realinstance[0].instance_id) 
    try:
        devami.extend_lifetime(10,DryRun = True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "DryRunOperation"
    
def test_start_devinstance(use_devcred,create_mockinstance):
    waiter = ec2_client_local.get_waiter('instance_running')
    waiter.wait(InstanceIds = [create_mockinstance[0].instance_id])
    ec2_client_local.stop_instances(InstanceIds=[create_mockinstance[0].instance_id])
    waiter = ec2_client_local.get_waiter('instance_stopped')
    waiter.wait(InstanceIds = [create_mockinstance[0].instance_id])
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    message = devami.start_devinstance(timeout = 100)
    assert message == "Instance is now in state: running"
    instance_info = ec2_client_local.describe_instances(InstanceIds=[devami.instance.instance_id])
    info_dict = instance_info["Reservations"][0]["Instances"][0]
    tags = info_dict["Tags"]
    tagdict = {d["Key"]:d["Value"] for d in tags}
    timeout = int(tagdict["Timeout"])
    assert timeout == 100

def test_stop_devinstance(use_devcred,create_mockinstance):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    message = devami.stop_devinstance()
    assert message == "Instance is now in state: stopped"

def test_terminate_devinstance(use_devcred,create_mockinstance):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    message = devami.terminate_devinstance() 
    assert message == "No state change."
    message = devami.terminate_devinstance(force = True) 
    assert message == "Instance is now in state: terminated"

def test_create_devami(use_devcred,create_mockinstance):
    aminame = "test-create-devami"
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    devami.create_devami(aminame)
    ami_id = devami.ami_hist[0]["ImageId"] 
    out = ec2_client_local.describe_images(ImageIds = [ami_id])
    assert out["Images"][0]

def test_create_then_terminate(use_devcred,create_mockinstance):
    aminame = "test-create-devami"
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    devami.create_devami(aminame)
    message = devami.terminate_devinstance() 
    assert message == "Instance is now in state: terminated"

def test_create_then_launch(use_devcred,create_mockinstance):
    aminame = "test-create-devami"
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    devami.create_devami(aminame)
    with pytest.raises(AssertionError):
        devami.launch_devinstance()

def test_create_terminate_launch(use_devcred,create_mockinstance):
    aminame = "test-create-devami"
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    devami.assign_instance(create_mockinstance[0].instance_id) 
    devami.create_devami(aminame)
    devami.terminate_devinstance()
    devami.launch_devinstance(ami=devami.ami_hist[0]["ImageId"])
    assert devami.instance.image_id == devami.ami_hist[0]["ImageId"]


