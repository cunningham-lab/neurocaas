## Import and test the lambda business logic in a local environment. Not ideal, but important
import localstack_client.session
import subprocess
import json
from botocore.exceptions import ClientError
import ncap_iac.protocols.utilsparam.env_vars
import ncap_iac.utils.environment_check as env_check
from ncap_iac.protocols import postprocess 
from ncap_iac.protocols.utilsparam import s3
from ncap_iac.protocols.utilsparam import ec2,ssm 
import pytest
import os

def get_dict_file():
    homedir = os.environ["HOME"]
    if homedir == "/Users/taigaabe":
        scriptflag = "local"
    else:
        scriptflag = "ci"
    return scriptflag
 
if get_dict_file() == "ci":
    pytest.skip("skipping tests that rely upon internal data", allow_module_level=True)

session = localstack_client.session
ec2_resource = session.resource("ec2")
ec2_client = session.client("ec2")
s3_client = session.client("s3")
s3_resource = session.resource("s3")

loc = os.path.dirname(os.path.realpath(__file__))
test_log_mats = os.path.join(loc,"test_mats","logfolder")
test_result_mats = os.path.join(loc,"test_mats","resultsfolder")
blueprint_path = os.path.join(loc,"test_mats","stack_config_template.json")
with open(os.path.join(loc,"../../ncap_iac/global_params_initialized.json")) as f:
    gpdict = json.load(f)
bucket_name = "test-searchlambda-analysis"
key_name = "test_user/submissions/submit.json"
fakedatakey_name = "test_user/submissions/fakedatasubmit.json"
fakeconfigkey_name = "test_user/submissions/fakeconfigsubmit.json"
notimestampkey_name = "test_user/submissions/notimestampconfigsubmit.json" 
nodatakey_name = "test_user/submissions/notimestampconfigsubmit.json" 
noconfigkey_name = "test_user/submissions/notimestampconfigsubmit.json" 
user_name = "test_user"

gpinfo = {
        "INDIR":gpdict["input_directory"],
        "OUTDIR":gpdict["output_directory"],
        "LOGDIR":gpdict["log_directory"],
        "CONFIGDIR":gpdict["config_directory"],
        "SUBMITDIR":gpdict["submission_directory"]
        }

def get_paths(rootpath):
    """Gets paths to all files relative to a given top level path. 

    """
    walkgen = os.walk(rootpath)
    paths = []
    for p,dirs,files in walkgen:
        relpath = os.path.relpath(p,rootpath)
        if len(files) > 0:
            for f in files:
                localfile = os.path.join(relpath,f)
                paths.append(localfile)
    return paths            

@pytest.fixture
def create_ami():
    instance = ec2_resource.create_instances(MaxCount = 1,MinCount=1)[0]
    ami = ec2_client.create_image(InstanceId=instance.instance_id,Name = "dummy")
    yield ami["ImageId"]

@pytest.fixture
def setup_lambda_env(monkeypatch,autouse = True):
    """Unclear if this is needed for this code. 

    """
    with open(blueprint_path,"r") as f:
        blueprint = json.load(f)
    config = blueprint["Lambda"]["LambdaConfig"]    
    for key in gpinfo:
        config[key] = gpinfo[key]
    config['versionid'] = subprocess.check_output(["git","rev-parse","HEAD"]).decode("utf-8") 
    
    for key,value in config.items():
        monkeypatch.setenv(key,str(value))
    yield "env vars set." 

@pytest.fixture
def setup_testing_bucket(monkeypatch):
    """Sets up a localstack bucket called test-searchlambda-analysis with the following directory structure:
    /
    |-test_user
      |-inputs
        |-data.json
      |-configs
        |-config.json
      |-submissions
        |-submit.json
      |-results
        |-job_testsearchlambda-analysis_timestamp1
          |-process_results
            |-1
              |-videos
                |-vid.mp4
            |-2
              |-videos
                |-vid.mp4
          |-logs
            |-DATASTATUS
            |-certificate.txt
    |-logs
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

    session = localstack_client.session.Session()
    monkeypatch.setattr(s3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(s3, "s3_resource", session.resource("s3"))
    monkeypatch.setattr(postprocess, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(postprocess, "s3_resource", session.resource("s3"))

    ## Write data files
    s3_client.create_bucket(Bucket = bucket_name)
    for sk in subkeys:
        key = os.path.join(user_name,sk)
        writeobj = s3_resource.Object(bucket_name,key)
        content = bytes(json.dumps(subkeys[sk]).encode("UTF-8"))
        writeobj.put(Body = content)
    ## Write results    
    result_paths = get_paths(test_result_mats) 
    try:
        for f in result_paths:
            s3_client.upload_file(os.path.join(test_result_mats,f),bucket_name,Key = os.path.join("test_user","results",f))
    except ClientError as e:        
        logging.error(e)
        raise
    ## Write logs    
    log_paths = get_paths(test_log_mats) 
    try:
        for f in log_paths:
            s3_client.upload_file(os.path.join(test_log_mats,f),bucket_name,Key = f)
    except ClientError as e:        
        logging.error(e)
        raise
    yield bucket_name,os.path.join(user_name,"results","job__{b}_timestamp1/process_results/end.txt".format(b=bucket_name)),os.path.join(user_name,"results","job__{b}_timestamp2/process_results/end.txt".format(b=bucket_name))       
    ## clear after processing. 
    s3_resource.Bucket(bucket_name).objects.all().delete()

class Test_PostProcess():
    def test_PostProcess(self,setup_testing_bucket):
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
    def test_get_endfile(self,setup_testing_bucket):
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        raw = pp.get_endfile()
        assert raw == "end of analysis marker\n"
    def test_check_postprocess(self,setup_testing_bucket):    
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        assert not pp_pre.check_postprocess() 
        pp_post = postprocess.PostProcess(bucket_name,endfilepost,bucket_name,"postprocess")
        assert pp_post.check_postprocess() 
    def test_write_postprocess(self,setup_testing_bucket):    
        body =  "correctly postprocessed"
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        pp_pre.write_postprocess(body = body)
        contents = s3_resource.Object(bucket_name,os.path.join(pp_pre.jobdir,"process_results","postprocess")).get()["Body"].read().decode("utf-8")
        assert contents == body
    def test_copy_logs(self,setup_testing_bucket):    
        body =  "correctly postprocessed"
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        pp_pre.copy_logs()
        certobject = s3_resource.Object(bucket_name,os.path.join(pp_pre.jobdir,"logs_pre_postprocess","certificate.txt"))
        certobject.load()
        statuobject = s3_resource.Object(bucket_name,os.path.join(pp_pre.jobdir,"logs_pre_postprocess","DATASET_NAME:raw_data.zip_STATUS.txt"))
        statuobject.load()
    def test_create_submitfile(self,setup_testing_bucket):    
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        datasets = ["test_user/inputs/data1.json","test_user/inputs/data2.json"]
        configs = "test_user/configs/config.json"
        submit = pp_pre.create_submitfile(datasets,configs)
        assert submit["dataname"] == datasets
        assert submit["configname"] == configs
        assert submit["timestamp"] == "timestamp1"
    def test_submit(self,setup_testing_bucket):    
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess(bucket_name,endfilepre,bucket_name,"postprocess")
        datasets = ["test_user/inputs/data1.json","test_user/inputs/data2.json"]
        configs = "test_user/configs/config.json"
        submit = pp_pre.create_submitfile(datasets,configs)
        pp_pre.submit(submit)
        statuobject = s3_resource.Object(bucket_name,os.path.join(pp_pre.groupdir,"submissions","postprocess_submit.json"))
        statuobject.load()
class Test_PostProcess_EnsembleDGPPredict():       
    def test_PostProcess_EnsembleDGPPredict(self,setup_testing_bucket):
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess_EnsembleDGPPredict(bucket_name,endfilepre,bucket_name,"postprocess")
    def test_load_config(self,setup_testing_bucket):
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess_EnsembleDGPPredict(bucket_name,endfilepre,bucket_name,"postprocess")
        config = pp_pre.load_config()
        assert config == {"task": "b29_post_side",
                "scorer": "erica",
                "nb_frames": 16,
                "seed": 4,
                "ensemble_size": 9,
                "videotype": "avi",
                "testing": False,
                "__duration__": 400,
                "jobnb": 1}
    def test_make_config(self,setup_testing_bucket):    
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess_EnsembleDGPPredict(bucket_name,endfilepre,bucket_name,"postprocess")
        newconfig = pp_pre.make_config()
        assert newconfig == {"task": "b29_post_side",
                "scorer": "erica",
                "nb_frames": 16,
                "seed": 4,
                "ensemble_size": 9,
                "videotype": "avi",
                "testing": False,
                "__duration__": 400,
                "mode":"predict",
                "modelpath":"results/job__test-searchlambda-analysis_timestamp1/process_results/",
                "modelnames": ["1","2","3","4","5","6","7","8","9"],
                "jobnb": 1}
    def test_write_config(self,setup_testing_bucket):    
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess_EnsembleDGPPredict(bucket_name,endfilepre,bucket_name,"postprocess")
        newconfig = pp_pre.make_config()
        configpath = pp_pre.write_config(newconfig)
        statuobject = s3_resource.Object(bucket_name,configpath)
        statuobject.load()
    def test_get_videos(self,setup_testing_bucket):
        bucket_name,endfilepre,endfilepost = setup_testing_bucket
        pp_pre = postprocess.PostProcess_EnsembleDGPPredict(bucket_name,endfilepre,bucket_name,"postprocess")
        assert pp_pre.get_videos() == [os.path.join(pp_pre.jobdir,"process_results","1","videos","TempTrial2ROI_0PART_0Interval_[54078, 54107].mp4")]
         

def test_postprocess_prediction_run(setup_testing_bucket):
    bucket_name,endfilepre,endfilepost = setup_testing_bucket
    pp = postprocess.postprocess_prediction_run(bucket_name,endfilepre)
    ## check that everything you looked into still holds true 
    ### submit file: 
    submitobject = s3_resource.Object(bucket_name,os.path.join(pp.groupdir,"submissions","prediction_submit.json"))
    submitcontent = json.loads(submitobject.get()["Body"].read().decode("utf-8"))
    s3_resource.Object(bucket_name,submitcontent["dataname"][0]).load()
    s3_resource.Object(bucket_name,submitcontent["configname"]).load()
    assert submitcontent["timestamp"] == "timestamp1"

