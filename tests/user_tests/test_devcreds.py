import pytest
import localstack_client.session
import boto3
from botocore.exceptions import ClientError
import pkg_resources

sts_client = boto3.client("sts")

permissions_path = pkg_resources.resource_filename("ncap_iac","permissions/dev_policy.json")

def test_user_unauthorized():
    session = boto3.Session(profile_name = "testdev")
    ec2_client = session.client("ec2")
    ec2_resource = session.resource("ec2")
    try:
        ec2_resource.create_instances(
                ImageId= "ami-07ebfd5b3428b6f4d",
                InstanceType = "t2.micro",
                MinCount = 1,
                MaxCount = 1,
                DryRun=True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "UnauthorizedOperation"

def test_user_tag_exists():
    session = boto3.Session(profile_name = "testdev")
    ec2_client = session.client("ec2")
    ec2_resource = session.resource("ec2")
    try:
        ec2_resource.create_instances(
                ImageId= "ami-07ebfd5b3428b6f4d",
                InstanceType = "t2.micro",
                MinCount = 1,
                MaxCount = 1,
                DryRun=True,
                TagSpecifications = [
                    {
                        "ResourceType":"instance",
                        "Tags":[
                        {
                            "Key":"a",
                            "Value": "b"
                        },
                        ]
                    }
                ]
            )
    except ClientError as e:
        assert e.response["Error"]["Code"] == "UnauthorizedOperation"

def test_user_tag_correct():
    session = boto3.Session(profile_name = "testdev")
    ec2_client = session.client("ec2")
    ec2_resource = session.resource("ec2")
    try:
        ec2_resource.create_instances(
                ImageId= "ami-07ebfd5b3428b6f4d",
                InstanceType = "t2.micro",
                MinCount = 1,
                MaxCount = 1,
                DryRun=True,
                TagSpecifications = [
                    {
                        "ResourceType":"volume",
                        "Tags":[
                        {
                            "Key":"PriceTracking",
                            "Value": "On"
                        },
                        {
                            "Key":"Timeout",
                            "Value":"6",
                        },
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
                            "Value":"6",
                        },
                        ]
                    }
                ]
            )
    except ClientError as e:
        try:
            assert e.response["Error"]["Code"] == "DryRunOperation"
        except AssertionError:    
            message = e.response["Error"]["Message"].split("Encoded authorization failure message:")[-1]
            print(message)
            out = sts_client.decode_authorization_message(EncodedMessage = message)
            print(out)
        
            assert 0 
