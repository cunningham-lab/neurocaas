from troposphere import Ref,GetAtt,Template,Output,Join,Sub,AWS_ACCOUNT_ID
from troposphere.codecommit import Repository,Trigger,Code,S3
#from troposphere.s3 import Bucket,Rules,S3Key,Filter
#from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
#from troposphere.cloudformation import CustomResource 
#from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import secrets
import os

## Function that takes in a bash script and a config file (for data processing, not for infrastructure). 
## Setup for pipelines will all the the same components: 
## 1. A CodeCommit repo that contains the scripts used to forward the pipeline.
## 2. A Lambda function that will auto-update AMIs according to activity in the CodeCommit repo and the config file that you provide. 
## 3. A 

## First define a function that loads the relevant config file into memory: 
class NCAPDeployTemplate(object):
    """
    Inputs: 

    config: The config file that users will pass along with submit.jsons 
    script: The script that will execute on the remote instance. 
    """
    def __init__(self,config,script):
        self.config = config 
        self.script = script

        ## 
        self.template = self.initialize_template()

        ### 
        self.commitlambda = self.create_lambda()

        ###
        Bucket = 'ncapcodecommitinit'
        Key = 'test_repo.zip'
        self.repo = self.create_repo(Bucket,Key)

        self.link_resources()


    def initialize_template(self):
        template = Template()
        ## Apply a transform to use serverless functions. 
        template.set_transform("AWS::Serverless-2016-10-31")
        return template

    def create_lambda(self):
        ## Now add to a lambda function: 
        function = Function('CodeLambda',
                CodeUri = '../../lambda_repo',
                Runtime = 'python3.6',
                Handler = 'updateami.commithandler',
                Description = 'Lambda Function pushing code changes for NCAP',
                MemorySize = 128,
                Timeout = 90,
                Role = 'arn:aws:iam::739988523141:role/lambda_dataflow', ## TODO: Create this in template
                Events= {})         
        codelamb = self.template.add_resource(function)
        return codelamb

    ##TODO::: Create the code to initialize a repo from the zip file we created. 
    def create_repo(self,bucket,key):
        ## First we need to create an S3 reference: 
        S3ref = S3(Bucket =bucket,Key = key)
        Coderef = Code(S3 = S3ref)
        Triggerref = Trigger(Name='TriggerBaseRepo',
                CustomData = 'Repo initialization for NCAP development',
                DestinationArn = GetAtt(self.commitlambda,'Arn'),
                Branches = ['master'],
                Events = ['all'])
        Repo = Repository('PipelineBaseRepo',Code = Coderef,
                RepositoryDescription = 'Initialization of repo for dynamic AMI updates.',
                RepositoryName = 'TestDevRepo',
                Triggers = [Triggerref]
                )
        repo_attached = self.template.add_resource(Repo)
        return repo_attached

    def link_resources(self):
        ## Attach specific permissions to invoke this lambda function as well. 
        cwpermission = Permission('CCPermissions',
                Action = 'lambda:InvokeFunction',
                Principal = 'codecommit.amazonaws.com',
                FunctionName = Ref(self.commitlambda),
                SourceArn = GetAtt(self.repo,'Arn'), 
                SourceAccount = Ref(AWS_ACCOUNT_ID))
        self.template.add_resource(cwpermission)
        
        ## Because this lambda function gets invoked by an unknown target, we need to take care of its log group separately. 
        
        figloggroup = LogGroup('FignameLogGroup',LogGroupName=Sub("/aws/lambda/${CodeLambda}"))
        self.template.add_resource(figloggroup)
        
if __name__ == '__main__':

    Customtemplate = NCAPDeployTemplate('dummycofig','dummyscript')
    with open('test_template.json','w') as f:
        print(Customtemplate.template.to_json(),file = f)



    


        
        
