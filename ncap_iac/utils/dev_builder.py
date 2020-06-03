from troposphere import Ref,Parameter,GetAtt,Template,Output,Join,Split,Sub,AWS_STACK_NAME,AWS_REGION
from troposphere.s3 import Bucket,Rules,S3Key,Filter
from troposphere.iam import User,Group,Policy,ManagedPolicy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function,Environment
from troposphere.awslambda import Permission
from troposphere.logs import LogGroup
from troposphere.cloudformation import CustomResource,Stack 
from lambda_policies import lambda_basepolicy,lambda_writeS3
import sys
import json 
import subprocess
import secrets
import os
import boto3

## Import global parameters: 
with open("../global_params_initialized.json") as gp:
    gpdict = json.load(gp)

## Function that takes in a pipeline config file. 

## Pipelines that we design will all have a designated, predetermined structure. 
## 1. There is an AWS S3 bucket that contains all input and output from the instances that we have. This is necessary because we can only have s3 buckets declared in the same template as the lambda function we will use as event sources.  
## 2. There is an AWS Custom Resource that sets up user folders inside this bucket with input and output folders. 
## 3. There is a user group per affiliate that we have, to which we add users. All users in a given user group only have access to their folder, and furthermore only have write access to the input folder and get access from the output folder. Additional "users" can include lambda functions from other pipelines.  
## 4. There is a lambda function that is triggered by submit files when they are passed to the input folder. We should be able to add event sources to it as we update the number of users. In addition to the standard behavior, it should set up a cloudwatch events rule to monitor given instances for state change behavior.  
######## TODO: 
## 5. Output management. A secondary lambda function that sends notifications to an end user when processing is done. Additionally, we can use this to route output from a pipeline to another one.  
## 6. Centralized function source control. Create an AMI_updater custom resource, that takes the ami id associated with a given stack, instantiates it, pulls from the repository, and runs tests to make sure that everything is still fine. Compare with instantiating via CodeCommit/CodePipeline. 

## First define a function that loads the relevant config file into memory: 
class NeuroCaaSTemplate(object):
    """
    Base class for NeuroCaaS pipelines. Takes in a blueprint, and returns a viable cloudformation template that can be deployed into a pipeline.  
    1. There is an AWS S3 bucket that contains all input and output from the instances that we have. This is necessary because we can only have s3 buckets declared in the same template as the lambda function we will use as event sources.  
    2. There is an AWS Custom Resource that sets up user folders inside this bucket with input, config, submission, result and log folders. 
    3. There is a user group per affiliate that we have, to which we add users. All users in a given user group only have access to their folder, and furthermore only have write access to the input folder and get access from the output folder. Additional "users" can include lambda functions from other pipelines.  
    4. There is a lambda function that is triggered by submit files when they are passed to the input folder. We should be able to add event sources to it as we update the number of users. In addition to the standard behavior, it should set up a cloudwatch events rule to monitor given instances for state change behavior.  
    ##### TODO: 
    5. Output management. A secondary lambda function that sends notifications to an end user when processing is done. Additionally, we can use this to route output from a pipeline to another one.  
    6. Centralized function source control. Create an AMI_updater custom resource, that takes the ami id associated with a given stack, instantiates it, pulls from the repository, and runs tests to make sure that everything is still fine. Compare with instantiating via CodeCommit/CodePipeline. 
    The differences in this version are that we are only allowing ourselves to attach new users, not to define them.  

    inputs: 
    filename (str): the path to the stack_config_template.json blueprint that you want to deploy.
    """
    def __init__(self,filename):
        self.filename = filename
        self.config = self.get_config(self.filename)
        ## We should get all resources once attached. 
        self.template,self.mkdirfunc,self.deldirfunc = self.initialize_template()
        ## Add bucket: 
        self.bucket = self.add_bucket() 
        ## Now add affiliates:
        affiliatedicts = self.config['UXData']['Affiliates']
        for affdict in affiliatedicts:
            self.add_affiliate(affdict)
        self.figurelamb = self.add_figure_lambda()
        self.add_submit_lambda()
        
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
            obj['PipelineName']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        try: 
            obj['REGION']
        except Exception as e: 
            print('config file missing key attribute',e )
            error += 1
        try: 
            obj['Lambda']
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

    ## Now initialize a template. this just involves applying the serverless transform and adding the resources necessary to get our custom resources up and running. 
    def initialize_template(self):
        raise NotImplementedError

    ## Take the template, and add in a bucket that takes the pipeline name as the name. 
    def add_bucket(self):
        bucket_id = "PipelineMainBucket"
        bucketname = self.config['PipelineName']
        ## First check that the bucketname is valid: 
        assert type(bucketname) == str,"bucketname must be string"
        lowercase = bucketname.islower()
        underscore = '_' in bucketname 
        assert (lowercase and not(underscore)),'string must follow s3 bucket style'
        
        ## Now we can add this resource: 
        bucket = Bucket(bucket_id,AccessControl = 'Private',BucketName = bucketname)
        bucket_attached = self.template.add_resource(bucket)
        return bucket_attached,bucketname,bucket_id 

    def add_affiliate(self,affiliatedict):
        '''
        when passed an affiliate dictionary, does two things. 1. creates the folder structure that is appropriate for this affiliate, and 2. adds a user group and users that can interact appropriately with this folder structure.
        '''
        ## First create folder structure
        affiliatename = affiliatedict['AffiliateName']
        self.add_affiliate_folder(affiliatename)
        ## Now create the usergroup to read/write appropriately. 
        self.add_affiliate_usernet(affiliatedict)

    def add_affiliate_folder(self,affiliatename):
        raise NotImplementedError

    def attach_users(self,affiliatedict):
        """Function to vet if the users we want to attach actually exist. 

        """
        print(affiliatedict,"affiliatedict")
        ## First get a list of usernames. 
        users = affiliatedict['UserNames']
        affiliatename = affiliatedict['AffiliateName']
        ## Initialize list of users: 
        affiliate_users = []
        affiliate_usernames = []
        err = 0
        for user in users:
            try:
                # Filter for existing: we only want to treat users who have already been declared elsewhere. 
                ## Get the internal user name filtered by region:
                user_local = user+self.config["Lambda"]["LambdaConfig"]["REGION"]
                self.iam_resource.User(user_local).create_date
                print("User {} exists, adding to group".format(user))
                ## Now ask if we are just updating an existing stack: 
                ## Get the groupname we will assign: 
                identifier = "{}".format(self.config["PipelineName"].replace("-",""))
                affiliatename = affiliatedict["AffiliateName"]
                groupname = "".join([affiliatename,identifier,"group"])
                grouplist = self.iam_client.list_groups_for_user(UserName=user_local)["Groups"]
                groupnameslist = [entry["GroupName"] for entry in grouplist]
                ## Check to make sure: 
                if groupname in groupnameslist:
                    ## This us just an update, we can allow it to pass.
                    pass
                else:
                    ## We need to watch out for the existing user group limit.
                    assert len(grouplist) < 10, "user can only belong to 10 groups."
                print("User currently belongs to {} groups".format(len(grouplist)))
                affiliate_users.append(self.iam_resource.User(user_local))
                affiliate_usernames.append(user_local)
            except Exception as e: 
                print("Error adding User {}, please evaluate".format(user),e)
                raise

        return affiliate_users,affiliate_usernames

    def add_affiliate_usernet(self,affiliatedict):
        ## Four steps here: 
        ## 1. Customize a user policy for this particular pipeline. 
        ## 2. Generate a user group with that policy. 
        ## 3. Attach users with credentials. 
        ## 4. Add users to group.  
        ## A method that customizes the json policy (see attached) to the particular affiliation name. 
        ## 1 and 2
        group = self.generate_usergroup(affiliatedict)
        ## 3 
        ## Note: this filters in the case where users are predefined elsewhere. 
        users,usernames  = self.attach_users(affiliatedict)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition(affiliatedict['AffiliateName']+'UserNet',GroupName = Ref(group),Users = usernames))

    def customize_userpolicy(self,affiliatedict):
        raise NotImplementedError

    def generate_usergroup(self,affiliatedict):
        raise NotImplementedError

    def generate_users(self,affiliatedict):
        ## First get a list of usernames. 
        users = affiliatedict['UserNames']
        affiliatename = affiliatedict['AffiliateName']
        ## Initialize list of users: 
        affiliate_users = []
        for user in users:
            affiliate_users.append(self.generate_user_with_creds(user,affiliatename))
        return affiliate_users
        
    def generate_user_with_creds(self,username,affiliatename,password = True,accesskey = True):
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True, 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        user = User(affiliatename+'user'+str(username),UserName=username)

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

    ## We can now move on to the actual lambda function!!
    def add_submit_lambda(self):
        ## We will make event triggers for all affiliates. 
        all_affiliates = self.config["UXData"]["Affiliates"]
        ## Make Rule sets for each affiliate: 
        all_events = {}
        for affiliate in all_affiliates: 
            ## Get necessary properties: 
            affiliatename = affiliate["AffiliateName"]
            ## If user input, reads directly from input directory. If other function output, reads from output directory.
            assert type(affiliate["UserInput"]) == bool, "must provide a json boolean for UserInput"
            if affiliate["UserInput"] == True:
                readdir = self.config['Lambda']['LambdaConfig']['SUBMITDIR'] 
            elif affiliate["UserInput"] == False: 
                readdir = self.config['Lambda']['LambdaConfig']['OUTDIR'] 

            aff_filter = Filter('Filter'+affiliatename,
                    S3Key = S3Key('S3Key'+affiliatename,
                        Rules= [Rules('PrefixRule'+affiliatename,Name = 'prefix',Value = affiliatename+'/'+readdir),
                                Rules('SuffixRule'+affiliatename,Name = 'suffix',Value = 'submit.json')])) 
            event_name = 'BucketEvent'+affiliatename
            all_events[event_name] = {'Type':'S3',
                                      'Properties':{
                                          'Bucket':Ref('PipelineMainBucket'),
                                          'Events':['s3:ObjectCreated:*'],
                                          'Filter':aff_filter}}
        ## We're going to add in all of the lambda configuration items to the runtime environment.
        lambdaconfig = self.config['Lambda']['LambdaConfig']
        ### Most of the config can be done through the config file, but we will pass certain elements from the template. 
        lambdaconfig['figlambid'] = Ref(self.figurelamb) 
        lambdaconfig['figlambarn'] = GetAtt(self.figurelamb,'Arn')
        lambdaconfig['cwrolearn'] = GetAtt(self.cwrole,'Arn')

        ## Additionally, we're going to add in the git commit version. 
        lambdaconfig['versionid'] = subprocess.check_output(["git","rev-parse","HEAD"]).decode("utf-8") 
        ## Now add to a lambda function: 
        function = Function('MainLambda',
                CodeUri = self.config['Lambda']["CodeUri"],##'../lambda_repo',
                Runtime = 'python3.6',
                Handler = self.config['Lambda']["Handler"],##'submit_start.handler',
                Description = 'Main Lambda Function for Serverless',
                MemorySize = 128,
                Timeout = self.config["Lambda"]['LambdaConfig']["EXECUTION_TIMEOUT"],
                #Role = 'arn:aws:iam::739988523141:role/testutilsstack-LambdaRole-1I7AHKZQN6WOJ', ## TODO: Create this in template
                Role = 'arn:aws:iam::{accid}:role/{role}'.format(accid = boto3.client('sts').get_caller_identity().get('Account'),role = gpdict['lambdarolename']),
                Events= all_events,
                #Environment = Environment(Variables={'figlambid':Ref(self.figurelamb),'figlambarn':GetAtt(self.figurelamb,'Arn'),'cwrolearn':GetAtt(self.cwrole,'Arn')})
                Environment = Environment(Variables=lambdaconfig)
                )         
        self.template.add_resource(function)

    ## Add in a lambda function to write cloudwatch events to s3 bucket "ncapctnfigures" 
    def add_figure_lambda(self):
        ## The figure lambda function needs the following information: 
        # 1. the development bucket where it should be writing this info. 
        # 2. 
        ## Now add to a lambda function: 
        function = Function('FigLambda',
                CodeUri = '../../protocols',
                Runtime = 'python3.6',
                Handler = 'log.monitor_updater',
                Description = 'Lambda Function logging start/stop for NCAP',
                MemorySize = 128,
                Timeout = 90,
                Role = 'arn:aws:iam::{accid}:role/{role}'.format(accid = boto3.client('sts').get_caller_identity().get('Account'),role = gpdict['lambdarolename']),
                Environment = Environment(Variables={"BUCKET_NAME":self.config["PipelineName"],
                    "INDIR":self.config['Lambda']['LambdaConfig']['INDIR'],
                    "REGION":self.config["REGION"]
                    }),
                Events= {})         
        figurelamb = self.template.add_resource(function)
        ## Attach specific permissions to invoke this lambda function as well. 
        cwpermission = Permission('CWPermissions',
                Action = 'lambda:InvokeFunction',
                Principal = 'events.amazonaws.com',
                FunctionName = Ref(figurelamb))
        self.template.add_resource(cwpermission)
        
        ## Because this lambda function gets invoked by an unknown target, we need to take care of its log group separately. 
        
        figloggroup = LogGroup('FignameLogGroup',LogGroupName=Sub("/aws/lambda/${FigLambda}"))
        self.template.add_resource(figloggroup)

        ## Now we need to configure this function as a potential target. 
        ## Initialize role to send events to cloudwatch
        with open('policies/cloudwatch_events_assume_role_doc.json','r') as f:
            cloudwatchassume_role_doc = json.load(f)
        ## Now get the actual policy: 
        with open('policies/cloudwatch_events_policy_doc.json','r') as f:
            cloudwatch_policy_doc = json.load(f)
        cloudwatchpolicy = ManagedPolicy("CloudwatchBusPolicy",
                Description = Join(" ",["Base Policy for all lambda function roles in",Ref(AWS_STACK_NAME)]),
                PolicyDocument = cloudwatch_policy_doc)
        self.template.add_resource(cloudwatchpolicy)
        ## create the role: 
        cwrole = Role("CloudWatchBusRole",
                AssumeRolePolicyDocument=cloudwatchassume_role_doc,
                ManagedPolicyArns = [Ref(cloudwatchpolicy)])
        cwrole_attached = self.template.add_resource(cwrole)
        self.cwrole = cwrole_attached
        return figurelamb

## First define a function that loads the relevant config file into memory: 
class DevTemplate(NeuroCaaSTemplate):
    """
    Dev mode pipelines are not hooked up to all users, and explicitly grant individuals access to a dedicated analysis bucket. Input locations are localized to the analysis bucket in the dev case.  

    inputs: 
    filename (str): the path to the stack_config_template.json blueprint that you want to deploy.
    """
    def __init__(self,filename):
        self.filename = filename
        self.config = self.get_config(self.filename)
        self.iam_resource = boto3.resource('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        ## We should get all resources once attached. 
        self.template,self.mkdirfunc,self.deldirfunc = self.initialize_template()
        ## Add bucket: 
        self.bucket = self.add_bucket() 
        ## Now add affiliates:
        affiliatedicts = self.config['UXData']['Affiliates']
        for affdict in affiliatedicts:
            self.add_affiliate(affdict)
        self.add_log_folder(affiliatedicts)
        self.figurelamb = self.add_figure_lambda()
        self.add_submit_lambda()

    def initialize_template(self):
        """
        Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
        """
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
        ## Custom resource to delete. 
        delresource = CustomResource('DeleteCustomResource',
                             ServiceToken=GetAtt(delfunction_attached,"Arn"),
                             BucketName = self.config['PipelineName'],
                             DependsOn = 'PipelineMainBucket')
        template.add_resource(delresource)
        ## We can add other custom resource initializations in the future
        return template,mkfunction_attached,delfunction_attached

    def generate_usergroup(self,affiliatedict):
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = affiliatename+'policy')
        usergroup = Group("UserGroup"+affiliatename,GroupName = affiliatename+"group",Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def add_log_folder(self,affiliatedicts):
        "this has to happen after affiliates are defined"
        bucketname = 'PipelineMainBucket'
        logfoldername = "LogFolder"

        ## A log folder to keep track of all resource monitoring across all users.  
        logmake = CustomResource(logfoldername,
                                 ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                 BucketName = self.config['PipelineName'],
                                 Path = "",
                                 DirName = self.config['Lambda']['LambdaConfig']['LOGDIR'],
                                 DependsOn = bucketname)
        logfolder = self.template.add_resource(logmake)

        ## Make an "active jobs" subfolder within: 
        logactivemake = CustomResource(logfoldername+"active",
                                 ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                 BucketName = self.config['PipelineName'],
                                 Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                 DirName = "active",
                                 DependsOn = [bucketname,logfoldername])
        logactivefolder = self.template.add_resource(logactivemake)

        ## Make a folder for each affiliate so they can be assigned completed jobs too. 
        for affdict in affiliatedicts:
            print(affdict,"dict here")
            affiliatename = affdict["AffiliateName"]
            logaffmake = CustomResource(logfoldername+affiliatename,
                                     ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                     BucketName = self.config['PipelineName'],
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = affiliatename,
                                     DependsOn = [bucketname,logfoldername])
            logafffolder = self.template.add_resource(logaffmake)

        ## Finally, make a "debug" folder that will always exist: 
        logdebugmake = CustomResource(logfoldername+"debug",
                                     ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                     BucketName = self.config['PipelineName'],
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = "debug"+self.config["PipelineName"],
                                     DependsOn = [bucketname,logfoldername])
        logdebugfolder = self.template.add_resource(logdebugmake)



    def add_affiliate_folder(self,affiliatename):
        ## Declare depends on resources: 
        bucketname = 'PipelineMainBucket'
        basefoldername = "BaseFolder"+affiliatename

        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basemake = CustomResource(basefoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = "",
                                  DirName = affiliatename,
                                  DependsOn = bucketname)
        basefolder = self.template.add_resource(basemake)

        ## Designate cfn resource names for each: 
        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
        dirnamekeys = ["INDIR","OUTDIR","SUBMITDIR","CONFIGDIR"]
        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
        for key in pairs:
            cfn_name = key+affiliatename
            make = CustomResource(cfn_name,
                                      ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                      BucketName = self.config['PipelineName'],
                                      Path = affiliatename+'/',
                                      DirName = self.config['Lambda']['LambdaConfig'][pairs[key]],
                                      DependsOn = [bucketname,basefoldername])
            folder = self.template.add_resource(make)

    def customize_userpolicy(self,affiliatedict):
        bucketname = self.config['PipelineName']
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
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringEquals':{'s3:prefix':['',
                affiliatename+'/',
                affiliatename+'/'+indir,
                affiliatename+'/'+outdir,
                logdir,
                affiliatename+'/'+subdir,
                affiliatename+'/'+condir,
                affiliatename+'/'+indir+'/',
                affiliatename+'/'+outdir+'/',
                affiliatename+'/'+subdir+'/',
                affiliatename+'/'+condir+'/'
            ],'s3:delimiter':['/']}}})
        ## Give LIST permissions within all subdirectories too. 
        obj["Statement"].append({
            'Sid': "ListSubBucket",
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringLike':{'s3:prefix':[
                affiliatename+'/'+indir+'/*',
                affiliatename+'/'+outdir+'/*',
                affiliatename+'/'+condir+'/*',
                affiliatename+'/'+subdir+'/*'
            ]}}})
        ## Give PUT, and DELETE permissions for the input, config, and submit subdirectories: 
        obj["Statement"].append({
            'Sid': 'Inputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:PutObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+indir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+condir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+subdir+'/*'
                         ]
             })
        
        ## Give GET, and DELETE permissions for the output, config and log subdirectory: 
        obj["Statement"].append({
           'Sid': 'Outputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:GetObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+outdir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+condir+'/*',
                         ]
             })
        with open('policies/'+affiliatename+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj
    

class WebDevTemplate(NeuroCaaSTemplate):
    """
    Dev mode pipelines are not hooked up to all users, and explicitly grant individuals access to a dedicated analysis bucket. Input locations are localized to the analysis bucket in the dev case.  

    inputs: 
    filename (str): the path to the stack_config_template.json blueprint that you want to deploy.
    """
    def __init__(self,filename):
        self.filename = filename
        self.config = self.get_config(self.filename)
        self.iam_resource = boto3.resource('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        self.iam_client = boto3.client('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        ## We should get all resources once attached. 
        self.template,self.mkdirfunc,self.deldirfunc = self.initialize_template()
        ## Add bucket: 
        self.bucket = self.add_bucket() 
        ## Now add affiliates:
        affiliatedicts = self.config['UXData']['Affiliates']
        for affdict in affiliatedicts:
            self.add_affiliate(affdict)
        self.add_log_folder(affiliatedicts)
        self.figurelamb = self.add_figure_lambda()
        self.add_submit_lambda()

    def generate_usergroup(self,affiliatedict):
        identifier = "{}".format(self.config["PipelineName"].replace("-",""))
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = affiliatename+'policy')
        usergroup = Group("UserGroup"+affiliatename+identifier,GroupName = affiliatename+identifier+"group",Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def initialize_template(self):
        """
        Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
        """
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
        ## Custom resource to delete. 
        delresource = CustomResource('DeleteCustomResource',
                             ServiceToken=GetAtt(delfunction_attached,"Arn"),
                             BucketName = self.config['PipelineName'],
                             DependsOn = 'PipelineMainBucket')
        template.add_resource(delresource)
        ## We can add other custom resource initializations in the future
        return template,mkfunction_attached,delfunction_attached

    def add_log_folder(self,affiliatedicts):
        "this has to happen after affiliates are defined"
        bucketname = 'PipelineMainBucket'
        logfoldername = "LogFolder"

        ## A log folder to keep track of all resource monitoring across all users.  
        logmake = CustomResource(logfoldername,
                                 ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                 BucketName = self.config['PipelineName'],
                                 Path = "",
                                 DirName = self.config['Lambda']['LambdaConfig']['LOGDIR'],
                                 DependsOn = bucketname)
        logfolder = self.template.add_resource(logmake)

        ## Make an "active jobs" subfolder within: 
        logactivemake = CustomResource(logfoldername+"active",
                                 ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                 BucketName = self.config['PipelineName'],
                                 Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                 DirName = "active",
                                 DependsOn = [bucketname,logfoldername])
        logactivefolder = self.template.add_resource(logactivemake)

        ## Make a folder for each affiliate so they can be assigned completed jobs too. 
        for affdict in affiliatedicts:
            print(affdict,"dict here")
            affiliatename = affdict["AffiliateName"]
            logaffmake = CustomResource(logfoldername+affiliatename,
                                     ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                     BucketName = self.config['PipelineName'],
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = affiliatename,
                                     DependsOn = [bucketname,logfoldername])
            logafffolder = self.template.add_resource(logaffmake)

        ## Finally, make a "debug" folder that will always exist: 
        logdebugmake = CustomResource(logfoldername+"debug",
                                     ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                     BucketName = self.config['PipelineName'],
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = "debug"+self.config["PipelineName"],
                                     DependsOn = [bucketname,logfoldername])
        logdebugfolder = self.template.add_resource(logdebugmake)



    def add_affiliate_folder(self,affiliatename):
        ## Declare depends on resources: 
        bucketname = 'PipelineMainBucket'
        basefoldername = "BaseFolder"+affiliatename

        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basemake = CustomResource(basefoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = "",
                                  DirName = affiliatename,
                                  DependsOn = bucketname)
        basefolder = self.template.add_resource(basemake)

        ## Designate cfn resource names for each: 
        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
        dirnamekeys = ["INDIR","OUTDIR","SUBMITDIR","CONFIGDIR"]
        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
        for key in pairs:
            cfn_name = key+affiliatename
            make = CustomResource(cfn_name,
                                      ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                      BucketName = self.config['PipelineName'],
                                      Path = affiliatename+'/',
                                      DirName = self.config['Lambda']['LambdaConfig'][pairs[key]],
                                      DependsOn = [bucketname,basefoldername])
            folder = self.template.add_resource(make)

    def customize_userpolicy(self,affiliatedict):
        bucketname = self.config['PipelineName']
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
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringEquals':{'s3:prefix':['',
                affiliatename+'/',
                affiliatename+'/'+indir,
                affiliatename+'/'+outdir,
                logdir,
                affiliatename+'/'+subdir,
                affiliatename+'/'+condir,
                affiliatename+'/'+indir+'/',
                affiliatename+'/'+outdir+'/',
                affiliatename+'/'+subdir+'/',
                affiliatename+'/'+condir+'/'
            ],'s3:delimiter':['/']}}})
        ## Give LIST permissions within all subdirectories too. 
        obj["Statement"].append({
            'Sid': "ListSubBucket",
            'Effect': 'Allow',
            'Action': 's3:ListBucket',
            'Resource': ['arn:aws:s3:::'+bucketname],
            'Condition':{'StringLike':{'s3:prefix':[
                affiliatename+'/'+indir+'/*',
                affiliatename+'/'+outdir+'/*',
                affiliatename+'/'+condir+'/*',
                affiliatename+'/'+subdir+'/*'
            ]}}})
        ## Give PUT, and DELETE permissions for the input, config, and submit subdirectories: 
        obj["Statement"].append({
            'Sid': 'Inputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:PutObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+indir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+condir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+subdir+'/*'
                         ]
             })
        
        ## Give GET, and DELETE permissions for the output, config and log subdirectory: 
        obj["Statement"].append({
           'Sid': 'Outputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:GetObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+outdir+'/*',
                         'arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+condir+'/*',
                         ]
             })
        with open('policies/'+affiliatename+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj
    

## Call the substack given.  
class WebSubstackTemplate(NeuroCaaSTemplate):
    """Created 6/1/20. Newest version of the neurocaas pipeline template that makes use of substacks for every individual affiliate group. 
    """
    def __init__(self,filename):
        self.filename = filename
        self.config = self.get_config(self.filename)
        self.iam_resource = boto3.resource('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        self.iam_client = boto3.client('iam',region_name = self.config['Lambda']["LambdaConfig"]["REGION"]) 
        ## Initialize. 
        self.template = self.initialize_template()
        ## Add a bucket.
        self.bucket,self.bucketname,self.bucket_logical_id = self.add_bucket()
        ## Add make and delete directory functions. 
        self.mkdirfunc,self.deldirfunc,self.mkfunction_logical_id,self.delfunction_logical_id = self.make_custom_resources()
        ## Now iterate through affiliates:
        for a,affiliatedict in enumerate(self.config["UXData"]["Affiliates"]):
            ## Filter the names of users to also include the region. 
            users,usernames  = self.attach_users(affiliatedict)
            ## Get the parameters in the correct form.
            name = affiliatedict["AffiliateName"]
            ## Concatenate the usernames (substack can't take list param, must take string.) 
            usernames_concat = ",".join(usernames)
            substack = Stack(
                    "UserSubstack{}".format(a),
                    TemplateURL="../utils_stack/user_subtemplate_packaged.yaml", ## This should be a file that has had sam-package already run on it. 
                    Parameters = {
                        "MakeFuncArn":GetAtt(self.mkdirfunc,"Arn"),#Ref(self.bucket),
                        "BucketName":self.bucketname,
                        "Name":name,
                        "UserNames":usernames_concat
                        },
                    DependsOn=[self.bucket_logical_id,self.mkfunction_logical_id,self.delfunction_logical_id])
            self.template.add_resource(substack)
        self.figurelamb = self.add_figure_lambda()
        self.add_submit_lambda()

    def initialize_template(self):
        """
        Defining function for development mode template. Makes per-dev group folders. NOTE: once folders have been created, they will not be modified by additional updates. This protects user data. 
        """
        template = Template()
        ## Apply a transform to use serverless functions. 
        template.set_transform("AWS::Serverless-2016-10-31")
        return template
        
    def attach_users(self,affiliatedict):
        """Function to vet if the users we want to attach actually exist. 

        """
        print(affiliatedict,"affiliatedict")
        ## First get a list of usernames. 
        users = affiliatedict['UserNames']
        affiliatename = affiliatedict['AffiliateName']
        ## Initialize list of users: 
        affiliate_users = []
        affiliate_usernames = []
        err = 0
        for user in users:
            try:
                # Filter for existing: we only want to treat users who have already been declared elsewhere. 
                ## Get the internal user name filtered by region:
                user_local = user+self.config["Lambda"]["LambdaConfig"]["REGION"]
                self.iam_resource.User(user_local).create_date
                print("User {} exists, adding to group".format(user))
                ## Now ask if we are just updating an existing stack: 
                ## Get the groupname we will assign: 
                identifier = "{}".format(self.config["PipelineName"].replace("-",""))
                affiliatename = affiliatedict["AffiliateName"]
                groupname = "".join([affiliatename,identifier,"substackgroup"])
                grouplist = self.iam_client.list_groups_for_user(UserName=user_local)["Groups"]
                groupnameslist = [entry["GroupName"] for entry in grouplist]
                ## Check to make sure: 
                if groupname in groupnameslist:
                    ## This us just an update, we can allow it to pass.
                    pass
                else:
                    ## We need to watch out for the existing user group limit.
                    assert len(grouplist) < 10, "user can only belong to 10 groups."
                print("User currently belongs to {} groups".format(len(grouplist)))
                affiliate_users.append(self.iam_resource.User(user_local))
                affiliate_usernames.append(user_local)
            except Exception as e: 
                print("Error adding User {}, please evaluate".format(user),e)
                raise

        return affiliate_users,affiliate_usernames

    def make_custom_resources(self):
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
        self.template.add_resource(base_policy)
        mkdirrole = Role("S3MakePathRole",
                AssumeRolePolicyDocument=mkdirassume_role_doc,
                ManagedPolicyArns=[Ref(base_policy)],
                Policies = [write_policy])
        mkdirrole_attached = self.template.add_resource(mkdirrole)

        ## Get the lambda config parameters for initialization of the custom resource delete function [needs the region]
        lambdaconfig = self.config['Lambda']['LambdaConfig']

        ## Now we need to write a lambda function that actually does the work:  
        mkfunction_logical_id = "S3PutObjectFunction"
        mkfunction = Function(mkfunction_logical_id,
                              CodeUri="../../protocols",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Environment = Environment(Variables=lambdaconfig),
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = self.template.add_resource(mkfunction)
        delfunction_logical_id = "S3DelObjectFunction"
        delfunction = Function(delfunction_logical_id,
                               CodeUri="../../protocols",
                               Description= "Deletes Objects from S3",
                               Handler="helper.handler_deldir",
                               Environment = Environment(Variables=lambdaconfig),
                               Role=GetAtt(mkdirrole_attached,"Arn"),
                               Runtime="python3.6",
                               Timeout=30)
        delfunction_attached = self.template.add_resource(delfunction)
        ## Custom resource to delete. 
        delresource = CustomResource('DeleteCustomResource',
                             ServiceToken=GetAtt(delfunction_attached,"Arn"),
                             BucketName = self.config['PipelineName'],
                             DependsOn = self.bucket_logical_id)
        self.template.add_resource(delresource)
        ## We can add other custom resource initializations in the future
        return mkfunction_attached,delfunction_attached,mkfunction_logical_id,delfunction_logical_id

## Make a parametrized version of the user template.  
class ReferenceUserSubstackTemplate(NeuroCaaSTemplate):
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
        self.makefuncarn,self.bucketname,affdict_params = self.add_affiliate_parameters()
        ## Now add affiliates:
        self.add_affiliate(affdict_params)
        self.add_log_folder([affdict_params])

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
        BucketName = Parameter("BucketName",
                Description="PhysicalResourceId of the bucket for this pipeline.",
                Type = "String")
        Name = Parameter("Name",
                Description="Name of the user group.",
                Type = "String")
        UserNames = Parameter("UserNames",
                Description="List of the users in this group who should be added to this group.",
                Type = "String")

        ## Attach parameter
        MakeFuncArnAttached = self.template.add_parameter(MakeFuncArn)
        BucketNameAttached = self.template.add_parameter(BucketName)
        NameAttached = self.template.add_parameter(Name)
        UserNamesAttached = self.template.add_parameter(UserNames)

        ## Add to a dictionary: 
        affiliatedict_params = {"AffiliateName":Ref(NameAttached),
                "UserNames":Ref(UserNamesAttached)}

        return Ref(MakeFuncArnAttached),Ref(BucketNameAttached),affiliatedict_params

    def add_affiliate_folder(self,affiliatename):
        ## Declare depends on resources: 
        basefoldername = "AffiliateTemplateBaseFolder" 
        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basemake = CustomResource(basefoldername,
                                  ServiceToken=self.makefuncarn,
                                  BucketName = self.bucketname,
                                  Path = "",
                                  DirName = affiliatename)
        basefolder = self.template.add_resource(basemake)

        ## Designate cfn resource names for each: 
        basenames = ["InFolder","OutFolder","SubmitFolder","ConfigFolder"]
        dirnamekeys = ["INDIR","OUTDIR","SUBMITDIR","CONFIGDIR"]
        pairs = {b:d for b,d in zip(basenames,dirnamekeys)}
        for key in pairs:
            cfn_name = key+"AffiliateTemplate"
            make = CustomResource(cfn_name,
                                      ServiceToken=self.makefuncarn,
                                      BucketName = self.bucketname,
                                      Path = Join("",[affiliatename,'/']),
                                      DirName = self.config['Lambda']['LambdaConfig'][pairs[key]],
                                      DependsOn = basefoldername)
            folder = self.template.add_resource(make)

    def customize_userpolicy(self,affiliatedict):
        bucketname = self.bucketname
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
        #with open(Join("",['policies/',affiliatename,'_policy.json']),'w') as fw: 
        #    json.dump(obj,fw,indent = 2)
        return obj

    def generate_usergroup(self,affiliatedict):
        #identifier = "{}".format(self.config["PipelineName"].replace("-",""))
        identifier = Join("",Split("-",self.bucketname))
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = Join("",[affiliatename,'policy']))
        usergroup = Group("UserGroupAffiliateTemplate",GroupName = Join("",[affiliatename,identifier,"substackgroup"]),Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached


    def add_affiliate_usernet(self,affiliatedict):
        ## Four steps here: 
        ## 1. Customize a user policy for this particular pipeline. 
        ## 2. Generate a user group with that policy. 
        ## 3. Attach users with credentials. 
        ## 4. Add users to group.  
        ## A method that customizes the json policy (see attached) to the particular affiliation name. 
        ## 1 and 2
        group = self.generate_usergroup(affiliatedict)
        ## 3 
        ## Note: this filters in the case where users are predefined elsewhere. 
        #users,usernames  = self.attach_users(affiliatedict)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition('AffiliateTemplate'+'UserNet',GroupName = Ref(group),Users = Split(",",affiliatedict["UserNames"])))

    def add_log_folder(self,affiliatedicts):
        "this has to happen after affiliates are defined"
        logfoldername = "LogFolder"

        ## A log folder to keep track of all resource monitoring across all users.  
        logmake = CustomResource(logfoldername,
                                 ServiceToken=self.makefuncarn,
                                 BucketName = self.bucketname,
                                 Path = "",
                                 DirName = self.config['Lambda']['LambdaConfig']['LOGDIR'])
        logfolder = self.template.add_resource(logmake)

        ## Make an "active jobs" subfolder within: 
        logactivemake = CustomResource(logfoldername+"active",
                                 ServiceToken=self.makefuncarn,
                                 BucketName = self.bucketname,
                                 Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                 DirName = "active",
                                 DependsOn = logfoldername)
        logactivefolder = self.template.add_resource(logactivemake)

        ## Make a folder for each affiliate so they can be assigned completed jobs too. 
        for affdict in affiliatedicts:
            print(affdict,"dict here")
            affiliatename = affdict["AffiliateName"]
            logaffmake = CustomResource(logfoldername+"AffiliateTemplate",
                                     ServiceToken=self.makefuncarn,
                                     BucketName = self.bucketname,
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = affiliatename,
                                     DependsOn = logfoldername)
            logafffolder = self.template.add_resource(logaffmake)

        ## Finally, make a "debug" folder that will always exist: 
        logdebugmake = CustomResource(logfoldername+"debug",
                                     ServiceToken=self.makefuncarn,
                                     BucketName = self.bucketname,
                                     Path = self.config['Lambda']['LambdaConfig']['LOGDIR']+'/',
                                     DirName = "debug"+self.config["PipelineName"],
                                     DependsOn = logfoldername)
        logdebugfolder = self.template.add_resource(logdebugmake)

if __name__ == "__main__":
    filename = sys.argv[1]
    mode = sys.argv[2]
    dirname = os.path.dirname(filename)
    ## Create any new users that have not yet been declared. 
    ## utemp = UserTemplate(filename)
    ## with open(dirname+"/"+"compiled_users.json","w") as f:$ 
        #print(utemp.template.to_json(),file = f)
    print(mode,"mode")
    if mode == "develop":
        print("develop mode")
        ## Construct a development mode pipeline.  
        temp =DevTemplate(filename)
        with open(dirname+'/'+'compiled_template.json','w') as f:
            print(temp.template.to_json(),file = f)
    elif mode == "webdev":
        print("webdev mode")
        ## Construct a web development mode pipeline. Standardizes user group handling for neatness. 
        temp =WebDevTemplate(filename)
        with open(dirname+'/'+'compiled_template.json','w') as f:
            print(temp.template.to_json(),file = f)
    elif mode == "websubstack":
        print("factorized substack mode")
        ## Constructs a new version of web dev pipelines that scales to many users by referencing a parametrized substack for every user group.  
        temp =WebSubstackTemplate(filename) 
        with open(dirname+'/'+'compiled_template.json','w') as f:
            print(temp.template.to_json(),file = f)
    else:
        print("mode {} not implemented yet or does not exist.".format(mode))

    ## 

