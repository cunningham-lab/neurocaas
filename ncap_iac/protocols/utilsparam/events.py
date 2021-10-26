import boto3 
import json
import os
import ast


## Declare resources and clients: 
events = boto3.client('events')

# 1. Run CreateRole to attach a trust agreement to a role. 
# 2. Run CreatePolicy to create a new managed policy from the policy document. 
# 3. Load in the role to a new object, and Run attach policy to attach the policy we created in step 2. 
# 4. Use the role to generate cloudwatch event calls. 

## Create event rule: 
def put_instance_rule(instance_id):
    event_pattern = {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Instance State-change Notification"],
            "detail":{
                "state":["running","stopped",'shutting-down'],
                "instance-id":[instance_id]}}
    ep_encoded = json.dumps(event_pattern)
    name = "Monitor"+instance_id
    print('environ_param',os.environ)
    response = events.put_rule(
            Name = name,
            EventPattern = ep_encoded,
            State = 'ENABLED',
            Description = 'on-the-fly monitoring setup for instance '+instance_id,
            RoleArn =os.environ['cwrolearn'])
    return response,name

## Create event rule for multiple instances. index by the job id instead. 
def put_instances_rule(instances,jobid):
    """Put a monitoring rule on multiple instances. 

    :param instances: a list of EC2 instance objects with parameter instance.instance_id 
    :param jobid: an id for the job given in terms of its analysis stack name, submission name, and timestamp.
    :returns: (response of events.put_rule,name)

    """
    jobname = jobid.replace(":","_") ## TODO: Kind of messy. 
    event_pattern = {
            "source": ["aws.ec2"],
            "detail-type": ["EC2 Instance State-change Notification"],
            "detail":{
                "state":["running","stopped",'shutting-down'],
                "instance-id":[instance.instance_id for instance in instances]}}
    ep_encoded = json.dumps(event_pattern)
    name = "Monitor"+jobname
    response = events.put_rule(
            Name = name,
            EventPattern = ep_encoded,
            State = 'ENABLED',
            Description = 'on-the-fly monitoring setup for job '+jobid, 
            RoleArn =os.environ['cwrolearn'])
    return response,name


## Create target: 
def put_instance_target(rulename):
    """Takes an existing rule, and sets as its targets the arn and id of the appropriate lambda function. This lambda function info is populated by cloudformation when it creates the lambdas, and provided as environment variables to the submit lambda as it runs. 

    :param rulename: name of the rule that we want to collect outputs for. 

    """
    response = events.put_targets(
            Rule = rulename,
            Targets = [
                {
                    'Arn':os.environ['figlambarn'],
                    'Id':os.environ['figlambid']}])
    return response

## Get the instances monitored by this rule: 
def get_monitored_instances(rulename):
    instances = ast.literal_eval(events.describe_rule(Name=rulename)["EventPattern"])["detail"]["instance-id"]
    return instances

def get_and_remove_target(rulename):
    """
    Returns the target id. 
    """
    targid = events.list_targets_by_rule(Rule=rulename)["Targets"][0]["Id"]
    response = events.remove_targets(Rule=rulename,Ids =[targid])
    return response

def full_delete_rule(rulename):
    """
    Normally, to remove a rule you must first remove all its targets. This function does all steps simultaneously.  
    """
    targresponse = get_and_remove_target(rulename)
    deleteresponse = events.delete_rule(Name= rulename)
    return [targresponse,deleteresponse]



