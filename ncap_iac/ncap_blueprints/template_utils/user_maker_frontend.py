from troposphere import Ref,GetAtt,Template,Output,Join,Sub,AWS_STACK_NAME,AWS_REGION
from troposphere.s3 import Bucket,Rules,S3Key,Filter
from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
from troposphere.cloudformation import CustomResource 
from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import secrets
import re
import os
import boto3
from botocore.client import ClientError

## Get boto3 declared utilities: 
s3 = boto3.resource("s3")

## A template that takes in a config file describing the sets of users that will be using the template. Users are associated under a particular group name [corresponding to a path prefix], and have access to a bucket that will eventually consolidate all of their data uploads [not yet implemented].
class UserTemplateFrontend():
    """
    Parser for user_stack_template.json files. This object eats ncap-specific user_stack_template files, and spits out cloudformation templates that can be parsed and directly deployed into AWS resources. Breaks out individual users into affiliate groups (i.e. labs) that together have collective resource capacity. For each group, this template creates a dedicated bucket where the group can deposit its data, and configures it with subfolders dedicated for data upload, result download, and admin monitoring of overall usage (monitoring implemented from the ncap_blueprint side via lambda functions). This object also configures the permissions of each user that allows them to upload, download, access and delete data from the appropriate areas, and creates folders in existing analysis buckets with analogous permissions. All methods are called in object creation. We make use of the python library troposphere to assist template writing.   

    Inputs:
    filename (str): the path to the user_config_template.json that will be translated into a cloudformation template.  

    Usage: 
    temp = UserTemplateFrontend("path/to/user_config_template")
    with open("path/to/cfntemplate","w") as f: 
        print(utemp.template.to_json(),file = f)
    """
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
            self.add_user_folders(aff)
            self.buckets[b_name] = b_attached
            ## we create users for each affiliate, give them permissions to access this data bucket via a specific user group with custom policy. 
            self.add_affiliate_usernet(aff)

            ## Now we create a folder in each of the analysis buckets that this user has access to, where we can drop submit files. 
            self.configure_pipelines(aff)
            ## Now we create user groups that allow access to these analysis folders. 
            #self.authorize_pipelines(aff)

            ## Finally we add these users to these analysis specific user groups. 

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
        ##TODO: Replace the paths for codeuri below once you move the actual code. 
        mkfunction = Function("S3PutObjectFunction",
                              CodeUri="../../ncap_blueprints/lambda_repo",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = template.add_resource(mkfunction)
        delfunction = Function("S3DelObjectFunction",
                              CodeUri="../../ncap_blueprints/lambda_repo",
                              Description= "Deletes Objects from S3",
                              Handler="helper.handler_deldir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        delfunction_attached = template.add_resource(delfunction)
        ## Custom resource to delete the folder within the submit file for each affiliate group upon user termination.  
        for aff in self.config["UXData"]["Affiliates"]:
            bucketname = aff["AffiliateName"]
            delresource = CustomResource('DeleteCustomResource'+bucketname,
                                 ServiceToken=GetAtt(delfunction_attached,"Arn"),
                                 BucketName = bucketname,
                                 DependsOn = 'UserBucket'+bucketname)
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

    ###########################################################################################################

    
    def add_user_bucket(self,aff):
        bucketname = aff["AffiliateName"] 
        ## First check that the bucketname is valid: 
        assert type(bucketname) == str,"bucketname must be string"
        lowercase = bucketname.islower()
        underscore = '_' in bucketname 
        assert (lowercase and not(underscore)),'string must follow s3 bucket style'
        
        ## Now we can add this resource: 
        bucket = Bucket('UserBucket'+bucketname,AccessControl = 'Private',BucketName = bucketname)
        bucket_attached = self.template.add_resource(bucket)
        
        return bucket_attached,bucketname 

    def add_user_folders(self,aff):
        bucketname = aff["AffiliateName"] 
        ## Within, we want to make an input, output and log folder. 
        inmake = CustomResource("UserInFolder"+bucketname,
                ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                BucketName = bucketname,
                Path = "",
                DirName = self.config['Lambda']["LambdaConfig"]["INDIR"],
                DependsOn = "UserBucket"+bucketname)
        ## Note that BucketNAme takes the name of the bucket, while depends on takes the name of the bucket as a cfn resource. 

        outmake = CustomResource("UserOutFolder"+bucketname,
                ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                BucketName = bucketname,
                Path = "",
                DirName = self.config['Lambda']["LambdaConfig"]["OUTDIR"],
                DependsOn = "UserBucket"+bucketname)

        logmake = CustomResource("UserLogFolder"+bucketname,
                ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                BucketName = bucketname,
                Path = "",
                DirName = self.config['Lambda']["LambdaConfig"]["LOGDIR"],
                DependsOn = "UserBucket"+bucketname)

        ## Attach custom resources to make
        infolder = self.template.add_resource(inmake)
        outfolder = self.template.add_resource(outmake)
        logfolder = self.template.add_resource(logmake)

        ## Declare custom resource to delete from this bucket
        userdelresource = CustomResource('UserDeleteCustomResource'+bucketname,
                             ServiceToken=GetAtt(self.deldirfunc,"Arn"),
                             BucketName = bucketname,
                             DependsOn = 'UserBucket'+bucketname)

        ## Attach custom resource to delete from this bucket. 
        self.template.add_resource(userdelresource)


    def add_affiliate_usernet(self,aff):
        """
        Attach users to the data bucket: generate the aws IAM Policy that they need to access the data bucket in appropriate ways, create a group that has this policy attached, and finally attach users to this group.  
        """
        ## Four steps here: 
        ## 1. Customize a user policy for this particular pipeline. 
        ## 2. Generate a user group with that policy. 
        ## 3. Generate users with credentials. 
        ## 4. Add users to group.  
        ## A method that customizes the json policy (see attached) to the particular affiliation name. 
        ## 1 and 2
        group = self.generate_usergroup_databucket(aff)
        ## 3 
        users = self.generate_users(aff)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition(aff['AffiliateName']+'UserNet',GroupName = Ref(group),Users = [Ref(u) for u in users]))
        return users_attached

        
    def generate_usergroup_databucket(self,affiliatedict):
        """
        As a subroutine, generates the policy needed 
        """
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.add_user_permissions(affiliatedict),PolicyName = affiliatename+'policy')
        usergroup = Group("UserGroup"+affiliatename,GroupName = affiliatename+"group",Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def add_user_permissions(self,aff):
        """
        Add permissions for this affiliate group to use a bunch of algorithms out of the gate, as well as their own personal user bucket.  
        """
        ## First add permissions to access the affiliate bucket. 
        bucketname = aff["AffiliateName"] 
        indir = self.config["Lambda"]["LambdaConfig"]["INDIR"]
        outdir = self.config["Lambda"]["LambdaConfig"]["OUTDIR"]
        logdir = self.config["Lambda"]["LambdaConfig"]["LOGDIR"]
        ## Get the same template policy that we use for customizeing templates per-pipeline
        with open('policies/iam_user_base_policy_doc.json','r') as f:
            obj = json.load(f)
        ## Give LIST permissions for the input and output folder as well as submdirectories. 
        obj["Statement"].append({
            'Sid': 'ListHomeBucket',
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringEquals':{'s3:prefix':['',
                indir,
                outdir,
                logdir,
                indir+'/',
                outdir+'/',
                logdir+'/'],'s3:delimiter':['/']}}})
        ## Because we match on a different condition, we need to partition out wildcard permissions for insides of subdirectory. 
        obj["Statement"].append({
            'Sid': 'ListHomeSubBucket',
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringLike':{'s3:prefix':['',
                indir+'/*',
                outdir+'/*',
                logdir+'/*']}}})

        obj["Statement"].append({
            'Sid':"Homeinputfolderwrite",
            'Effect':'Allow',
            'Action':['s3:PutObject','s3:DeleteObject'],
            'Resource':['arn:aws:s3:::'+bucketname+'/'+indir+'/*']})

        obj["Statement"].append({
            'Sid':"Homeoutputfolderget",
            'Effect':'Allow',
            'Action':['s3:GetObject','s3:DeleteObject'],
            'Resource':['arn:aws:s3:::'+bucketname+'/'+outdir+'/*']})

        with open('policies/'+aff["AffiliateName"]+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj

    def generate_users(self,affiliatedict):
        """
        Wrapper function for generate_user_with_creds: create the relevant users, and generate the credentials that they will be using in the future. 
        """
        ## First get a list of usernames. 
        users = affiliatedict['UserNames']
        affiliatename = affiliatedict['AffiliateName']
        ## Initialize list of users: 
        affiliate_users = []
        for user in users:
            affiliate_users.append(self.generate_user_with_creds(user,affiliatename))
        return affiliate_users
    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True):
        """
        Generates the credentials (access key and secret access key for programmatic access, as well as password for console access. These are all stored as outputs of the eventual cloudformation stack.) 
        """
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

    def configure_pipelines(self,aff):
        """
        First, add folders in the appropriate pipeline directories  
        """
        self.analysis_exists(aff)
        affiliatename = aff["AffiliateName"]
        affiliatename_safe = re.sub('[\W_]+', '', affiliatename)
        ## Now iterate folder creation over pipelines: 
        for pipelinename in aff["Pipelines"]:
            ## Within, we want to make an input, output and log folder. 
            pipelinename_safe = re.sub('[\W_]+', '', pipelinename)
            inmake = CustomResource("UserInFolder"+affiliatename_safe+pipelinename_safe,
                    ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                    BucketName = pipelinename,
                    Path = "",
                    DirName = self.config['Lambda']["LambdaConfig"]["INDIR"])
                    #DependsOn = "PipelineBucket"+pipelinename)
            ## Note that BucketNAme takes the name of the bucket, while depends on takes the name of the bucket as a cfn resource. 

            outmake = CustomResource("UserOutFolder"+affiliatename_safe+pipelinename_safe,
                    ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                    BucketName = pipelinename,
                    Path = "",
                    DirName = self.config['Lambda']["LambdaConfig"]["OUTDIR"])
                    #DependsOn = "PipelineBucket"+pipelinename)

            logmake = CustomResource("UserLogFolder"+affiliatename_safe+pipelinename_safe,
                    ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                    BucketName = pipelinename,
                    Path = "",
                    DirName = self.config['Lambda']["LambdaConfig"]["LOGDIR"])
                    #DependsOn = "PipelineBucket"+pipelinename)

            ## Attach custom resources to make
            infolder = self.template.add_resource(inmake)
            outfolder = self.template.add_resource(outmake)
            logfolder = self.template.add_resource(logmake)

            ## Declare custom resource to delete from this bucket
            userdelresource = CustomResource('UserDeleteCustomResource'+affiliatename_safe+pipelinename_safe,
                                 ServiceToken=GetAtt(self.deldirfunc,"Arn"),
                                 BucketName = pipelinename)
                                 #DependsOn = 'PipelineBucket'+pipelinename)

            ## Attach custom resource to delete from this bucket. 
            self.template.add_resource(userdelresource)

    def authorize_pipelines(self,aff):
        """
        Now create per-pipeline user groups that give this user access to a subfolder of the appropriate pipeline. 
        """
        self.analysis_exists(aff)
        affiliatename= aff["AffiliateName"]
        policy = Policy(PolicyDocument=self.per_pipeline_permissions(aff),PolicyName = affiliatename+'analysispolicy')
        pipelinesusergroup = Group("UserGroupAnalysis"+affiliatename,GroupName = affiliatename+"analysisgroup",Policies=[policy])
        usergroup_attached = self.template.add_resource(pipelinesusergroup)

        usernames_bare = aff['UserNames']
        ## Initialize list of users: 
        affiliate_users = []
        affiliate_usernames = []
        err = 0
        for user in usernames_bare:
            try:
                # Filter for existing: we only want to treat users who have already been declared elsewhere. 
                ## Get the internal user name filtered by region:
                user_local = user+self.config["Lambda"]["LambdaConfig"]["REGION"]
                print("User {} exists, adding to group".format(user))
                affiliate_usernames.append(user_local)
            except Exception as e: 
                print("Error adding User {}, please evaluate.".format(user),e)
                raise Exception

        users_attached = self.template.add_resource(UserToGroupAddition(aff['AffiliateName']+'AnalysisUserNet',GroupName = Ref(usergroup_attached),Users = [Ref(u) for u in affiliate_usernames]))
        return users_attached
    def per_pipeline_permissions(self,aff):
        indir = self.config["Lambda"]["LambdaConfig"]["INDIR"]
        outdir = self.config["Lambda"]["LambdaConfig"]["OUTDIR"]
        logdir = self.config["Lambda"]["LambdaConfig"]["LOGDIR"]
        ## Get the same template policy that we use for customizeing templates per-pipeline
        with open('policies/iam_user_base_policy_doc.json','r') as f:
            obj = json.load(f)
        for pipelinename in aff["Pipelines"]:
            ## Give LIST permissions for the input and output folder as well as submdirectories. 
            obj["Statement"].append({
                'Sid': 'List{}Bucket'.format(pipelinename),
                'Effect': 'Allow',
                'Action': 's3:ListBucket',
                'Resource': ['arn:aws:s3:::'+pipelinename],
                'Condition':{'StringEquals':{'s3:prefix':['',
                    indir,
                    outdir,
                    logdir,
                    indir+'/',
                    outdir+'/',
                    logdir+'/'],'s3:delimiter':['/']}}})
            ## Because we match on a different condition, we need to partition out wildcard permissions for insides of subdirectory. 
            obj["Statement"].append({
                'Sid': 'List{}SubBucket'.format(pipelinename),
                'Effect': 'Allow',
                'Action': 's3:ListBucket',
                'Resource': ['arn:aws:s3:::'+pipelinename],
                'Condition':{'StringLike':{'s3:prefix':['',
                    indir+'/*',
                    outdir+'/*',
                    logdir+'/*']}}})

            obj["Statement"].append({
                'Sid':pipelinename+"inputfolderwrite",
                'Effect':'Allow',
                'Action':['s3:PutObject','s3:DeleteObject'],
                'Resource':['arn:aws:s3:::'+pipelinename+'/'+indir+'/*']})

            obj["Statement"].append({
                'Sid':pipelinename+"outputfolderget",
                'Effect':'Allow',
                'Action':['s3:GetObject','s3:DeleteObject'],
                'Resource':['arn:aws:s3:::'+pipelinename+'/'+outdir+'/*']})

        with open('policies/'+aff["AffiliateName"]+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj
    def analysis_exists(self,aff):
        """
        Helper function to check that the analyses this pipeline is authorized to configure actually exist.  
        """
        ##TODO: check not just that the bucket exists, but also that it is an ncap enabled bucket. 
        ## Now we want to iterate permissions for all of the algorithms that this user has access to. We extract this information from the Pipelines field, which refers to the corresponding analysis buckets in S3.  
        ## First check that all buckets exist: 
        for pipelinename in aff["Pipelines"]:
            try:
                s3.meta.client.head_bucket(Bucket=pipelinename)
            except ClientError:
                print("Bucket {} doesn't exist.".format(pipelinename))
                raise Exception 

    #def add_analysis_permissions(self,aff):
    #    
    #    ## Now we want to iterate permissions for all of the algorithms that this user has access to. We extract this information from the Pipelines field, which refers to the corresponding analysis buckets in S3.  
    #    ## First check that all buckets exist: 
    #    for pipelinename in aff["Pipelines"]:
    #        try:
    #            s3.meta.client.head_bucket(Bucket=pipelinename)
    #        except ClientError:
    #            print("Bucket {} doesn't exist.".format(pipelinename))
    #            raise Exception 

    #    ## Now, we will
    #    ## 1) make folders for each user group to submit to inside those buckets. . 
    #    ## 2) give users permission to use those buckets. 

    #    for pipelinename in aff["Pipelines"]:
    #        
    #        obj["Statement"].append({
    #            'Sid': 'ListPipeline'+})
    #    

    #        
    ### Define functions that take in a pipeline name and then 1) make an appropriate set of folders within it, and 2) give users access to those folders. 
    #def make_analysisfolders(self,pipelinename):


    #def add_analysis_folders(self,aff):
    #    """
    #    Analogous to add_user_folders, but makes the folders inside individual analysis buckets for this particular affiliate 
    #    """
    #    affname = aff["AffiliateName"] 
    #    for 
    #    ## Within, we want to make an input, output and log folder. 
    #    inmake = CustomResource("UserInFolder"+bucketname,
    #            ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
    #            BucketName = bucketname,
    #            Path = "",
    #            DirName = self.config['Lambda']["LambdaConfig"]["INDIR"],
    #            DependsOn = "PipelineBucket"+bucketname)
    #    ## Note that BucketNAme takes the name of the bucket, while depends on takes the name of the bucket as a cfn resource. 

    #    outmake = CustomResource("UserOutFolder"+bucketname,
    #            ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
    #            BucketName = bucketname,
    #            Path = "",
    #            DirName = self.config['Lambda']["LambdaConfig"]["OUTDIR"],
    #            DependsOn = "PipelineBucket"+bucketname)

    #    logmake = CustomResource("UserLogFolder"+bucketname,
    #            ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
    #            BucketName = bucketname,
    #            Path = "",
    #            DirName = self.config['Lambda']["LambdaConfig"]["LOGDIR"],
    #            DependsOn = "PipelineBucket"+bucketname)

    #    ## Attach custom resources to make
    #    infolder = self.template.add_resource(inmake)
    #    outfolder = self.template.add_resource(outmake)
    #    logfolder = self.template.add_resource(logmake)

    #    ## Declare custom resource to delete from this bucket
    #    userdelresource = CustomResource('UserDeleteCustomResource'+bucketname,
    #                         ServiceToken=GetAtt(self.deldirfunc,"Arn"),
    #                         BucketName = bucketname,
    #                         DependsOn = 'PipelineBucket'+bucketname)

    #    ## Attach custom resource to delete from this bucket. 
    #    self.template.add_resource(userdelresource)

        

        
if __name__ == "__main__":
    filename = sys.argv[1]
    dirname = os.path.dirname(filename)
    ## Create new users  
    utemp = UserTemplateFrontend(filename)
    with open(dirname+"/"+"compiled_users.json","w") as f: 
        print(utemp.template.to_json(),file = f)
