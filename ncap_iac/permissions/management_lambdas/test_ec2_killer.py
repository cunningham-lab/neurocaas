import json
import timeoututils
import os
import boto3
import time
from botocore.exceptions import ClientError
from datetime import datetime,timedelta,timezone

## amount of time that instances are ignored before evaluation starts in minutes
graceperiod = os.environ["graceperiod"]
exempt = os.environ["exemptlist"].split(",")
assert os.environ["dryrun"] in ["0","1"]
topicarn = os.environ["topicarn"]

ec2_client = boto3.client("ec2")
cloudwatch_client = boto3.client("cloudwatch")
ssm_client = boto3.client("ssm")
sns_client = boto3.client("sns")

def active_past_graceperiod(instance_info):
    ltime = instance_info["LaunchTime"]
    difference = datetime.now(timezone.utc) - ltime
    difference_minutes = difference.total_seconds()/60
    return difference_minutes > float(graceperiod)
    

def active_past_timeout(instance_info):
    """Determines if the instance has been active longer than a given timeout. 
    If timeout is not given, we compare with the grace period provided by the environment variable. 
    """
    tags = instance_info["Tags"]
    
    if timeout is None:
        timeout = graceperiod
    ltime = instance_info["LaunchTime"]
    difference = datetime.now(timezone.utc) - ltime
    difference_minutes = difference.total_seconds()/60
    return difference_minutes > float(timeout)

def not_exempt(instance_info):
    id = instance_info["InstanceId"]
    not_exempt = id not in exempt
    return not_exempt

def get_active_instances():
    """
    Get active ec2 instances with the specified security group.
    """
    instances = ec2_client.describe_instances(Filters = [{'Name':'instance-state-name',
                                             'Values':["running"]}]
                                             )
    ## Get out just the ids instances as a flat list
    try:
        assert len(instances["Reservations"]) > 0
        instances_flatlist = [inst for res in instances["Reservations"] for inst in res["Instances"]]
    except AssertionError:
        print("no instances active")
        instances_flatlist = []
    
    ## Now check which are active:
    try: 
        instances_notexempt = [i for i in instances_flatlist if not_exempt(i)]
        if len(instances_notexempt) > 80:
            return instances_notexempt
        else:
            instances_active = [i for i in instances_notexempt if active_past_graceperiod(i)]
        assert len(instances_active) > 0
    except AssertionError:
        print("no instances active for longer than {} minutes".format(os.environ["graceperiod"]))
        instances_active = []
        
    return instances_active
    
def get_metricdata_dict(instance_id):
    """
    When supplied with the id of an ec2 instance (assumed active), gets the correctly formatted dictionary 
    to query its activity in 5 minute intervals for the past hour. 
    """
    MetricDataDict = {
        "Id":"testmetricid{}".format(instance_id.split("i-")[-1]),
        "MetricStat":{
            "Period":300,
            "Stat":"Maximum",
            "Metric":{
                    "Namespace": "AWS/EC2",
                    "Dimensions":[
                        {
                            "Name":"InstanceId",
                            "Value":instance_id,
                        }
                        ],
                    "MetricName":"CPUUtilization"
                }
        }
        
    }
    return MetricDataDict

def get_instance_activity(instanceid):
    """
    Provided with an instance id, returns the activity of that instance over the last hour
    """
    end = datetime.now()
    start = end-timedelta(hours = 1)
    data = cloudwatch_client.get_metric_data(MetricDataQueries = [get_metricdata_dict(instanceid)],
                                        StartTime = start,
                                        EndTime = end
        )
    ## less than 5% utilization across the last hour. 
    
    idle = all([entry <5 for entry in data["MetricDataResults"][0]["Values"]])
    return idle
    
def publish_message(message,events = 1):
    print(message)
    if events == 0:
        sns_client.publish(TopicArn = topicarn,Message = message, Subject = "NO INSTANCES STOPPED: Lambda deployment hourly check in")
    else:
        sns_client.publish(TopicArn = topicarn,Message = message, Subject = "INSTANCES STOPPED: Lambda deployment hourly check in")


def lambda_handler(event, context):
    """
    Function to watch for unhandled or idle neurocaas resources. Looks for all resources with a security group indicating deployment by neurocaas, considers those that have been active 
    longer than a specified grace period (os.environ['graceperiod'] minutes). If they have, they are then checked for being idle (activity below 5% consistently for the past hour), or if they have never seen an ssm command.
    If either of those conditions are met, then the instance is stopped and a message is sent to an sns topic. 
    """
    #timeoututils.assert_timeout(context,900)
    ##
    instances_info = get_active_instances()

    if len(instances_info) == 0:
        pass
        message = "no instances active for longer than {} minutes".format(os.environ["graceperiod"])
        #publish_message(message,events = 0)
    else:
        to_stop = [i["InstanceId"] for i in instances_info]
        dryrun = bool(int(os.environ["dryrun"]))
        if len(to_stop) == 0:
       
            message = "All {} instances examined are working as expected.".format(len(ids))
            publish_message(message,events = 0)
     
        else:
            try:
                ec2_client.stop_instances(InstanceIds = to_stop,DryRun=dryrun)
                message= "Stopping instances: {}".format(to_stop)
                publish_message(message)
            except ClientError as e:
                print(e.response)
                if e.response["Error"]["Code"] == "UnsupportedOperation":
                    message = "Instances {} include spot instances, cannot stop. Will terminate.".format(to_stop)
                    publish_message(message)
                    try:
                        ec2_client.terminate_instances(InstanceIds=to_stop,DryRun=dryrun)
                    except ClientError as e:
                        if e.response["Error"]["Code"] == "DryRunOperation":
                            message = "Dry run set, would have terminated: {}".format(to_stop)
                            publish_message(message)      
                        else:
                            raise
                elif e.response["Error"]["Code"] == "DryRunOperation":
                    message = "Dry run set, would have stopped/terminated: {}".format(to_stop)
                    publish_message(message)
                else:
                    raise
                
    return message
