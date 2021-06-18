import pytest
import localstack_client.session
import logging
import os
import ncap_iac.protocols.utilsparam.ec2 as ec2
import ncap_iac.protocols.utilsparam.env_vars

session = localstack_client.session.Session()

ec2_client = session.client("ec2")
ec2_resource = session.resource("ec2")

@pytest.fixture
def patch_boto3_ec2(monkeypatch):
    ec2_client = session.client("ec2")
    ec2_resource = session.resource("ec2")
    monkeypatch.setattr(ec2,"ec2_resource",session.resource("ec2"))
    monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
    yield "patching resources."

@pytest.fixture
def create_ami():
    instance = ec2_resource.create_instances(MaxCount = 1,MinCount=1)[0]
    ami = ec2_client.create_image(InstanceId=instance.instance_id,Name = "dummy")
    yield ami["ImageId"]

@pytest.fixture
def loggerfactory():
    class logger():
        def __init__(self):
            self.logs = []
        def append(self,message):    
            self.logs.append(message)
        def write(self): 
            logging.warning("SEE Below: \n"+str("\n".join(self.logs)))
    yield logger()        


def test_launch_new_instances(patch_boto3_ec2,loggerfactory,create_ami):
    instance_type = "t2.micro"
    ami = create_ami 
    logger = loggerfactory 
    number = 1
    add_size = 200
    duration = None
    message = patch_boto3_ec2

    response = ec2.launch_new_instances(instance_type,ami,logger,number,add_size,duration)
    info = ec2_client.describe_instances(InstanceIds=[response[0].id])

    assert len(info["Reservations"][0]["Instances"]) == 1
    info_instance = info["Reservations"][0]["Instances"][0]
    
    assert info_instance["ImageId"] == ami
    assert info_instance["InstanceType"] == instance_type
    
def test_launch_new_instances_spot(patch_boto3_ec2,loggerfactory,create_ami):
    """This doesn't actually check if the instance is spot, just that the code works.   
    """
    instance_type = "t2.micro"
    ami = create_ami 
    logger = loggerfactory 
    number = 1
    add_size = 200
    duration = 20
    message = patch_boto3_ec2

    response = ec2.launch_new_instances(instance_type,ami,logger,number,add_size,duration)
    info = ec2_client.describe_instances(InstanceIds=[response[0].id])

    assert len(info["Reservations"][0]["Instances"]) == 1
    info_instance = info["Reservations"][0]["Instances"][0]
    
    assert info_instance["ImageId"] == ami
    assert info_instance["InstanceType"] == instance_type

@pytest.mark.parametrize("duration,value",([10,"10"],[None,"20"]))
def test_launch_new_instances_with_tags(patch_boto3_ec2,loggerfactory,create_ami,duration,value):
    instance_type = "t2.micro"
    ami = create_ami 
    logger = loggerfactory 
    number = 1
    add_size = 200
    message = patch_boto3_ec2

    response = ec2.launch_new_instances_with_tags(instance_type,ami,logger,number,add_size,duration)
    info = ec2_client.describe_instances(InstanceIds=[response[0].id])

    assert len(info["Reservations"][0]["Instances"]) == 1
    info_instance = info["Reservations"][0]["Instances"][0]
    
    assert info_instance["ImageId"] == ami
    assert info_instance["InstanceType"] == instance_type
    assert info_instance["Tags"] == [
            {"Key":"PriceTracking","Value":"On"},
            {"Key":"Timeout","Value":value}
            ]
    
