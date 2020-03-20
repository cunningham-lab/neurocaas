import boto3
import json
import urllib.parse

# 1. Run CreateRole to attach a trust agreement to a role. 
# 2. Run CreatePolicy to create a new managed policy from the policy document. 
# 3. Load in the role to a new object, and Run attach policy to attach the policy we created in step 2. 
# 4. Use the role to generate cloudwatch event calls. 

iam_client = boto3.client('iam')

def create_cloudwatch_role(Rolename):
    ## First get the trustagreement: 
    with open("../policies/cloudwatch_events_assume_role_doc.json",'r') as f:
        obj = json.load(f) 
        trustencoded = json.dumps(obj)
        #trustencoded = urllib.parse.urlencode(obj)

    response = iam_client.create_role(
            RoleName=Rolename,
            AssumeRolePolicyDocument = trustencoded,
            Description = 'Trust agreement to shunt cloudwatch event logs to lambda.'
            )
    return response

def create_cloudwatch_managedpolicy(Policyname):
    ## First get the policy:
    with open("../policies/cloudwatch_events_policy_doc.json","r") as f:
        obj = json.load(f)
        policyencoded = json.dumps(obj) 
    response = iam_client.create_policy(
            PolicyName = Policyname,
            PolicyDocument = policyencoded,
            Description = 'Policy needed to take cloudwatch events.'
            )
    return response

def attach_policy_to_role(Rolename,Policyarn):
    response = iam_client.attach_role_policy(
            RoleName=Rolename,
            PolicyArn = Policyarn)


