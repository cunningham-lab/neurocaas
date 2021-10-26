## Basic tests to see that the outputs of a logging run can correctly pass. 
import localstack_client.session as session
import subprocess
import json
from botocore.exceptions import ClientError
import ncap_iac.protocols.utilsparam.env_vars_log
import ncap_iac.utils.environment_check as env_check
from ncap_iac.protocols import log 
from ncap_iac.protocols.utilsparam import s3,ssm,ec2,events,pricing
import pytest
from test_submit_start import setup_lambda_env,get_paths,user_name
import os

here = os.path.abspath(os.path.dirname(__file__)) 
test_log_mats = os.path.join(here,"test_mats","logfolder")
bucket_name = "cianalysispermastack"
key_name = "test_user/submissions/submit.json"
fakedatakey_name = "test_user/submissions/fakedatasubmit.json"
fakeconfigkey_name = "test_user/submissions/fakeconfigsubmit.json"
notimestampkey_name = "test_user/submissions/notimestampconfigsubmit.json" 
nodatakey_name = "test_user/submissions/notimestampconfigsubmit.json" 
noconfigkey_name = "test_user/submissions/notimestampconfigsubmit.json" 
## set up mock client and resources. 
s3_client = session.client("s3")
s3_resource = session.resource("s3")
## The lambda function logic we use is monitor_updater:q

@pytest.fixture()
def mock_resources(monkeypatch):
    ## mock s3 resources:
    monkeypatch.setattr(s3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(s3, "s3_resource", session.resource("s3"))
    ## mock ssm resources:
    monkeypatch.setattr(ssm,"ssm_client",session.client("ssm"))
    ## mock ec2 resources:
    monkeypatch.setattr(ec2,"ec2_resource",session.resource("ec2"))
    monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
    ## mock events:
    monkeypatch.setattr(events,"events",session.client("events"))
    ## mock pricing
    #monkeypatch.setattr(pricing,"client",session.client("pricing"))
    monkeypatch.setattr(pricing,"ec2client",session.client("ec2"))
    
@pytest.fixture
def setup_testing_bucket(monkeypatch):
    """Sets up a localstack bucket called cianalysispermastack with the following directory structure:
    /
    |-test_user
      |-inputs
        |-data.json
      |-configs
        |-config.json
      |-submissions
        |-submit.json
    |-logs
      |-active
        |-i-1234567890abcdef0.json
        |-i-superexpensive.json
      |-test_user
        |-joblog1
        |-joblog2
        ...

    """
    subkeys = {
            "inputs/data1.json":{"data":"value"},
            "inputs/data2.json":{"data":"value"},
            "configs/config.json":{"param":"p1"},
            "configs/fullconfig.json":{"param":"p1","__duration__":360,"__dataset_size__":20,"ensemble_size":5},
            "submissions/singlesubmit.json":{
                "dataname":os.path.join(user_name,"inputs","data1.json"),
                "configname":os.path.join(user_name,"configs","config.json"),
                "timestamp":"testtimestamp"},
            "submissions/submit.json":{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "configname":os.path.join(user_name,"configs","config.json"),
                "timestamp":"testtimestamp"},
            "submissions/{}".format(os.path.basename(fakedatakey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data21.json","data22.json"]],
                "configname":os.path.join(user_name,"configs","config.json"),
                "timestamp":"testtimestamp"},
            "submissions/{}".format(os.path.basename(fakeconfigkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "configname":os.path.join(user_name,"configs","config22.json"),
                "timestamp":"testtimestamp"},
            "submissions/{}".format(os.path.basename(nodatakey_name)):{
                "configname":os.path.join(user_name,"configs","config22.json"),
                "timestamp":"testtimestamp"},
            "submissions/{}".format(os.path.basename(noconfigkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "timestamp":"testtimestamp"},
            "submissions/{}".format(os.path.basename(notimestampkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "configname":os.path.join(user_name,"configs","config22.json")}
            }

    s3_client = session.client("s3")
    s3_resource = session.resource("s3")
    monkeypatch.setattr(s3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(s3, "s3_resource", session.resource("s3"))
    try:
        for sk in subkeys:
            obj = s3_client.get_object(Bucket = bucket_name,Key = os.path.join(user_name,sk))
        s3_client.get_object(Bucket = bucket_name,Key="logs/test_user/i-0ff308d5c9b5786f3.json")    
    except ClientError:    
        ## Write data files
        s3_client.create_bucket(Bucket = bucket_name)
        for sk in subkeys:
            key = os.path.join(user_name,sk)
            writeobj = s3_resource.Object(bucket_name,key)
            content = bytes(json.dumps(subkeys[sk]).encode("UTF-8"))
            writeobj.put(Body = content)
    ## Write logs    
    log_paths = get_paths(test_log_mats) 
    try:
        for f in log_paths:
            s3_client.upload_file(os.path.join(test_log_mats,f),bucket_name,Key = f)
    except ClientError as e:        
        logging.error(e)
        raise
    yield bucket_name,os.path.join(user_name,"submissions/submit.json")        

def test_monitor_updater_begin(mock_resources,setup_testing_bucket,setup_lambda_env,tmp_path):
    ## client for file transfer to check 
    with open(os.path.join(here,"test_mats","simevents","cloudwatch_startevent.json"),"r") as f:
        event = json.load(f)
    exitcode = log.monitor_updater(event,{})
    assert exitcode == 0
    ## now also get the file from remote and check its properties: 
    retrieved = os.path.join(tmp_path,"retrieved_log")
    s3_client.download_file(bucket_name,"logs/active/i-1234567890abcdef0.json",retrieved)
    with open(retrieved,"r") as f:
        retrieved_file = json.load(f)
    assert retrieved_file["start"] is not None   

def test_monitor_updater_end(mock_resources,setup_testing_bucket,setup_lambda_env,tmp_path):
    with open(os.path.join(here,"test_mats","simevents","cloudwatch_termevent.json"),"r") as f:
        event = json.load(f)
    ## Get the corresponding log: 
    with open(os.path.join(here,"test_mats","logfolder","logs","active","i-1234567890abcdef0.json"),"r") as f:
        logfile = json.load(f)
    instanceid = logfile["instance-id"]
    jobpath = logfile["jobpath"]
    jobname = os.path.basename(jobpath)
    ## First create a monitoring rule 
    class instance():
        def __init__(self,instanceid):
            self.instance_id = instanceid

    response,name = events.put_instances_rule([instance(instanceid)],jobname)
    targetdata = events.put_instance_target(name)
    print(response,name,"resp and name")

    ## update the log as you would do after a "running" statechange    
    exitcode = log.monitor_updater(event,{})
    assert exitcode == 0
    ## now also get the file from remote and check its properties: 
    retrieved = os.path.join(tmp_path,"retrieved_log")
    s3_client.download_file(bucket_name,"logs/{}/i-1234567890abcdef0.json".format(user_name),retrieved)
    with open(retrieved,"r") as f:
        retrieved_file = json.load(f)
    assert retrieved_file["start"] is None   
    assert retrieved_file["end"] is not None   


