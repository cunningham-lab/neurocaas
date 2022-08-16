from troposphere import Ref,Parameter,GetAtt,Template,Output,Join,Split,Sub,AWS_STACK_NAME,AWS_REGION
from troposphere.s3 import Bucket,Rules,S3Key,Filter
from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
from troposphere.cloudformation import CustomResource,Stack
from config_handler import NCAPTemplate
from dev_builder import NeuroCaaSTemplate
from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import secrets
import os
import re
import boto3
from botocore.exceptions import ClientError

## Import global parameters: 
with open("../global_params_initialized.json") as gp:
    gpdict = json.load(gp)

def return_alphanumeric(string):
    """
    Return alphanumeric version of provided string.  
    """
    alphapat = '[^\W_]'
    match = re.findall(alphapat,string)
    string_alpha = "".join(match) 
    return string_alpha
    
def validate_resource(resource_physicalid,parentstack_name):
    """
    given an AWS resource physical id, makes sure that it does not exist in other stack names 
    :param resource_physicalid: physical resource id we are trying to vet. 
    :param parentstack_name: the name of the stack that we expect our resource to be in, if at all. 

    :return: boolean, if it is valid to create this resource or not. 
    """
    cfn_client = boto3.client("cloudformation")
    try:
        response = cfn_client.describe_stack_resources(PhysicalResourceId=resource_physicalid)
        ## stack exists: 
        valid = response["StackResources"][0]["StackName"] == parentstack_name 
    except ClientError as e:
        try:
            ## Does not exist: 
            assert e.response["Error"]["Code"] == "ValidationError"
            assert e.response["Error"]["Message"] == "Stack for {} does not exist".format(resource_physicalid)
            valid = True 
        except AssertionError:
            ## Encountered an unknown error. Try again. 
            valid = False 
    return valid

def bucket_exists(bucketname):
    """ Check if s3 bucket exists. 

    """
    s3 = boto3.resource("s3")

    try:
        s3.meta.client.head_bucket(Bucket=bucketname)
        
        exists = True
    except ClientError: 
        exists = False
    return exists

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
class ReferenceUserCreationTemplate():
    """Created 6/1/20
    Function to create a parametrized stack that will be referenced by other pipeline stacks. Separates users associated with a given 
    pipeline from the actual mechanics of the pipeline processing.     

    """
    def __init__(self,filename):
        self.filename = filename
        self.stackname = os.path.basename(os.path.dirname(self.filename))
        self.config = self.get_config(self.filename)
        self.iam_resource = boto3.resource('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        self.iam_client = boto3.client("iam",region_name = self.config['Lambda']['LambdaConfig']["REGION"])
        ## We should get all resources once attached. 
        self.template = self.initialize_template()
        self.makefuncarn,self.delfuncarn = self.attach_folder_lambdas()

        ## Now add affiliates:
        for affiliate in self.config["UXData"]["Affiliates"]:
            self.validate_parameters(affiliate)
            self.add_affiliate(affiliate)
            self.add_folder_substack(affiliate)
        #self.add_log_folder(self.config["UXData"]["Affiliates"],"testneurocaasusersidefolders")

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

    def attach_folder_lambdas(self):
        """ Creates and attaches the lambda functions that create and delete folders upon stack create/delete.

        :return: The arns of the make and delete lambda functions, to be referenced inside custom resources. 
        """
        ## First get the trust agreement: 
        with open('policies/lambda_role_assume_role_doc.json',"r") as f:
            mkdirassume_role_doc = json.load(f)
        ## Base lambda policy
        base_policy = lambda_basepolicy("LambdaBaseRole")
        ## Write permissions for lambda to s3 
        write_policy = lambda_writeS3('LambdaWriteS3Policy')
        ## 
        self.template.add_resource(base_policy)
        mkdirrole = Role("S3MakePathRole",
                AssumeRolePolicyDocument=mkdirassume_role_doc,
                ManagedPolicyArns=[Ref(base_policy)],
                Policies = [write_policy])
        mkdirrole_attached = self.template.add_resource(mkdirrole)

        ## Get the lambda config parameters for initialization of the custom resource delete function [needs the region]
        lambdaconfig = self.config['Lambda']['LambdaConfig']

        ## Now we need to write a lambda function that actually does the work:  
        mkfunction = Function("S3PutObjectFunction",
                              CodeUri="../../protocols",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = self.template.add_resource(mkfunction)
        delfunction = Function("S3DelObjectFunction",
                               CodeUri="../../protocols",
                               Description= "Deletes Objects from S3",
                               Handler="helper.handler_deldir",
                               Environment = Environment(Variables=lambdaconfig),
                               Role=GetAtt(mkdirrole_attached,"Arn"),
                               Runtime="python3.6",
                               Timeout=30)
        delfunction_attached = self.template.add_resource(delfunction)

        return GetAtt(mkfunction_attached,"Arn"),GetAtt(delfunction_attached,"Arn")

    def add_folder_substack(self,affiliatedict):
        """function to pass arguments to substack. 
      

        """
        alphapat = '[^\W_]'
        name = affiliatedict["AffiliateName"]
        match = re.findall(alphapat,name)
        name_alpha = "".join(match) 
        for bucketname in affiliatedict["Pipelines"]:
            match = re.findall(alphapat,bucketname)
            bucketname_alpha = "".join(match) 
            substack = Stack("FolderSubstack{}{}".format(name_alpha,bucketname_alpha),
                    TemplateURL="../../ncap_blueprints/utils_stack/template.yaml",
                    Parameters = {"MakeFuncArn":self.makefuncarn,
                        "DelFuncArn":self.delfuncarn,
                        "Name":name,
                        "BucketName":bucketname})
            self.template.add_resource(substack)

    #def attach_folder_creator_function(self,folderlogicalid,bucketname,path,dirname,dependson):
    #    """attach_folder_creator_function. Creates a lambda backed custom resource to make folders when this stack is created/updated. Subsequently attached it to the template represented by this resource.  

    #    :param folderlogicalid: the logical id that we will give to the folder create resources, identifying it within the cloudformation stack. 
    #    :param bucketname: the bucket within which we will make the folder related resource. 
    #    :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
    #    :param dirname: the name of the folder that we are making. Do not suffix with a slash.
    #    :return: the template-attached custom resource, as a troposphere object. 
    #    """
    #    if dependson is None:
    #        basemake = CustomResource(folderlogicalid,
    #                                  ServiceToken=self.makefuncarn,
    #                                  BucketName = bucketname,
    #                                  Path = path,
    #                                  DirName = dirname)
    #    else:
    #        basemake = CustomResource(folderlogicalid,
    #                                  ServiceToken=self.makefuncarn,
    #                                  BucketName = bucketname,
    #                                  Path = path,
    #                                  DirName = dirname,
    #                                  DependsOn = dependson)
    #    basefolder_creator = self.template.add_resource(basemake)
    #    return basefolder_creator

    #def attach_folder_deleter_function(self,folderlogicalid,bucketname,path,dirname,dependson):
    #    """attach_folder_creator_function. Creates a lambda backed custom resource to delete folders when this stack is deleted. Subsequently attached it to the template represented by this resource.  

    #    :param folderlogicalid: the logical id that we will give to the folder create resources, identifying it within the cloudformation stack. 
    #    :param bucketname: the bucket within which we will make the folder related resource. 
    #    :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
    #    :param dirname: the name of the folder that we are making. Do not suffix with a slash.
    #    :return: the template-attached custom resource, as a troposphere object. 
    #    """
    #    if dependson is None:
    #        basemake = CustomResource(folderlogicalid,
    #                                  ServiceToken=self.delfuncarn,
    #                                  BucketName = bucketname,
    #                                  Path = path,
    #                                  DirName = dirname)
    #    else:
    #        basemake = CustomResource(folderlogicalid,
    #                                  ServiceToken=self.delfuncarn,
    #                                  BucketName = bucketname,
    #                                  Path = path,
    #                                  DirName = dirname,
    #                                  DependsOn=dependson)
    #    basefolder_deleter = self.template.add_resource(basemake)
    #    return basefolder_deleter

    #def attach_folder_resources(self,folderid,bucketname,path,dirname,dependson = None):
    #    """attach_folder_resources. Creates two lambda backed custom resources to create and delete folders corresponding to stack events. Subsequently attaches these to the template represented by this resource. Assumes that dependencies passed to this function were created with the same function, and will modify names accordingly.  

    #    :param affiliatename: The name of the affiliate user or group. 
    #    :param bucketname: the name of the s3 bucket that we are creating a folder in. 
    #    :param path: the path to the location where we will create a folder. use "" if creating a folder in the base directory. 
    #    :param dirname: the name of the folder that we are making. Do not suffix with a slash.
    #    :return: the template-attached custom resources for folder create and delete, as troposphere objects. 
    #    """
    #    folderid_alnum = ''.join(ch for ch in folderid if ch.isalnum())
    #    makeid = folderid_alnum+"make"
    #    delid = folderid_alnum+"del"
    #    if dependson is None:
    #        makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson)
    #        delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson)
    #    else:
    #        dependson_alnum = ''.join(ch for ch in dependson if ch.isalnum())
    #        makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson_alnum+"make")
    #        delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson_alnum+"del")
    #    return makeattached,delattached

    def validate_parameters(self,affiliatedict):
        """validate_parameters. Validates the parameters in this dictionary:
        -assures that the group given does not already exist in another stack
        -assures that the users being declared to not already exist in another stack 
        -assures that the buckets being referenced exist and are correctly structured. 

        :param affiliatedict:
        """
        group_valid = self.validate_group(affiliatedict)
        assert group_valid, "Group {} exists in another stack, cancelling.".format(affiliatedict["AffiliateName"])
        users_valid = self.validate_users(affiliatedict)
        assert users_valid, "One or more users in group {} exist in another stack, cancelling.".format(affiliatedict["AffiliateName"])
        buckets_valid = self.validate_buckets(affiliatedict)
        assert buckets_valid, "One or more pipelines indicated in profile for group {} does not exist, cancelling.".format(affiliatedict["AffiliateName"])


    def validate_group(self,affiliatedict):
        """validate_group. Validates that the group we would declare does not already exist. 

        :param affiliatedict:
        """
        groupname = self.generate_group_physical_id(affiliatedict)
        valid = validate_resource(groupname,self.stackname)
        return valid

    def validate_users(self,affiliatedict):
        """validate individual users. Validates that the users we would declare  
        """
        condition = []
        for username in affiliatedict["UserNames"]:
            condition.append(validate_resource(self.generate_user_physical_id(username),self.stackname))
        return all(condition)

    def validate_buckets(self,affiliatedict):
        """validate the pipeline buckets that have been passed as input, checking that they exist.  
        
        """
        condition = []
        for bucketname in affiliatedict["Pipelines"]:
            condition.append(bucket_exists(bucketname))
        return all(condition)





    def add_affiliate(self,affiliatedict):
        '''
        when passed an affiliate dictionary, does two things. 1. creates the folder structure that is appropriate for this affiliate, and 2. adds a user group and users that can interact appropriately with this folder structure.
        '''
        ## First create folder structure
        #self.add_affiliate_folder(affiliatedict)
        ## Now create the usergroup to read/write appropriately. 
        self.add_affiliate_usernet(affiliatedict)

    #def add_affiliate_folder(self,affiliatedict):
    #    affiliatename = affiliatedict["AffiliateName"]
    #    bucketnames = affiliatedict["Pipelines"] 
    #    for bucketname in bucketnames:
    #        ## Declare depends on resources: 
    #        basefoldername = "AffiliateTemplateBaseFolder"+affiliatename+bucketname 
    #        ## Retrieve lambda function and role: 
    #        ## We will declare three custom resources per affiliate: 
    #        basefolder,basefolderdelete = self.attach_folder_resources(basefoldername,bucketname,"",affiliatename)

    #        ## Designate cfn resource names for each: 
    #        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
    #        dirnamekeys = ["INDIR","OUTDIR","SUBMITDIR","CONFIGDIR"]
    #        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
    #        for key in pairs:
    #            cfn_name = key+"AffiliateTemplate"+affiliatename+bucketname
    #            make,delete = self.attach_folder_resources(cfn_name,bucketname,Join("",[affiliatename,'/']),self.config['Lambda']['LambdaConfig'][pairs[key]],dependson = basefoldername)

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

        ## Figure out if we should rotate keys: 
        usernames = []
        try:
            keyserial = affiliatedict["KeySerialNumber"]
        except KeyError:
            ## no key serial given. Note that this will throw an error if you delete key serial numbers after providing them. 
            keyserial = 1

        for u,user in enumerate(affiliatedict["UserNames"]):
            user_attached= self.generate_user_with_creds(user,affiliatedict["AffiliateName"],id_number = keyserial)
            usernames.append(Ref(user_attached))
        ## 3 
        ## Note: this filters in the case where users are predefined elsewhere. 
        #users,usernames  = self.attach_users(affiliatedict)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition('AffiliateTemplate'+'UserNet'+return_alphanumeric(affiliatedict["AffiliateName"]),GroupName = Ref(group),Users = usernames))

    def generate_group_physical_id(self,affiliatedict):
        """
        Function to generate the physical resource id for the given group. Meant to unify the way that group physical ids are created and validated.  
        """
        return affiliatedict["AffiliateName"]+"usercentricgroup"
    def generate_user_physical_id(self,username):
        """generate_user_physical_id. Appends the region name to the user name, to protect from catastrophic errors. Meant as a way to unify the way that user ids are created and validated. 

        :param username:
        """
        return username+self.config["Lambda"]["LambdaConfig"]["REGION"]

    def generate_usergroup(self,affiliatedict):
        """ Create a group with which we will associate the policies that allow for bucket access.  

        :param affiliatedict: a dictionary containing information about the affiliates we need to use. 
        """
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = Join("",[affiliatename,'policy']))
        usergroup = Group("UserGroupAffiliateTemplate"+return_alphanumeric(affiliatename),GroupName = self.generate_group_physical_id(affiliatedict),Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True,id_number = 1):
        """generate_user_with_creds.

        :param username: name of the user to create. 
        :param affiliatename: name of the group the user belongs to. 
        :param password: whether or not to assign password to user. 
        :param accesskey: whether or not to assign accesskey to user. 
        :param id_number: the access key number. Can only be incremented, in order to rotate the key.  
        """
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True, 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        ## IMPORTANT: we will associate with each user a UserName (in the sense of the AWS parameter.)
        ## Doing so, we can reference existing users in other cfn stacks. An important and dire quirk to automated user creation is that creating the same IAM username in the same account in different regions can cause "unrecoverable data loss". To handle this, we will pass around usernames that are not postfixed, but will be converted under the hood to a username with a region associated. 

        username_region = self.generate_user_physical_id(username)

        ## We need to get the alphanumeric part of the username, and use that in the actual cloudformation logical name.  
        username_alpha = return_alphanumeric(username)

        groupname_alpha = return_alphanumeric(affiliatename)

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
        
            #self.template.add_output(Output('Password'+str(id_number),Value = default_password,Description = 'Default password of new user '+username + " in group "+affiliatename))
            self.template.add_output(Output('Password'+username_alpha,Value = default_password,Description = 'Default password of new user '+username+" in group "+affiliatename))
            user_t.LoginProfile = lp

        ## Now we generate access keys:  
        if accesskey == True:
            key = AccessKey('userkey'+username_alpha,UserName = Ref(user),Serial = id_number)
            self.template.add_resource(key)
            accesskey = Ref(key)
            secretkey = GetAtt(key,'SecretAccessKey')

            self.template.add_output(Output('AccessKey'+username_alpha,Value = accesskey,Description = 'Access Key of user: '+username + ' in group '+affiliatename))
            self.template.add_output(Output('SecretAccessKey'+username_alpha,Value = secretkey,Description = 'Secret Key of new user: '+username+" in group "+ affiliatename))
        return user_t


    def customize_userpolicy(self,affiliatedict):
        """customize_userpolicy. The method used to generate a policy that will allow users with the policy to run jobs in the relevant buckets.   

        :param affiliatedict: An affiliate dictionary containing the group name and member names of users. 
        :param bucketname: the name of the bucket for which this policy will grant access. 
        """
        affiliatename = affiliatedict["AffiliateName"]
        bucketnames = affiliatedict["Pipelines"]
        bucket_arns = [Join("",['arn:aws:s3:::',bucketname]) for bucketname in bucketnames]
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
            'Resource': bucket_arns, 
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
            'Resource': bucket_arns,
            'Condition':{'StringLike':{'s3:prefix':[
                Join("",[affiliatename,'/',indir,'/*']),
                Join("",[affiliatename,'/',outdir,'/*']),
                Join("",[affiliatename,'/',condir,'/*']),
                Join("",[affiliatename,'/',subdir,'/*'])
            ]}}})
        ## Give PUT, and DELETE permissions for the input, config, and submit subdirectories: 
        subfolder_arn_input_list = []
        for bucketname in bucketnames:
            for directory in [indir,condir,subdir]:
                subfolder_arn_input_list.append(
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',directory,'/*'])
                         )

        obj["Statement"].append({
            'Sid': 'Inputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:PutObject','s3:PutObjectTagging','s3:DeleteObject'],
            'Resource': subfolder_arn_input_list
             })
        
        ## Give GET, and DELETE permissions for the output, config and log subdirectory: 
        subfolder_arn_output_list = []
        for bucketname in bucketnames:
            for directory in [outdir,condir]:
                subfolder_arn_output_list.append(
                         Join("",['arn:aws:s3:::',bucketname,'/',affiliatename,'/',directory,'/*'])
                         )
        obj["Statement"].append({
           'Sid': 'Outputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:GetObject','s3:GetObjectTagging','s3:DeleteObject'],
            'Resource': subfolder_arn_output_list 
             })
        return obj

    #def add_log_folder(self,affiliatedicts,bucketname):
    #    """ Adds the directory infrastructure to a given analysis bucket that allows it to do logging. 
    #    this has to happen after affiliates are defined. Perhaps major difference from previous version: only creates affiliate subdirectory of full log directory, because that should already exist upon startup. 
    #    TODO: make this an add-only event, not parametrized by bucketname. . Lambda will auto-generate a folder for you, but it's better if you don't have to also. 

    #    """
    #    logfoldername = "LogFolder"

    #    ## Make a folder for each affiliate so they can be assigned completed jobs too. 
    #    for affdict in affiliatedicts:
    #        affiliatename = affdict["AffiliateName"]
    #        logaffmake,logaffdelete = self.attach_folder_resources(
    #                logfoldername+"Affiliate"+affiliatename,
    #                bucketname,
    #                self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
    #                affiliatename,
    #                )

class ReferenceFolderSubstackTemplate():
    """
    Puts all of the folder creation for a group and pipeline bucket into a substack template. 

    """
    def __init__(self):
        self.template = self.initialize_template()
        self.makefuncarn,self.delfuncarn,self.bucketname,self.name = self.add_affiliate_parameters()
        self.add_affiliate_folder()
        self.add_log_folder()

    def initialize_template(self):
        """
        Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
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
              a reference to the logical id of the folder making lambda function for the pipeline. 
              (Ref): 
              a reference to the physical resource id of the main analysis bucket for the pipeline. 
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
        BucketName = Parameter("BucketName",
                Description="PhysicalResourceId of the bucket for this pipeline.",
                Type = "String")
        Name = Parameter("Name",
                Description="Name of the user group.",
                Type = "String")

        ## Attach parameter
        MakeFuncArnAttached = self.template.add_parameter(MakeFuncArn)
        DelFuncArnAttached = self.template.add_parameter(DelFuncArn)
        BucketNameAttached = self.template.add_parameter(BucketName)
        NameAttached = self.template.add_parameter(Name)

        return Ref(MakeFuncArnAttached),Ref(DelFuncArnAttached),Ref(BucketNameAttached),Ref(NameAttached)

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
        folderid_alnum = ''.join(ch for ch in folderid if ch.isalnum())
        makeid = folderid_alnum+"make"
        delid = folderid_alnum+"del"
        if dependson is None:
            makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson)
            delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson)
        else:
            dependson_alnum = ''.join(ch for ch in dependson if ch.isalnum())
            makeattached = self.attach_folder_creator_function(makeid,bucketname,path,dirname,dependson_alnum+"make")
            delattached = self.attach_folder_deleter_function(delid,bucketname,path,dirname,dependson_alnum+"del")
        return makeattached,delattached

    def add_affiliate_folder(self):
        affiliatename = self.name
        bucketname = self.bucketname
        ## Declare depends on resources: 
        basefoldername = "AffiliateTemplateBaseFolder"+"usercentricsubstack"
        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basefolder,basefolderdelete = self.attach_folder_resources(basefoldername,bucketname,"",affiliatename)

        ## Designate cfn resource names for each: 
        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
        dirnamekeys = ["input_directory","output_directory","submission_directory","config_directory"]
        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
        for key in pairs:
            cfn_name = "AffiliateTemplate"+key+"usercentricsubstack"
            make,delete = self.attach_folder_resources(cfn_name,bucketname,Join("",[affiliatename,'/']),gpdict[pairs[key]],dependson = basefoldername)

    def add_log_folder(self):
        """ Adds the directory infrastructure to a given analysis bucket that allows it to do logging. 
        this has to happen after affiliates are defined. Perhaps major difference from previous version: only creates affiliate subdirectory of full log directory, because that should already exist upon startup. 
        TODO: make this an add-only event, not parametrized by bucketname. . Lambda will auto-generate a folder for you, but it's better if you don't have to also. 

        """
        logfoldername = "LogFolder"

        ## Make a folder for each affiliate so they can be assigned completed jobs too. 
        affiliatename = self.name 
        logaffmake,logaffdelete = self.attach_folder_resources(
                logfoldername+"Affiliate"+"usercentricsubstack",
                self.bucketname,
                gpdict["log_directory"]+'/',
                affiliatename,
                )
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
        ## Create new users with new directory structure. 
        utemp = UserTemplateWeb(filename)
        with open(dirname+"/"+"compiled_users.json","w") as f: 
            print(utemp.template.to_json(),file = f)
    elif stage == "webusercentric":
        ## Create new users, with new directory structure and user affiliated folders. 
        utemp = ReferenceUserCreationTemplate(filename)
        with open(dirname+"/"+"compiled_users.json","w") as f: 
            print(utemp.template.to_json(),file = f)




