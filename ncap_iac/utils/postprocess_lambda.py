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
import os
import boto3
from config_handler import NCAPTemplate


## Function that takes in the pipeline config file for epi and creates an additional lambda function to monitor the results bucket. s 

## Pipelines that we design will all have a designated, predetermined structure. 
## 1. There is an AWS S3 bucket that contains all input and output from the instances that we have. This is necessary because we can only have s3 buckets declared in the same template as the lambda function we will use as event sources.  
## 2. There is an AWS Custom Resource that sets up user folders inside this bucket with input and output folders. 
## 3. There is a user group per affiliate that we have, to which we add users. All users in a given user group only have access to their folder, and furthermore only have write access to the input folder and get access from the output folder. Additional "users" can include lambda functions from other pipelines.  
## 4. There is a lambda function that is triggered by submit files when they are passed to the input folder. We should be able to add event sources to it as we update the number of users. In addition to the standard behavior, it should set up a cloudwatch events rule to monitor given instances for state change behavior.  
######## TODO: 
## 5. Output management. A secondary lambda function that sends notifications to an end user when processing is done. Additionally, we can use this to route output from a pipeline to another one.  
## 6. Centralized function source control. Create an AMI_updater custom resource, that takes the ami id associated with a given stack, instantiates it, pulls from the repository, and runs tests to make sure that everything is still fine. Compare with instantiating via CodeCommit/CodePipeline. 



## First define a function that loads the relevant config file into memory: 
class PipelineTemplate(NCAPTemplate):
    ## The differences in this version are that we are only allowing ourselves to attach new users, not to define them.  
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
        self.figurelamb = self.add_figure_lambda()
        self.add_submit_lambda()
        self.add_search_lambda()

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

    def generate_usergroup(self,affiliatedict):
        affiliatename = affiliatedict["AffiliateName"]
        policy = Policy(PolicyDocument=self.customize_userpolicy(affiliatedict),PolicyName = affiliatename+'policy')
        usergroup = Group("UserGroup"+affiliatename,GroupName = affiliatename+"group",Policies=[policy])
        usergroup_attached = self.template.add_resource(usergroup)
        return usergroup_attached

    def attach_users(self,affiliatedict):
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
                affiliate_users.append(self.iam_resource.User(user_local))
                affiliate_usernames.append(user_local)
            except Exception as e: 
                print("Error adding User {}, please evaluate".format(user),e)

        return affiliate_users,affiliate_usernames
        

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
                CodeUri = self.config['Lambda']["CodeUri"],##'../lambda_repo',
                Runtime = 'python3.6',
                Handler = self.config['Lambda']["Handler"],##'submit_start.handler',
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
                CodeUri = '../../protocols', ## assume we are running from the stack config template location.
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
    
    ## Add in a lambda function to do hyperparameter search and return output to the user.  
    def add_search_lambda(self):
        ## We will make event triggers for all affiliates. 
        all_affiliates = self.config["UXData"]["Affiliates"]
        ## Make Rule sets for each affiliate: 
        all_events = {}
        for affiliate in all_affiliates: 
            ## Get necessary properties: 
            affiliatename = affiliate["AffiliateName"]
            ## If user input, reads directly from input directory. If other function output, reads from output directory.
            readdir = self.config['Lambda']['LambdaConfig']['OUTDIR'] 

            aff_filter = Filter('Filter'+affiliatename,
                    S3Key = S3Key('S3Key'+affiliatename,
                        Rules= [Rules('PrefixRule'+affiliatename,Name = 'prefix',Value = affiliatename+'/'+readdir),
                                Rules('SuffixRule'+affiliatename,Name = 'suffix',Value = 'opt_data.csv')])) 
            event_name = 'BucketEvent'+affiliatename+"AnalysisEnd"
            all_events[event_name] = {'Type':'S3',
                                      'Properties':{
                                          'Bucket':Ref('PipelineMainBucket'),
                                          'Events':['s3:ObjectCreated:*'],
                                          'Filter':aff_filter}}
        ## We're going to add in all of the lambda configuration items to the runtime environment.
        lambdaconfig = self.config['Lambda']['LambdaConfig']
        ### Most of the config can be done through the config file, but we will pass certain elements from the template. 
        #lambdaconfig['figlambid'] = Ref(self.figurelamb) 
        #lambdaconfig['figlambarn'] = GetAtt(self.figurelamb,'Arn')
        #lambdaconfig['cwrolearn'] = GetAtt(self.cwrole,'Arn')
        ## Now add to a lambda function: 
        function = Function('SearchLambda',
                CodeUri = self.config['Lambda']["PostCodeUri"],##'../lambda_repo',
                Runtime = 'python3.6',
                Handler = self.config['Lambda']["PostHandler"],##'submit_start.handler',
                Description = 'Postprocessing Lambda Function for Serverless',
                MemorySize = 128,
                Timeout = self.config["Lambda"]['LambdaConfig']["EXECUTION_TIMEOUT"],
                Role = 'arn:aws:iam::739988523141:role/lambda_dataflow', ## TODO: Create this in template
                Events= all_events,
                #Environment = Environment(Variables={'figlambid':Ref(self.figurelamb),'figlambarn':GetAtt(self.figurelamb,'Arn'),'cwrolearn':GetAtt(self.cwrole,'Arn')})
                Environment = Environment(Variables=lambdaconfig)
                )         
        self.template.add_resource(function)

if __name__ == "__main__":
    filename = sys.argv[1]
    dirname = os.path.dirname(filename)
    ## Create any new users that have not yet been declared. 
    ## utemp = UserTemplate(filename)
    ## with open(dirname+"/"+"compiled_users.json","w") as f: 
        #print(utemp.template.to_json(),file = f)

    ## Construct the pipeline. 
    temp =PipelineTemplate(filename)
    with open(dirname+'/'+'compiled_template.json','w') as f:
        print(temp.template.to_json(),file = f)

    ## 

