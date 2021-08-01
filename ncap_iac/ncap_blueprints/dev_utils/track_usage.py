import sys
import boto3
import os
import json
from datetime import datetime
from botocore.exceptions import ClientError

form = "%Y-%m-%dT%H:%M:%SZ" 

### Module with tools to track usage for each individual stack. 
def check_bucket_exists(bucket):
    s3 = boto3.resource('s3')
    if s3.Bucket(bucket).creation_date is None:
        assert 0, "bucket {} does not exist".format(bucket)
    else:
        pass

def get_users(dict_files):
    """
    Presented with a dict of files (response of list_objects_v2), gets usernames from them.
    """

    users = [os.path.basename(li["Key"][:-1]) for li in dict_files["Contents"] if li["Key"].endswith("/")]
    try:
        users.remove("active")
    except ValueError:
        print("bucket not correctly formatted. skipping. ")
        users = []

    try:
        users.remove("logs")
    except ValueError:
        print("bucket not correctly formatted. skipping. ")
        users = []

    return users
    
    

def sort_activity_by_users(dict_files,userlist):
    """
    When given the raw resposne output + list of usernames, returns a dictionary of files organized by that username. 
    """
    activity = [li["Key"] for li in dict_files["Contents"] if li["Key"].endswith(".json")]
    userdict = {name:[] for name in userlist}
    for a in activity:
        user = os.path.basename(os.path.dirname(a))
        try:
            userdict[user].append(a)
        except KeyError as e:
            if user in ['active','debug']:
                pass
            else:
                userdict[user] = []
                userdict[user].append(a)
    return userdict
    

def get_user_logs(bucket_name):
    """
    returns a list of s3 paths corresponding to logged users inside a bucket. 

    :param bucket_name: the name of the s3 bucket we are looking for 
    """

    s3_client = boto3.client("s3") 
    try:

        l = s3_client.list_objects_v2(Bucket=bucket_name,Prefix = "logs")
    except ClientError as e:
        print(e.response["Error"])
    checktruncated = l["IsTruncated"]
    if checktruncated:
        print("WARNING: not listing all results.")
    else:
        print("Listing all results.")

    ## Get Users
    users = get_users(l)
    users_dict = sort_activity_by_users(l,users)
    return users_dict

def get_duration(start,end):
    """
    Get the duration of a job from a pair of strings using datetime. 
    2020-05-17T01:21:05Z
    """
    starttime = datetime.strptime(start,form)
    endtime = datetime.strptime(end,form)
    diff = endtime-starttime
    diff_secs = diff.total_seconds()
    return diff_secs

def get_month(start):
    time = datetime.strptime(start,form)
    return time.month


def calculate_usage(bucket_name,usage_list,user):
    """
    gets the json files containing the usage for a particular user, and returns the total (number of hours, cost, and number of jobs run) per month.   
    :param bucket_name: the name of the bucket where the json file lives. 
    :type bucket_name: str
    """

    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    monthly_cost = {months[i]:0 for i in range(12)}
    monthly_time = {months[i]:0 for i in range(12)}
    usage_compiled = {"username":user,"cost":monthly_cost,"duration":monthly_time}
     
    for job in usage_list:
        usage_dict = load_json(bucket_name,job)
        if None in [usage_dict["start"],usage_dict["end"]]:
            continue
        duration = get_duration(usage_dict["start"],usage_dict["end"])
        month = get_month(usage_dict["start"])
        cost = (usage_dict["price"]/3600)*duration
        usage_compiled["cost"][months[month]] += cost
        usage_compiled["duration"][months[month]] += duration

    return usage_compiled


def load_json(bucket_name, key):
    s3_resource = boto3.resource("s3") 
    """ Function to load the contents of a json file stored in S3 into memory for a lambda function. 

    :param bucket_name: the name of the bucket where the json file lives. 
    :type bucket_name: str
    :param key: the path to the json object. 
    :type key: str
    :raises: ValueError. If the key does not point to a properly formatted json file, an exception will be raised. 
    :return: json content: the content of the json file. 
    :rtype: dict
    """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(raw_content)
    except ValueError as ve:
        raise ValueError("[JOB TERMINATE REASON] Could not load config file. From parser: {}".format(ve))

    ## Transfer type 
    return json_content 


if __name__ == "__main__":
    """
    Pass in space separated names of buckets, get usage by analysis by user as output. 
    """
    bucket_names = sys.argv[1:]
    all_bucket_logs = {} 
    [check_bucket_exists(bucket_name) for bucket_name in bucket_names]
    for bucket_name in bucket_names:
        print("Starting bucket {}".format(bucket_name))
        bucket_logs = {"bucket_name":bucket_name,"users":{}}
        userdict = get_user_logs(bucket_name)
        for user in userdict:
            if len(userdict[user]) > 0:
                usage_compiled = calculate_usage(bucket_name,userdict[user],user)
                bucket_logs["users"][user] = usage_compiled            
            else:
                print("no usage from user {}".format(user))

        all_bucket_logs[bucket_name] =bucket_logs
    with open("neurocaas_activity.json","w") as f:
        json.dump(all_bucket_logs,f,indent = 4)

