from troposphere import Ref,GetAtt,Template,Output,Join,Sub,AWS_STACK_NAME,AWS_REGION
from troposphere.s3 import Bucket,Rules,S3Key,Filter
from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
from troposphere.cloudformation import CustomResource 
from config_handler import NCAPTemplate
from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import secrets
import os
import boto3

## A template that takes in a config file describing the sets of users that will be using the template. Users are associated under a particular group name [corresponding to a path prefix], and have access to a bucket that will eventually consolidate all of their data uploads [not yet implemented].
class UserTemplate(NCAPTemplate):
    def __init__(self,filename):
        ## Clean filename input: 
        assert os.path.basename(filename) == "user_config_template.json", "Must pass a valid user template with filename 'user_config_template.json'."
        self.filename = filename 
        self.config = self.get_config(self.filename)
        self.template,self.mkdirfunc,self.deldirfunc = self.initialize_template()
        ## Now we iterate through affiliates and set up resources for each. 
        ## Set up iterative resources: 
        self.buckets = {} 
        self.users = {}
        for aff in self.config["UXData"]["Affiliates"]:
            ## we create a bucket for each affiliate 
            b_attached,b_name = self.add_user_bucket(aff)
            self.buckets[b_name] = b_attached
            ## TODO: Add folders in each of these buckets. 
            ## we create users for each affiliate
            self.generate_users(aff)
            ## Now we create a user group that allows us to write to this bucket, and the users necessary to do so. 

    ## Now initialize a template. this just involves applying the serverless transform and adding the resources necessary to get our custom resources up and running. 
    def initialize_template(self):
        template = Template()
        ## Apply a transform to use serverless functions. 
        template.set_transform("AWS::Serverless-2016-10-31")
        ## Make role for custom resources. 
        ## Initialize the resources necessary to make directories. 
        ## First get the trust agreement: 
        with open('policies/lambda_role_assume_role_doc.json',"r") as f:
            mkdirassume_role_doc = json.load(f)
        ## Base lambda policy
        base_policy = lambda_basepolicy("LambdaBaseRole")
        ## Write permissions for lambda to s3 
        write_policy = lambda_writeS3('LambdaWriteS3Policy')
        ## 
        template.add_resource(base_policy)
        mkdirrole = Role("S3MakePathRole",
                AssumeRolePolicyDocument=mkdirassume_role_doc,
                ManagedPolicyArns=[Ref(base_policy)],
                Policies = [write_policy])
        mkdirrole_attached = template.add_resource(mkdirrole)

        ## Get the lambda config parameters for initialization of the custom resource delete function [needs the region]
        lambdaconfig = self.config['Lambda']['LambdaConfig']

        ## Now we need to write a lambda function that actually does the work:  
        mkfunction = Function("S3PutObjectFunction",
                              CodeUri="../lambda_repo",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = template.add_resource(mkfunction)
        delfunction = Function("S3DelObjectFunction",
                               CodeUri="../lambda_repo",
                               Description= "Deletes Objects from S3",
                               Handler="helper.handler_deldir",
                               Environment = Environment(Variables=lambdaconfig),
                               Role=GetAtt(mkdirrole_attached,"Arn"),
                               Runtime="python3.6",
                               Timeout=30)
        delfunction_attached = template.add_resource(delfunction)
        ## Custom resource to delete for each: . 
        for aff in self.config["UXData"]["Affiliates"]:
            bucketname = aff["AffiliateName"]
            delresource = CustomResource('DeleteCustomResource'+bucketname,
                                 ServiceToken=GetAtt(delfunction_attached,"Arn"),
                                 BucketName = bucketname,
                                 DependsOn = 'PipelineBucket'+bucketname)
            template.add_resource(delresource)
        return template,mkfunction_attached,delfunction_attached

    def get_config(self,filename):
        with open(filename,'r') as f: 
            obj = json.load(f)
        ## Check top level attributes we care about exist:
        error = 0

        try:
            obj["UXData"]
        except Exception as e: 
            print("config file missing key attribute",e)
            error += 1 
        try: 
            obj["UXData"]["Affiliates"]
        except Exception as e: 
            print("config file missing key attribute",e)
            error += 1 
        ## Check that we have necessary info for each: 
        for aff in obj["UXData"]["Affiliates"]:
            try:
                type(aff["AffiliateName"]) == str
                type(aff["UserNames"]) == list
                type(aff["Pipelines"]) == list
                type(aff["PipelineDir"]) == list
                type(aff["ContactEmail"]) == str
            except Exception as e: 
                print("config file user data misconfigured, ", e)
                err +=1 
        return obj

    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True):
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True, 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        ## IMPORTANT: we will associate with each user a UserName (in the sense of the AWS parameter.)
        ## Doing so, we can reference existing users in other cfn stacks. An important and dire quirk to automated user creation is that creating the same IAM username in the same account in different regions can cause "unrecoverable data loss". To handle this, we will pass around usernames that are not postfixed, but will be converted under the hood to a username with a region associated. 
        username_region = username+self.config["Lambda"]["LambdaConfig"]["REGION"]

        user = User(affiliatename+'user'+str(username),UserName=username_region,Path="/"+affiliatename+'/')

        user_t = self.template.add_resource(user)

        if password == True:
            ## User can reset if desired
            ResetRequired = False
            default_password = secrets.token_hex(8)
            lp = LoginProfile(Password = default_password,PasswordResetRequired = ResetRequired)
            data['password'] = []
            data['password'].append({
                'password': default_password
                })
        
            self.template.add_output(Output('Password'+username,Value = default_password,Description = 'Default password of new user '+username + " in group "+affiliatename))
            user_t.LoginProfile = lp


        ## Now we generate access keys:  
        if accesskey == True:
            key = AccessKey('userkey'+username,UserName = Ref(user))
            self.template.add_resource(key)
            accesskey = Ref(key)
            secretkey = GetAtt(key,'SecretAccessKey')

            self.template.add_output(Output('AccessKey'+username,Value = accesskey,Description = 'Access Key of user: '+username + ' in group '+affiliatename))
            self.template.add_output(Output('SecretAccessKey'+username,Value = secretkey,Description = 'Secret Key of new user: '+username+" in group "+ affiliatename))
        return user_t
    
    def add_user_bucket(self,aff):
        bucketname = aff["AffiliateName"] 
        ## First check that the bucketname is valid: 
        assert type(bucketname) == str,"bucketname must be string"
        lowercase = bucketname.islower()
        underscore = '_' in bucketname 
        assert (lowercase and not(underscore)),'string must follow s3 bucket style'
        
        ## Now we can add this resource: 
        bucket = Bucket('PipelineBucket'+bucketname,AccessControl = 'Private',BucketName = bucketname)
        bucket_attached = self.template.add_resource(bucket)
        return bucket_attached,bucketname 
        
if __name__ == "__main__":
    filename = sys.argv[1]
    dirname = os.path.dirname(filename)
    ## Create new users  
    utemp = UserTemplate(filename)
    with open(dirname+"/"+"compiled_users.json","w") as f: 
        print(utemp.template.to_json(),file = f)
