import boto3 
import json
import os


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
    response = events.put_targets(
            Rule = rulename,
            Targets = [
                {
                    'Arn':os.environ['figlambarn'],
                    'Id':os.environ['figlambid']}])
    return response

