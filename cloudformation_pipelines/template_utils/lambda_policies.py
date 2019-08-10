## A module to deal with lambda functions template creation. 
from troposphere.iam import ManagedPolicy,Policy
from troposphere import Join,Ref,AWS_STACK_NAME
import json

## Helper function: Base policy for lambda functions. From https://raw.githubusercontent.com/gilt/cloudformation-helpers/master/create_cloudformation_helper_functions.template

# returns the base policy for a lambda function. 
def lambda_basepolicy(policyname):
    with open("policies/lambda_role_base_policy_doc_minimal.json",'r') as f:
        policydoc = json.load(f)

    policy = ManagedPolicy(policyname,
            Description=Join(" ",["Base Policy for all lambda function roles in",Ref(AWS_STACK_NAME)]),
            PolicyDocument = policydoc)
    return policy

# returns the policy that allows lambda functions to assume this role. 
def lambda_writeS3(policyname):
    with open("policies/lambda_role_write_s3_doc.json") as f:
        policydoc = json.load(f)

    policy = Policy(PolicyName = 'write_s3_policy',PolicyDocument = policydoc)
    return policy


    

