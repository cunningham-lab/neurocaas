import os 
import json 
import boto3 
import pathlib
import time
from botocore.exceptions import ClientError


## Get global parameters:
utildir = pathlib.Path(__file__).parent.absolute()
basedir = os.path.dirname(os.path.dirname(os.path.dirname(utildir)))
with open(os.path.join(basedir,"global_params.json")) as gp:
    gpdict = json.load(gp)

def test_standard_case():
    s3_client = boto3.client("s3")
    s3_resource = boto3.resource("s3")
    ec2_client = boto3.client("ec2")
    waiter = ec2_client.get_waiter("instance_terminated")
    #from ..test_resources.set_remote import *

    test_path = "../test_resources"

    ## go get parameters that tell us where to upload: 
    with open(os.path.join(test_path,"test_params.json"),"r") as params:
        paramdict = json.load(params)
        groupname = paramdict["groupname"]
        bucketname = paramdict["bucketname"]

    ## Now indicate what file you will be uploading:
    dataname = "dataset1.txt"
    configname = "config_duration_size.json"
    logname = "i-1costlow.json"

    datafilepath = os.path.join(test_path,dataname)
    configfilepath = os.path.join(test_path,configname)
    logfilepath = os.path.join(test_path,logname)

    ## first upload data: 
    datauploadpath = os.path.join(groupname,"inputs",dataname) ## Technically this is the "INDIR" param specified in utils/dev_builder, we can't get that easily right now.  
    try:
        s3_client.upload_file(datafilepath,bucketname,datauploadpath)
    except ClientError as e: 
        print(e)

    ## then upload config file 
    configuploadpath = os.path.join(groupname,"configs",configname) ## Technically this is the "CONFIGDIR" param, see "INDIR"
    try:
        s3_client.upload_file(configfilepath,bucketname,configuploadpath)
    except ClientError as e: 
        print(e)

    ## finally upload appropriate log files
    loguploadpath = os.path.join("logs",groupname,logname)
    try:
        s3_client.upload_file(logfilepath,bucketname,loguploadpath)
    except ClientError as e: 
        print(e)

    ## now create a submit file that references the right data and config file. 
    ## we need a dictionary with the following fields:
    submit = {}
    submit["dataname"] = datauploadpath
    submit["configname"] = configuploadpath
    submit["timestamp"] = "11:04:112"
    ## then submit it. 
    dataobj = s3_resource.Object(bucketname,os.path.join(groupname,"submissions","test11underdurationsubmit.json"))
    dataobj.put(Body = (bytes(json.dumps(submit).encode("UTF-8"))))

    ## Now we wait for the test session to complete. We can get a rough idea of when this will be based on the duration parameter in the config. [the ami we have for the instance ]
    with open(configfilepath,"r") as cf:
        cfdict = json.load(cf)
        waittime = int(cfdict["wait"])

    time.sleep(waittime+200)

    ## check that the appropriate results folder exists. 
    resultlogpath = os.path.join(groupname,"results","job__epi-ncap-stable_{}".format(submit["timestamp"]),"logs")
    try:
        out = s3_client.list_objects_v2(Bucket=bucketname,Prefix = resultlogpath)
        contents = out["Contents"]
        keys = [zi["Key"] for zi in contents]
        ## First check for existence of logs
        dataset_status = os.path.join(resultlogpath,"DATASET_NAME:dataset1.txt_STATUS.txt")
        result_status = os.path.join(resultlogpath,"certificate.txt")
        assert dataset_status in keys
        assert result_status in keys
        
        ## Read in the Dataset status: 
        file_object = s3_resource.Object(bucketname,dataset_status)
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        dsdict = json.loads(raw_content)
        assert dsdict["status"] in ["SUCCESS","INITIALIZING"]
        instanceid = dsdict["instance"]
        waiter.wait(InstanceIds=[instanceid])
        ## Now go get the corresponding log file:
        print(os.path.join("logs",groupname,"{}.json".format(instanceid)))
        log_object = s3_resource.Object(bucketname,os.path.join("logs",groupname,"{}.json".format(instanceid)))
        log_content = log_object.get()['Body'].read().decode('utf-8')
        logdict = json.loads(log_content)
        print(logdict)
        assert logdict["start"] is not None
        assert logdict["end"] is not None

    except ClientError as e: 
        print(e)
        assert 0



    



    
