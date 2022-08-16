"""
Script to test tagging of ec2 instances. 
"""
import boto3
from botocore.exceptions import ClientError
import ncap_iac.protocols.utilsparam.ec2 as ec2 
import ncap_iac.protocols.utilsparam.env_vars
import os

master = boto3.session.Session(profile_name="default")
dev = boto3.session.Session(profile_name="developer")
sts_client = master.client("sts")

class logger():
    def __init__(self):
        self.value = []
    def append(self,value):
        pass
    def write(self):
        pass

if __name__ == "__main__":
    try:
        ec2.launch_new_instances_with_tags("t2.micro","ami-0ff8a91507f77f867",logger(),8,8,duration = 5)
        print("success")
    except ClientError as e:
        message = e.response["Error"]["Message"]
        print("failure")

