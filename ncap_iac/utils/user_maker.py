from troposphere import Ref,Parameter,GetAtt,Template,Output,Join,Split,Sub,AWS_STACK_NAME,AWS_REGION
from troposphere.s3 import Bucket,Rules,S3Key,Filter
from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
from troposphere.cloudformation import CustomResource 
from config_handler import NCAPTemplate
from dev_builder import NeuroCaaSTemplate
from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import secrets
import os
import re
import boto3

## Import global parameters: 
with open("../global_params_initialized.json") as gp:
    gpdict = json.load(gp)

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
        ##TODO: Replace the paths for codeuri below once you move the actual code. 
        mkfunction = Function("S3PutObjectFunction",
                              CodeUri="../../protocols",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = template.add_resource(mkfunction)
        delfunction = Function("S3DelObjectFunction",
                              CodeUri="../../protocols",
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
        
class UserTemplateWeb(NeuroCaaSTemplate):
    '''
    Parsing file for user template for users who have been added through the website. Importantly, these users do not have their own dedicated buckets. 
    '''

    def __init__(self,filename):
        ## Clean filename input: 
        assert os.path.basename(filename) == "user_config_template.json", "Must pass a valid user template with filename 'user_config_template.json'."
        self.filename = filename 
        self.config = self.get_config(self.filename)
        self.template = self.initialize_template()
        ## Now we iterate through affiliates and set up resources for each. 
        ## Set up iterative resources: 
        self.users = {}
        for aff in self.config["UXData"]["Affiliates"]:
            ## we create users for each affiliate
            self.generate_users(aff)
            ## Now we create a user group that allows us to write to this bucket, and the users necessary to do so. 

    def get_config(self,filename):
        with open(filename,'r') as f:
            obj = json.load(f)

        ## Check that the top-level attributes we care about exist. 
        error = 0
        
        try: 
            obj['UXData']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        try: 
            obj['Lambda']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        try: 
            obj["Lambda"]["LambdaConfig"]['REGION']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        assert error == 0, 'please fix formatting errors in config file'


        return obj

    def initialize_template(self):
        """
        Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
        """
        template = Template()
        ## Apply a transform to use serverless functions. 
        template.set_transform("AWS::Serverless-2016-10-31")
        return template

    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True):
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True, 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        ## IMPORTANT: we will associate with each user a UserName (in the sense of the AWS parameter.)
        ## Doing so, we can reference existing users in other cfn stacks. An important and dire quirk to automated user creation is that creating the same IAM username in the same account in different regions can cause "unrecoverable data loss". To handle this, we will pass around usernames that are not postfixed, but will be converted under the hood to a username with a region associated. 
        username_region = username+self.config["Lambda"]["LambdaConfig"]["REGION"]

        ## We need to get the alphanumeric part of the username, and use that in the actual cloudformation logical name.  
        alphapat = '[^\W_]'
        match = re.findall(alphapat,username)
        username_alpha = "".join(match) 
        print(username_alpha,"here")

        groupmatch = re.findall(alphapat,affiliatename)
        groupname_alpha = "".join(groupmatch)

        user = User(groupname_alpha+'user'+username_alpha,UserName=username_region,Path="/"+groupname_alpha+'/')

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
        
            self.template.add_output(Output('Password'+username_alpha,Value = default_password,Description = 'Default password of new user '+username + " in group "+affiliatename))
            user_t.LoginProfile = lp


        ## Now we generate access keys:  
        if accesskey == True:
            key = AccessKey('userkey'+username_alpha,UserName = Ref(user))
            self.template.add_resource(key)
            accesskey = Ref(key)
            secretkey = GetAtt(key,'SecretAccessKey')

            self.template.add_output(Output('AccessKey'+username_alpha,Value = accesskey,Description = 'Access Key of user: '+username + ' in group '+affiliatename))
            self.template.add_output(Output('SecretAccessKey'+username_alpha,Value = secretkey,Description = 'Secret Key of new user: '+username+" in group "+ affiliatename))
        return user_t


## Make a parametrized version of the user template.  
class ReferenceUserCreationSubstackTemplate():
    """Created 6/1/20
    Function to create a parametrized stack that will be referenced by other pipeline stacks. Separates users associated with a given 
    pipeline from the actual mechanics of the pipeline processing. Note that this function DOES NOT actually depend upon the specific values of the stack configuration template that is passed to it. It only uses this structure to set up a parametrized template, and at a later date the dependence on a filename should be factored out. 
    
    """
    def __init__(self,filename):
        self.filename = filename
        self.config = self.get_config(self.filename)
        self.iam_resource = boto3.resource('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        self.iam_client = boto3.client("iam",region_name = self.config['Lambda']['LambdaConfig']["REGION"])
        ## We should get all resources once attached. 
        self.template = self.initialize_template()
        self.makefuncarn,self.delfuncarn,self.bucketname,affdict_params = self.add_affiliate_parameters()
        ## Now add affiliates:
        self.add_affiliate(affdict_params)
        self.add_log_folder([affdict_params],"testneurocaasusersidefolders")

    def get_config(self,filename):
        with open(filename,'r') as f:
            obj = json.load(f)

        ## Check that the top-level attributes we care about exist. 
        error = 0
        
        try: 
            obj['UXData']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        assert error == 0, 'please fix formatting errors in config file'

        ## Fill in some additional fields. 
        keys = ['INDIR',
                'OUTDIR',
                'LOGDIR',
                "CONFIGDIR",
                "SUBMITDIR"]
        vals = [gpdict["input_directory"],
                gpdict["output_directory"],
                gpdict["log_directory"],
                gpdict["config_directory"],
                gpdict["submission_directory"]]
        #vals = ['inputs','results','logs',"configs","submissions"]
        appenddict = {k:v for k,v in zip(keys,vals)}
        obj['Lambda']['LambdaConfig'].update(appenddict)

        return obj

    def initialize_template(self):
        """ Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
        :return: the troposphere template object that will be added to throughout initialization. 
        """
        template = Template()
        ## Apply a transform to use serverless functions. 
        template.set_transform("AWS::Serverless-2016-10-31")
        return template


    ## Parameter addition function:
    def add_affiliate_parameters(self):
        """Function to add parameters to a user subtemplate. A generator for the substack template for only one user group.

        Arguments:
        self: (object)
              The neurocaas blueprint. Should be initialized by calling the initialize_template() method. 
        Outputs:
              (Ref): 
              a reference to the logical id of the folder making lambda function for this group. 
              (Ref): 
              a reference to the logical id of the folder deleting lambda function for this group. 
              (Ref): 
              a reference to the physical resource id of the analysis buckets for this group. 
              (Dict): 
              a dictionary mocking the structure of the affiliatedictionary that is imported from the stack configuration template.
              Contains (Ref) objects as its entries.
        """
        try:
            self.template
        except AttributeError:
            raise AttributeError("template not yet created. do not call this method outside the init method.")
        ## Declare Parameters.
        MakeFuncArn = Parameter("MakeFuncArn",
                Description="ARN of the make folder function.",
                Type = "String")
        DelFuncArn = Parameter("DelFuncArn",
                Description="ARN of the delete folder function.",
                Type = "String")
        BucketNames = Parameter("BucketNames",
                Description="PhysicalResourceId of the buckets that users have access to.",
                Type = "String")
        Name = Parameter("Name",
                Description="Name of the user group.",
                Type = "String")
        UserNames = Parameter("UserNames",
                Description="List of the users in this group who should be added to this group.",
                Type = "String")

        ## Attach parameter
        MakeFuncArnAttached = self.template.add_parameter(MakeFuncArn)
        DelFuncArnAttached = self.template.add_parameter(DelFuncArn)
        BucketNamesAttached = self.template.add_parameter(BucketNames)
        NameAttached = self.template.add_parameter(Name)
        UserNamesAttached = self.template.add_parameter(UserNames)

        ## Add to a dictionary: 
        affiliatedict_params = {"AffiliateName":Ref(NameAttached),
                "UserNames":Ref(UserNamesAttached)}

        return Ref(MakeFuncArnAttached),Ref(DelFuncArnAttached),Ref(BucketNamesAttached),affiliatedict_params

    def attach_folder_creator_function(self,folderlogicalid,bucketname,path,dirname,dependson):
        """attach_folder_creator_function. Creates a lambda backed custom resource to make folders when this stack is created/updated. Subsequently attached it to the template represented by this resource.  

        :param folderlogicalid: the logical id that we will give to the folder create resources, identifying it within the cloudformation stack. 
        :param bucketname: the bucket within which we will make the folder related resource. 
        :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
        :param dirname: the name of the folder that we are making. Do not suffix with a slash.
        :return: the template-attached custom resource, as a troposphere object. 
        """
        if dependson is None:
            basemake = CustomResource(folderlogicalid,
                                      ServiceToken=self.makefuncarn,
                                      BucketName = bucketname,
                                      Path = path,
                                      DirName = dirname)
        else:
            basemake = CustomResource(folderlogicalid,
                                      ServiceToken=self.makefuncarn,
                                      BucketName = bucketname,
                                      Path = path,
                                      DirName = dirname,
                                      DependsOn = dependson)
        basefolder_creator = self.template.add_resource(basemake)
        return basefolder_creator

    def attach_folder_deleter_function(self,folderlogicalid,bucketname,path,dirname,dependson):
        """attach_folder_creator_function. Creates a lambda backed custom resource to delete folders when this stack is deleted. Subsequently attached it to the template represented by this resource.  

        :param folderlogicalid: the logical id that we will give to the folder create resources, identifying it within the cloudformation stack. 
        :param bucketname: the bucket within which we will make the folder related resource. 
        :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
        :param dirname: the name of the folder that we are making. Do not suffix with a slash.
        :return: the template-attached custom resource, as a troposphere object. 
        """
        if dependson is None:
            basemake = CustomResource(folderlogicalid,
                                      ServiceToken=self.delfuncarn,
                                      BucketName = bucketname,
                                      Path = path,
                                      DirName = dirname)
        else:
            basemake = CustomResource(folderlogicalid,
                                      ServiceToken=self.delfuncarn,
                                      BucketName = bucketname,
                                      Path = path,
                                      DirName = dirname,
                                      DependsOn=dependson)
        basefolder_deleter = self.template.add_resource(basemake)
        return basefolder_deleter

    def attach_folder_resources(self,folderid,bucketname,path,dirname,dependson = None):
        """attach_folder_resources. Creates two lambda backed custom resources to create and delete folders corresponding to stack events. Subsequently attaches these to the template represented by this resource. Assumes that dependencies passed to this function were created with the same function, and will modify names accordingly.  

        :param affiliatename: The name of the affiliate user or group. 
        :param bucketname: the name of the s3 bucket that we are creating a folder in. 
        :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
        :param dirname: the name of the folder that we are making. Do not suffix with a slash.
        :return: the template-attached custom resources for folder create and delete, as troposphere objects. 
        """
        makeid = folderid+"make"
        delid = folderid+"del"
        if dependson is None:
            makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson)
            delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson)
        else:
            makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson+"make")
            delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson+"del")
        return makeattached,delattached

    def add_affiliate_folder(self,affiliatename,bucketname):
        ## Declare depends on resources: 
        basefoldername = "AffiliateTemplateBaseFolder" 
        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basefolder,basefolderdelete = self.attach_folder_resources(basefoldername,bucketname,"",affiliatename)

        ## Designate cfn resource names for each: 
        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
        dirnamekeys = ["INDIR","OUTDIR","SUBMITDIR","CONFIGDIR"]
        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
        for key in pairs:
            cfn_name = key+"AffiliateTemplate"
            make,delete = self.attach_folder_resources(cfn_name,bucketname,Join("",[affiliatename,'/']),self.config['Lambda']['LambdaConfig'][pairs[key]],dependson = basefoldername)

    def customize_userpolicy(self,affiliatedict,bucketname):
        """customize_userpolicy. The method used to generate a policy that will allow users with the policy to run jobs in the relevant bucket.   

        :param affiliatedict: An affiliate dictionary containing the group name and member names of users. 
        :param bucketname: the name of the bucket for which this policy will grant access. 
        """
        affiliatename = affiliatedict["AffiliateName"]
        indir = self.config['Lambda']['LambdaConfig']['INDIR']
        outdir = self.config['Lambda']['LambdaConfig']['OUTDIR']
        logdir = self.config['Lambda']['LambdaConfig']['LOGDIR']
        subdir = self.config['Lambda']['LambdaConfig']['SUBMITDIR']
        condir = self.config['Lambda']['LambdaConfig']['CONFIGDIR']
        ## First get the template policy 
        with open('policies/iam_user_base_policy_doc.json','r') as f:
            obj = json.load(f)
        ## The following policies are not iterated for readability:
        ## Give LIST permissions for the affiliate folder and subdirectories.  
        obj["Statement"].append({
            'Sid': 'ListBucket',
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': Join("",['arn:aws:s3:::',bucketname]),
            'Condition':{'StringEquals':{'s3:prefix':['',
                Join("",[affiliatename,'/']),
                Join("",[affiliatename,'/',indir]),
                Join("",[affiliatename,'/',outdir]),
                logdir,
                Join("",[affiliatename,'/',subdir]),
                Join("",[affiliatename,'/',condir]),
                Join("",[affiliatename,'/',indir,'/']),
                Join("",[affiliatename,'/',outdir,'/']),
                Join("",[affiliatename,'/',subdir,'/']),
                Join("",[affiliatename,'/',condir,'/'])
            ],'s3:delimiter':['/']}}})
        ## Give LIST permissions within all subdirectories too. 
        obj["Statement"].append({
            'Sid': "ListSubBucket",
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': Join("",['arn:aws:s3:::',bucketname]),
            'Condition':{'StringLike':{'s3:prefix':[
                Join("",[affiliatename,'/',indir,'/*']),
                Join("",[affiliatename,'/',outdir,'/*']),
                Join("",[affiliatename,'/',condir,'/*']),
                Join("",[affiliatename,'/',subdir,'/*'])
            ]}}})
        ## Give PUT, and DELETE permissions for the input, config, and submit subdirectories: 
        obj["Statement"].append({
            'Sid': 'Inputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:PutObject','s3:DeleteObject'],
            'Resource': [
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',indir,'/*']),
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',condir,'/*']),
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',subdir,'/*'])
                         ]
             })
        
        ## Give GET, and DELETE permissions for the output, config and log subdirectory: 
        obj["Statement"].append({
           'Sid': 'Outputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:GetObject','s3:DeleteObject'],
            'Resource': [
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',outdir,'/*']),
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',condir,'/*']),
                         ]
             })
        return obj

    def generate_usergroup(self,affiliatedict):
        """ Create a group with which we will associate the policies that allow for bucket access.  

        :param affiliatedict: a dictionary containing information about the affiliates we need to use. 
        """
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict,"testneurocaasusersidefolders"),PolicyName = Join("",[affiliatename,'policy']))
        usergroup = Group("UserGroupAffiliateTemplate",GroupName = Join("",[affiliatename,"substackgroup"]),Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def add_affiliate(self,affiliatedict):
        '''
        when passed an affiliate dictionary, does two things. 1. creates the folder structure that is appropriate for this affiliate, and 2. adds a user group and users that can interact appropriately with this folder structure.
        '''
        ## First create folder structure
        affiliatename = affiliatedict['AffiliateName']
        self.add_affiliate_folder(affiliatename,"testneurocaasusersidefolders")
        ## Now create the usergroup to read/write appropriately. 
        self.add_affiliate_usernet(affiliatedict)

    def add_affiliate_usernet(self,affiliatedict):
        """add_affiliate_usernet. 

        :param affiliatedict:
        """
        ## Four steps here: 
        ## 1. Customize a user policy for this particular pipeline. 
        ## 2. Generate a user group with that policy. 
        ## 3. Attach users with credentials. 
        ## 4. Add users to group.  
        ## A method that customizes the json policy (see attached) to the particular affiliation name. 
        ## 1 and 2
        group = self.generate_usergroup(affiliatedict)
        Users = Split(",",affiliatedict["UserNames"])
        user = "tacosyne"
        self.generate_user_with_creds(user,affiliatedict["AffiliateName"],id_number = 0)
        ## 3 
        ## Note: this filters in the case where users are predefined elsewhere. 
        #users,usernames  = self.attach_users(affiliatedict)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition('AffiliateTemplate'+'UserNet',GroupName = Ref(group),Users = Users))

    def add_log_folder(self,affiliatedicts,bucketname):
        """ Adds the directory infrastructure to a given analysis bucket that allows it to do logging. 
        this has to happen after affiliates are defined. Perhaps major difference from previous version: only creates affiliate subdirectory of full log directory, because that should already exist upon startup. 

        """
        logfoldername = "LogFolder"

        ## Make a folder for each affiliate so they can be assigned completed jobs too. 
        for affdict in affiliatedicts:
            affiliatename = affdict["AffiliateName"]
            logaffmake,logaffdelete = self.attach_folder_resources(
                    logfoldername+"Affiliate",
                    bucketname,
                    self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                    affiliatename,
                    )


    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True,id_number = 0):
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True, 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        ## IMPORTANT: we will associate with each user a UserName (in the sense of the AWS parameter.)
        ## Doing so, we can reference existing users in other cfn stacks. An important and dire quirk to automated user creation is that creating the same IAM username in the same account in different regions can cause "unrecoverable data loss". To handle this, we will pass around usernames that are not postfixed, but will be converted under the hood to a username with a region associated. 
        username_region = username+self.config["Lambda"]["LambdaConfig"]["REGION"]

        user = User("affiliate"+'user'+str(id_number),UserName =username_region,Path="/")

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
        
            #self.template.add_output(Output('Password'+str(id_number),Value = default_password,Description = 'Default password of new user '+username + " in group "+affiliatename))
            self.template.add_output(Output('Password'+str(id_number),Value = default_password,Description = Join("",['Default password of new user ',username," in group ",affiliatename])))
            user_t.LoginProfile = lp


        ## Now we generate access keys:  
        if accesskey == True:
            key = AccessKey('userkey'+username,UserName = Ref(user))
            self.template.add_resource(key)
            accesskey = Ref(key)
            secretkey = GetAtt(key,'SecretAccessKey')

            self.template.add_output(Output('AccessKey'+str(id_number),Value = accesskey,Description = Join("",['Access Key of user: ',username , ' in group ',affiliatename])))
            self.template.add_output(Output('SecretAccessKey'+str(id_number),Value = secretkey,Description = Join("",['Secret Key of new user: ',username," in group ", affiliatename])))
        return user_t


if __name__ == "__main__":
    filename = sys.argv[1]
    dirname = os.path.dirname(filename)
    ## First get the development stage we are in. 
    with open(filename,"r") as f:
        userdict = json.load(f)
    try:
        stage = userdict["STAGE"]
    except KeyError:
        ## Legacy vers. of scripting code that does not include a "STAGE" field.  
        stage = "dev" 
    except Exception as err:
        print("Unhandled exception: ",sys.exc_info())
        raise 

    if stage == "dev":
        ## Create new users  
        utemp = UserTemplate(filename)
        with open(dirname+"/"+"compiled_users.json","w") as f: 
            print(utemp.template.to_json(),file = f)
    elif stage == "web":
        ## Create new users  
        utemp = UserTemplateWeb(filename)
        with open(dirname+"/"+"compiled_users.json","w") as f: 
            print(utemp.template.to_json(),file = f)
