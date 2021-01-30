import boto3 
import os
import json
import localstack_client.session
from botocore.exceptions import ClientError
import sys
import zipfile

environment = {
        "Variables":{
            "graceperiod":"10",     
            "exemptlist":"i-029339d0ff4fa4318,i-0ce3833f4cce8fcdf,i-0c366d0e991bc6fde,i-04a5f4794bafda3b1,i-0a7b60fe2661444da",     
            "dryrun":"0",
            "topicarn": "arn:aws:sns:us-east-1:739988523141:EC2_Instance_Sweeper",
            "localstack":"0",
                    }
                }

if environment["Variables"]["localstack"] == "1":
    lambda_client = localstack_client.session.Session().client("lambda") 
    ec2_client = localstack_client.session.Session().client("ec2")
    ec2_resource = localstack_client.session.Session().resource("ec2")

if environment["Variables"]["localstack"] == "0":
    lambda_client = boto3.client("lambda") 

name = "ec2-rogue-killer"
runtime = "python3.8"
role = "arn:aws:iam::739988523141:role/lambda_dataflow"
handler = "lambda_function_imported.lambda_handler"

def create_zip(filename):
    z = zipfile.ZipFile("lambda_zipped.zip",mode="w").write(filename)

def deploy_package():
    lambda_client.create_function(
            FunctionName=name,
            Runtime = runtime,
            Role = role,
            Handler = handler,
            Code={"ZipFile":open('./lambda_zipped.zip','rb').read()},
            Description = "EC2 instance monitoring function written locally",
            Timeout = 900,
            MemorySize=128,
            Environment = environment
        )

def update_lambda_code(filename):
    response = lambda_client.update_function_code(
            FunctionName= name,
            ZipFile=open('./lambda_zipped.zip','rb').read()
            )

def update_lambda_env_vars():
    response = lambda_client.update_function_configuration(
            FunctionName=name,
            Environment = environment)

def test_lambda():
    invocationtype = "RequestResponse"
    payload = '{}'
    response = lambda_client.invoke(
            FunctionName=name,
            Payload = payload
            )
    return response

def test_lambda_rogue_active():
    ## create an instance
    output = ec2_resource.create_instances(ImageId='garbage', InstanceType='t2.micro',
      MinCount=1,
      MaxCount=1,
      TagSpecifications=[
     {'ResourceType':'volume', 
      'Tags':[{'Key':'Timeout',  'Value':str(-1)}]}, {'ResourceType':'instance',  'Tags':[{'Key':'Timeout',  'Value':str(-1)}]}])

    invocationtype = "RequestResponse"
    payload = '{}'
    response = lambda_client.invoke(
            FunctionName=name,
            Payload = payload
            )

    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    return response

if __name__ == "__main__":
    filename = sys.argv[1]
    create_zip(filename)
    try:
        deploy_package()
        print("deployed new package")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            update_lambda_code(filename)
            update_lambda_env_vars()
            print("updating existing package")
        else:
            print("unhandled error: {}".format(e.response["Error"]))
            raise
    if environment["Variables"]["localstack"] == "1":    
        response = test_lambda()
        message = json.loads(response['Payload'].read().decode("utf-8"))
        print("response payload:",message)
        assert message == "no instances active for longer than 10 minutes"
        response = test_lambda_rogue_active()
        message = json.loads(response['Payload'].read().decode("utf-8"))
        print("response payload:",message)






    


