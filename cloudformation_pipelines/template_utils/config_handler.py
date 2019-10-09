from troposphere import Ref,GetAtt,Template,Output,Join,Sub,AWS_STACK_NAME
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
import os

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
class NCAPTemplate(object):
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
        return obj

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

        ## Now we need to write a lambda function that actually does the work:  
        mkfunction = Function("S3PutObjectFunction",
                              CodeUri="../lambda_repo",
                              Description= "Puts Objects in S3",
                              Handler="helper.handler_mkdir",
                              Role=GetAtt(mkdirrole_attached,"Arn"),
                              Runtime="python3.6",
                              Timeout=30)
        mkfunction_attached = template.add_resource(mkfunction)
        delfunction = Function("S3DelObjectFunction",
                               CodeUri="../lambda_repo",
                               Description= "Deletes Objects from S3",
                               Handler="helper.handler_deldir",
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

    ## Take the template, and add in a bucket that takes the pipeline name as the name. 
    def add_bucket(self):
        bucketname = self.config['PipelineName']
        ## First check that the bucketname is valid: 
        assert type(bucketname) == str,"bucketname must be string"
        lowercase = bucketname.islower()
        underscore = '_' in bucketname 
        assert (lowercase and not(underscore)),'string must follow s3 bucket style'
        
        ## Now we can add this resource: 
        bucket = Bucket('PipelineMainBucket',AccessControl = 'Private',BucketName = bucketname)
        bucket_attached = self.template.add_resource(bucket)
        return bucket_attached,bucketname 

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
        ## Declare depends on resources: 
        bucketname = 'PipelineMainBucket'
        basefoldername = 'BaseFolder'+affiliatename
        infoldername = 'InFolder'+affiliatename
        outfoldername = 'OutFolder'+affiliatename
        logfoldername = 'LogFolder'+affiliatename

        ## Retrieve lambda function and role: 
        ## We will declare three custom resources per affiliate: 
        basemake = CustomResource(basefoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = "",
                                  DirName = affiliatename,
                                  DependsOn = bucketname)
        basefolder = self.template.add_resource(basemake)
        ## Now an input folder:
        inmake = CustomResource(infoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = affiliatename+'/',
                                  DirName = self.config['Lambda']['LambdaConfig']['INDIR'],
                                  DependsOn = [bucketname,basefoldername])
        infolder = self.template.add_resource(inmake)
        ## Likewise an output folder:
        outmake = CustomResource(outfoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = affiliatename+'/',
                                  DirName = self.config['Lambda']['LambdaConfig']['OUTDIR'],
                                  DependsOn = [bucketname,basefoldername])
        outfolder = self.template.add_resource(outmake)
        ## Likewise a log folder
        logmake = CustomResource(logfoldername,
                                  ServiceToken=GetAtt(self.mkdirfunc,"Arn"),
                                  BucketName = self.config['PipelineName'],
                                  Path = affiliatename+'/',
                                  DirName = self.config['Lambda']['LambdaConfig']['LOGDIR'],
                                  DependsOn = [bucketname,basefoldername])
        logfolder = self.template.add_resource(logmake)

    def add_affiliate_usernet(self,affiliatedict):
        ## Four steps here: 
        ## 1. Customize a user policy for this particular pipeline. 
        ## 2. Generate a user group with that policy. 
        ## 3. Generate users with credentials. 
        ## 4. Add users to group.  
        ## A method that customizes the json policy (see attached) to the particular affiliation name. 
        ## 1 and 2
        group = self.generate_usergroup(affiliatedict)
        ## 3 
        users = self.generate_users(affiliatedict)
        ## 4 
        users_attached = self.template.add_resource(UserToGroupAddition(affiliatedict['AffiliateName']+'UserNet',GroupName = Ref(group),Users = [Ref(u) for u in users]))

    def customize_userpolicy(self,affiliatedict):
        bucketname = self.config['PipelineName']
        affiliatename = affiliatedict["AffiliateName"]
        indir = self.config['Lambda']['LambdaConfig']['INDIR']
        outdir = self.config['Lambda']['LambdaConfig']['OUTDIR']
        logdir = self.config['Lambda']['LambdaConfig']['LOGDIR']
        ## First get the template policy 
        with open('policies/iam_user_base_policy_doc.json','r') as f:
            obj = json.load(f)
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
                affiliatename+'/'+logdir,
                affiliatename+'/'+indir+'/',
                affiliatename+'/'+outdir+'/',
                affiliatename+'/'+logdir+'/'
            ],'s3:delimiter':['/']}}})
        ## Give PUT, and DELETE permissions for the input subdirectory: 
        obj["Statement"].append({
            'Sid': 'Inputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:PutObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+indir+'/*']
             })
        ## Give GET, and DELETE permissions for the output and log subdirectory: 
        obj["Statement"].append({
            'Sid': 'Outputfolderwrite',
            'Effect': 'Allow',
            'Action': ['s3:GetObject','s3:DeleteObject'],
            'Resource': ['arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+outdir+'/*','arn:aws:s3:::'+bucketname+'/'+affiliatename+'/'+logdir+'/*']
             })
        with open('policies/'+affiliatename+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj

    def generate_usergroup(self,affiliatedict):
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = affiliatename+'policy')
        usergroup = Group("UserGroup"+affiliatename,GroupName = affiliatename+"group",Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

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
        user = User(affiliatename+'user'+str(username))

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
                readdir = self.config['Lambda']['LambdaConfig']['INDIR'] 
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
        #lambdaconfig ={}
        ### Most of the config can be done through the config file, but we will pass certain elements from the template. 
        lambdaconfig['figlambid'] = Ref(self.figurelamb) 
        lambdaconfig['figlambarn'] = GetAtt(self.figurelamb,'Arn')
        lambdaconfig['cwrolearn'] = GetAtt(self.cwrole,'Arn')
        ## Now add to a lambda function: 
        function = Function('MainLambda',
                CodeUri = '../lambda_repo',
                Runtime = 'python3.6',
                Handler = 'submit_start.handler',
                Description = 'Main Lambda Function for Serverless',
                MemorySize = 128,
                Timeout = self.config["Lambda"]['LambdaConfig']["EXECUTION_TIMEOUT"],
                Role = 'arn:aws:iam::739988523141:role/lambda_dataflow', ## TODO: Create this in template
                Events= all_events,
                #Environment = Environment(Variables={'figlambid':Ref(self.figurelamb),'figlambarn':GetAtt(self.figurelamb,'Arn'),'cwrolearn':GetAtt(self.cwrole,'Arn')})
                Environment = Environment(Variables=lambdaconfig)
                )         
        self.template.add_resource(function)

    ## Add in a lambda function to write cloudwatch events to s3 bucket "ncapctnfigures" 
    def add_figure_lambda(self):
        ## Now add to a lambda function: 
        function = Function('FigLambda',
                CodeUri = '../lambda_repo',
                Runtime = 'python3.6',
                Handler = 'log.eventshandler',
                Description = 'Lambda Function logging start/stop for NCAP',
                MemorySize = 128,
                Timeout = 90,
                Role = 'arn:aws:iam::739988523141:role/lambda_dataflow', ## TODO: Create this in template
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

if __name__ == "__main__":
    filename = sys.argv[1]
    dirname = os.path.dirname(filename)
    temp = NCAPTemplate(filename)
    with open(dirname+'/'+'compiled_template.json','w') as f:
        print(temp.template.to_json(),file = f)

