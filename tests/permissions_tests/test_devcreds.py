import pytest
import localstack_client.session
import boto3
from botocore.exceptions import ClientError
import pkg_resources
from tagcombos import *

sts_client = boto3.client("sts")

permissions_path = pkg_resources.resource_filename("ncap_iac","permissions/dev_policy.json")

@pytest.mark.parametrize("tags,responsecodes", ## We import tag lists from the tagcombos module for cleanness here.  
        [
        (wrong_tags,"UnauthorizedOperation"),
        (right_tags,"DryRunOperation"),
        (right_tags_instance_only,"UnauthorizedOperation"),
        (right_tags_volume_only,"UnauthorizedOperation"),
        (right_tags_wrong_val,"UnauthorizedOperation"),
        ])
def test_user_policy(tags,responsecodes):
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
                TagSpecifications = tags)
    except ClientError as e:
        assert e.response["Error"]["Code"] == responsecodes


