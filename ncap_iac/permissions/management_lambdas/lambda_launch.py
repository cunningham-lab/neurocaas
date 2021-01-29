import boto3 
import os
import json
import localstack_client.session
from botocore.exceptions import ClientError
import sys
import zipfile

lambda_client = localstack_client.session.Session().client("lambda") 

#lambda_client = boto3.client("lambda")

environment = {
        "Variables":{
            "graceperiod":"10",     
            "exemptlist":"i-029339d0ff4fa4318,i-0c366d0e991bc6fde,i-04a5f4794bafda3b1,i-0a7b60fe2661444da",     
            "dryrun":"1",
            "topicarn": "arn:aws:sns:us-east-1:739988523141:EC2_Instance_Sweeper",
            "localstack":"1",
            "AWS_ACCCESS_KEY_ID":"foo",
            "AWS_SECRET_ACCESS_KEY":"bar"
                    }
                }

name = "ec2-instance-killer-local"
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
    response = test_lambda()
    print(response)
    print(json.loads(response['Payload'].read().decode("utf-8")),"response payload")




    


