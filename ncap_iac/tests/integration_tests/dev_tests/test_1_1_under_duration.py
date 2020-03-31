import os 
import json 
import boto3 

def test_standard_case():
    s3_client = boto3.client("s3")
    s3_resource = boto3.resource("s3")
    #from ..test_resources.set_remote import *

    test_path = "../test_resources"

    ## go get parameters that tell us where to upload: 
    with open(os.path.join(test_path,"test_params.json"),"r") as params:
        paramdict = json.load(params)
        groupname = paramdict["groupname"]
        bucketname = paramdict["bucketname"]

    ## Now indicate what file you will be uploading:
    dataname = "dataset1.txt"
    configname = "config_duration.json"
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
    submit["timestamp"] = "11:04:11"
    ## then submit it. 
    dataobj = s3_resource.Object(bucketname,os.path.join(groupname,"submissions","test11underdurationsubmit.json"))
    dataobj.put(Body = (bytes(json.dumps(submit).encode("UTF-8"))))

    ## Now we wait for the test session to complete. We can get a rough idea of when this will be based on the duration parameter in the config. [the ami we have for the instance ]


    
