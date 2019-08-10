from troposphere import Ref,GetAtt,Template,Output
from troposphere.s3 import Bucket
from troposphere.iam import User,Group,Policy,LoginProfile,AccessKey,UserToGroupAddition,Role
from troposphere.serverless import Function
from troposphere.cloudformation import CustomResource
from lambda_policies import lambda_basepolicy, lambda_writeS3
import sys
import json
import secrets

## There are certain things we know that our template will need for sure. 
def initialize_template():
    template = Template()
    ## Apply a transform to use serverless functions. 
    template.set_transform("AWS::Serverless-2016-10-31")
    ## Initialize the resources necessary to make directories. 
    
    with open('policies/lambda_role_assume_role_doc.json',"r") as f:
        assume_role_doc = json.load(f)
     
    ## Base lambda policy
    base_policy = lambda_basepolicy("LambdaBaseRole")
    ## Write permissions for lambda to s3 
    write_policy = lambda_writeS3('LambdaWriteS3Policy')
    ## 
    template.add_resource(base_policy)
    role = Role("S3MakePathRole",
            AssumeRolePolicyDocument=assume_role_doc,
            ManagedPolicyArns=[Ref(base_policy)],
            Policies = [write_policy])
    template.add_resource(role)

    ## Now we need to write a lambda function that actually does the work:  
    function = Function("S3PutObjectFunction",
                        CodeUri="../lambda_repo",
                        Description= "Puts Objects in S3",
                        Handler="helper.handler_mkdir",
                        Role=GetAtt(role,"Arn"),
                        Runtime="python3.6",
                        Timeout=30)
    template.add_resource(function)
    return template





class UXTemplate(object):
    '''
    A class that handles all user experience aspects of the cloudformation stack creation. This includes creation of the affiliate's bucket, the pipeline folder within that bucket, an iam group for the affiliate, and iam users for each member of the affiliate's organization.  
    '''
    ## If there is no default template, the init method makes one and adds a bucket and iam group. 
    def __init__(self,affiliatename,defaulttemplate = False):
        if defaulttemplate == False: 
            self.template = Template()
            ## Update the template to accept serverless functions. 
            self.template.set_transform('AWS::Serverless-2016-10-31')
            self.affiliatename = affiliatename
            ## TODO: Check that the affiliate name is all lowercase 
            ## Declare the logical name for the bucket resource. 
            self.bucket_logname = 'UserBucket'+affiliatename
            bucket = Bucket(self.bucket_logname,AccessControl = 'Private',BucketName =affiliatename)
            self.bucket = self.template.add_resource(bucket)
            ## Now define a new user policy: 
            policy = Policy(PolicyDocument =self.customize_userpolicy(),PolicyName = self.affiliatename+'policy')
            ## Now define an iam user group to which we can attach this policy: 
            self.group_logname = 'UserGroup'+affiliatename
            self.groupname = self.affiliatename+'group'
            usergroup = Group(self.group_logname,GroupName = self.groupname,Policies=[policy])
            self.usergroup = self.template.add_resource(usergroup)
            self.users = []
            self.usercount = 0
        else:
            'Implement me! and remember to implement getting of resources as attributes!' 
            
    ## A method that customizes the json policy (see attached) to the particular affiliation name. 
    def customize_userpolicy(self):
        ## First get the template policy 
        with open('policies/iam_user_base_policy_doc.json','r') as f:
            obj = json.load(f)
        obj["Statement"].append({
            'Sid': 'VisualEditor2',
            'Effect': 'Allow',
            'Action': 's3:*',
            'Resource': ['arn:aws:s3:::'+self.affiliatename+'/*','arn:aws:s3:::'+self.affiliatename]})
        with open('policies/'+self.affiliatename+'_policy.json','w') as fw: 
            json.dump(obj,fw,indent = 2)
        return obj

## Define a function that, given a group name and a user name, returns an iam user and puts credentials in the output.  

    def generate_user_with_creds(self,username,password = True,accesskey = True):
        ## Generate a random password as 8-byte hexadecimal string
        data = {}

        assert password == True or accesskey == True; 'Must have some credentials'
        
        ## Now we declare a user, as we need to reference a user to generate access keys. 
        user = User(self.affiliatename+'user'+str(username))

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
        
            self.template.add_output(Output('Password'+str(self.usercount),Value = default_password,Description = 'Default password of new user '+username))
            user_t.LoginProfile = lp


        ## Now we generate access keys:  
        if accesskey == True:
            key = AccessKey('userkey'+str(self.usercount),UserName = Ref(user))
            self.template.add_resource(key)
            accesskey = Ref(key)
            secretkey = GetAtt(key,'SecretAccessKey')

            self.template.add_output(Output('AccessKey'+str(self.usercount),Value = accesskey,Description = 'Access Key of user: '+username))
            self.template.add_output(Output('SecretAccessKey'+str(self.usercount),Value = secretkey,Description = 'Secret Key of new user: '+username))
        self.users.append(user_t)
        self.usercount+=1

    def add_users_to_group(self,users = False):
        ## Assumes you just declared a bunch of users with credentials (saved in self.users, to be added. otherwise, users given as argument will be added.  )
        
        if users is False:
            users_t = self.template.add_resource(UserToGroupAddition('Users',GroupName = Ref(self.usergroup),Users=[Ref(u) for u in self.users]))

    def make_folder_custom_resource(self,bucketname,pathname,dirname):
        ## 1. Make a role for the lambda function to take on. 
        ## First handle policies: 
        ## Assume role policy doc: 
        with open('policies/lambda_role_assume_role_doc.json',"r") as f:
            assume_role_doc = json.load(f)
         
        ## Base lambda policy
        base_policy = lambda_basepolicy("LambdaBaseRole")
        ## Write permissions for lambda to s3 
        write_policy = lambda_writeS3('LambdaWriteS3Policy')
        ## 
        self.template.add_resource(base_policy)
        role = Role("S3MakePathRole",
                AssumeRolePolicyDocument=assume_role_doc,
                ManagedPolicyArns=[Ref(base_policy)],
                Policies = [write_policy])
        self.template.add_resource(role)

        ## Now we need to write a lambda function that actually does the work:  
        function = Function("S3PutObjectFunction",
                            CodeUri="../lambda_repo",
                            Description= "Puts Objects in S3",
                            Handler="helper.handler_mkdir",
                            Role=GetAtt(role,"Arn"),
                            Runtime="python3.6",
                            Timeout=30)
        self.template.add_resource(function)

        ## Finally, we declare a custom resource that makes use of this lambda function. 
        foldermake = CustomResource('S3PutObject',
                                    ServiceToken=GetAtt(function,"Arn"),
                                    BucketName = self.affiliatename,
                                    Path = pathname,
                                    DirName = dirname)
        self.template.add_resource(foldermake)

if __name__ == "__main__":
    groupname = sys.argv[1]
    pathname = sys.argv[2]
    dirname = sys.argv[3]
    usernames = list(map(str, sys.argv[4].strip('[]').split(',')))
    ## Initialize with bucket and iam user group 
    utemp = UXTemplate(groupname)
    [utemp.generate_user_with_creds(username) for username in usernames]
    utemp.add_users_to_group()
    utemp.make_folder_custom_resource(groupname,pathname,dirname)
    #make_folder_custom_resource(utemp,groupname)

    #utemp.customize_userpolicy()

    #temp = Template() 
    #temp_updated = generate_user_with_creds(temp,groupname,username)
    print(utemp.template.to_json())



    


