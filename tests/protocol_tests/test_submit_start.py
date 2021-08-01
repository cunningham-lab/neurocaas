## Import and test the lambda business logic in a local environment. Not ideal, but important
import localstack_client.session
import subprocess
import json
from botocore.exceptions import ClientError
import ncap_iac.protocols.utilsparam.env_vars
import ncap_iac.utils.environment_check as env_check
from ncap_iac.protocols import submit_start, submit_start_legacy_wfield_preprocess
from ncap_iac.protocols.utilsparam import s3
from ncap_iac.protocols.utilsparam import ec2,ssm 
import pytest
import os

ec2_resource = localstack_client.session.resource("ec2")
ec2_client = localstack_client.session.client("ec2")

loc = os.path.dirname(os.path.realpath(__file__))
test_log_mats = os.path.join(loc,"test_mats","logfolder")
blueprint_path = os.path.join(loc,"test_mats","stack_config_template.json")
with open(os.path.join(loc,"../../ncap_iac/global_params_initialized.json")) as f:
    gpdict = json.load(f)
bucket_name = "test-submitlambda-analysis"
bucket_name_legacy = "test-submitlambda-analysis-legacy"
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
    """Our lambda functions require a certain number of environment variables to be set in order to function properly. 

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
    """Sets up a localstack bucket called test-submitlambda-analysis with the following directory structure:
    /
    |-test_user
      |-inputs
        |-data.json
      |-configs
        |-config.json
      |-submissions
        |-submit.json
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
    
@pytest.fixture
def setup_testing_bucket_legacy(monkeypatch):
    """Sets up a localstack bucket called test-submitlambda-analysis with the following directory structure (needed for legacy application):
    /
    |-test_user
      |-inputs
        |-data.json
      |-configs
        |-config.json
      |-submissions
        |-submissions2
          |-submit.json
    |-logs
      |-test_user
        |-joblog1
        |-joblog2
        ...

    """
    subkeys = {
            "inputs/data1.zip":{"data":"value"}, ## Takes only zip files.
            "inputs/data2.zip":{"data":"value"},
            "configs/config.json":{"param":"p1"},
            "submissions/submissions2/submit.json":{
                "dataname":os.path.join(user_name,"inputs"), ## big difference: takes everything in the folder.
                "configname":os.path.join(user_name,"configs","config.json"),
                "instance_type":"t2.micro",
                "timestamp":"testtimestamp"},
            "submissions/submissions2/{}".format(os.path.basename(fakedatakey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data21.json","data22.json"]],
                "configname":os.path.join(user_name,"configs","config.json"),
                "instance_type":"t2.micro",
                "timestamp":"testtimestamp"},
            "submissions/submissions2/{}".format(os.path.basename(fakeconfigkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "configname":os.path.join(user_name,"configs","config22.json"),
                "instance_type":"t2.micro",
                "timestamp":"testtimestamp"},
            "submissions/submissions2/{}".format(os.path.basename(nodatakey_name)):{
                "configname":os.path.join(user_name,"configs","config22.json"),
                "instance_type":"t2.micro",
                "timestamp":"testtimestamp"},
            "submissions/submissions2/{}".format(os.path.basename(noconfigkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "instance_type":"t2.micro",
                "timestamp":"testtimestamp"},
            "submissions/submissions2/{}".format(os.path.basename(notimestampkey_name)):{
                "dataname":[os.path.join(user_name,"inputs",d) for d in ["data1.json","data2.json"]],
                "instance_type":"t2.micro",
                "configname":os.path.join(user_name,"configs","config22.json")}
            }

    session = localstack_client.session.Session()
    s3_client = session.client("s3")
    s3_resource = session.resource("s3")
    monkeypatch.setattr(s3, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(s3, "s3_resource", session.resource("s3"))
    try:
        for sk in subkeys:
            obj = s3_client.get_object(Bucket = bucket_name_legacy,Key = os.path.join(user_name,sk))
        s3_client.get_object(Bucket = bucket_name_legacy,Key="logs/test_user/i-0ff308d5c9b5786f3.json")    
    except ClientError:    
        ## Write data files
        s3_client.create_bucket(Bucket = bucket_name_legacy)
        for sk in subkeys:
            key = os.path.join(user_name,sk)
            writeobj = s3_resource.Object(bucket_name_legacy,key)
            content = bytes(json.dumps(subkeys[sk]).encode("UTF-8"))
            writeobj.put(Body = content)
        ## Write logs    
        log_paths = get_paths(test_log_mats) 
        try:
            for f in log_paths:
                s3_client.upload_file(os.path.join(test_log_mats,f),bucket_name_legacy,Key = f)
        except ClientError as e:        
            logging.error(e)
            raise
    yield bucket_name_legacy,os.path.join(user_name,"submissions/submissions2/submit.json")        

@pytest.fixture
def check_instances():
    """Check if unattended instances have been left running."""
    yield "checking for uncleaned instances"
    session = localstack_client.session.Session()
    ec2_resource = session.resource("ec2")
    instances = ec2_resource.instances.filter(Filters = [{"Name":"instance-state-name","Values":["running"]}]) 
    for instance in instances:
        pytest.fail("Uncleaned instances!")

@pytest.fixture
def set_ssm_budget_under(monkeypatch):
    """Use SSM to set budget lower than the tolerable value.

    """
    session = localstack_client.session.Session()
    ssm_client = session.client("ssm")
    monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) ## TODO I don't think these are scoped correctly w/o a context manager.
    ssm_client.put_parameter(Name = ssm.budgetname.format(g =user_name,a=bucket_name),
            Overwrite = False,
            Value = "0",
            Type = "String")
    yield
    ssm_client.delete_parameter(Name = ssm.budgetname.format(g=user_name,a = bucket_name))

@pytest.fixture
def set_ssm_budget_over(monkeypatch):    
    """Use SSM to set budget higher than the tolerable value.

    """
    session = localstack_client.session.Session()
    ssm_client = session.client("ssm")
    monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) ## TODO I don't think these are scoped correctly w/o a context manager.
    ssm_client.put_parameter(Name = ssm.budgetname.format(g=user_name,a=bucket_name),
            Overwrite = False,
            Value = "1300",
            Type = "String")
    yield
    ssm_client.delete_parameter(Name = ssm.budgetname.format(g=user_name,a=bucket_name))

@pytest.fixture
def set_ssm_budget_other(monkeypatch):    
    """Use SSM to set budget higher than the tolerable value.

    """
    session = localstack_client.session.Session()
    ssm_client = session.client("ssm")
    monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) ## TODO I don't think these are scoped correctly w/o a context manager.
    ssm_client.put_parameter(Name = "random",
            Overwrite = False,
            Value = "1300",
            Type = "String")
    yield
    ssm_client.delete_parameter(Name = "random")

class Test_Submission_dev():
    def test_Submission_dev(self,setup_lambda_env,setup_testing_bucket,check_instances):
        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,submit_path,"111111111")
    
    def test_Submission_dev_nobucket(self,setup_lambda_env,setup_testing_bucket,check_instances):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(FileNotFoundError):
            sd = submit_start.Submission_dev("fakebucket",submit_path,"111111111")

    def test_Submission_dev_nofile(self,setup_lambda_env,setup_testing_bucket,check_instances):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(FileNotFoundError):
            sd = submit_start.Submission_dev(bucket_name,os.path.join(os.path.dirname(submit_path),"fakefilesubmit.json"),"111111111")

    def test_Submission_dev_file_misconfig(self,setup_lambda_env,setup_testing_bucket,check_instances):
        """If unable to find a group name:"""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(FileNotFoundError):
            sd = submit_start.Submission_dev(bucket_name,"fakefilesubmit.json","111111111")

    def test_Submission_dev_no_datakey(self,setup_lambda_env,setup_testing_bucket,check_instances):
        """If unable to find a group name:"""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(ValueError):
            sd = submit_start.Submission_dev(bucket_name,nodatakey_name,"111111111")

    def test_Submission_dev_no_configkey(self,setup_lambda_env,setup_testing_bucket,check_instances):
        """If unable to find a group name:"""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(ValueError):
            sd = submit_start.Submission_dev(bucket_name,noconfigkey_name,"111111111")

    def test_Submission_dev_no_timestamp(self,setup_lambda_env,setup_testing_bucket,check_instances):
        """If no timestamp provided:"""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        with pytest.raises(ValueError):
            sd = submit_start.Submission_dev(bucket_name,notimestampkey_name,"111111111")


### Testing check_existence. 
    @pytest.mark.parametrize("submitname,path",[("submit.json",[os.path.join("test_user/inputs/",d) for d in ["data1.json","data2.json"]]),("singlesubmit.json",[os.path.join("test_user/inputs/","data1.json")])])
    def test_Submission_dev_check_existence(self,setup_lambda_env,setup_testing_bucket,check_instances,submitname,path):        
        """check existence of data in s3."""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_path = os.path.join(user_name,"submissions",submitname)
        sd = submit_start.Submission_dev(bucket_name,submit_path,"111111111")
        sd.check_existence()
        assert sd.filenames == path 

    @pytest.mark.parametrize("dataname,error",[(1,TypeError),("fake",ValueError),(["fake","fake"],ValueError)])
    def test_Submission_dev_check_existence_wrongdata(self,setup_lambda_env,setup_testing_bucket,check_instances,dataname,error):        
        """check existence of data in s3."""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,submit_path,"111111111")
        sd.data_name = dataname
        with pytest.raises(error):
            sd.check_existence()

    def test_Submission_dev_check_existence_wrongconfig(self,setup_lambda_env,setup_testing_bucket,check_instances):        
        """check existence of data in s3."""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,submit_path,"111111111")
        sd.config_name = "trash.yaml"
        with pytest.raises(ValueError):
            sd.check_existence()

### Testing function get_costmonitoring
    def test_Submission_dev_get_costmonitoring(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch):
        session = localstack_client.session.Session()
        ssm_client = session.client("ssm")
        monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        assert sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch):
        session = localstack_client.session.Session()
        ssm_client = session.client("ssm")
        monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_under):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_over):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        assert sd.get_costmonitoring()
    
    def test_Submission_dev_get_costmonitoring_ssm_default_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_other):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm_default(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_other):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        assert sd.get_costmonitoring()

    def test_Submission_dev_parse_config(self,setup_lambda_env,setup_testing_bucket):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        sd.parse_config()
        assert sd.jobduration is None
        assert sd.jobsize is None

    def test_Submission_dev_parse_config_full(self,setup_lambda_env,setup_testing_bucket):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        sd.config_name = os.path.join(user_name,"configs","fullconfig.json")
        sd.parse_config()
        assert sd.jobduration == 360
        assert sd.jobsize == 20


class Test_Submission_ensemble():
    def test_Submission_ensemble(self,setup_lambda_env,setup_testing_bucket):
        """check existence of data in s3."""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_ensemble(bucket_name,submit_path,"111111111")

    @pytest.mark.parametrize("submitname,path",[("submit.json",None),("singlesubmit.json",[os.path.join("test_user/inputs/","data1.json")])])
    def test_Submission_ensemble_check_existence(self,setup_lambda_env,setup_testing_bucket,check_instances,submitname,path):        
        """check existence of data in s3."""
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_path = os.path.join(user_name,"submissions",submitname)
        sd = submit_start.Submission_ensemble(bucket_name,submit_path,"111111111")
        if path is not None:
            sd.check_existence()
            assert sd.filenames == path 
        else:    
            with pytest.raises(AssertionError):
                sd.check_existence()

    def test_Submission_ensemble_parse_config(self,setup_lambda_env,setup_testing_bucket):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_path = os.path.join(user_name,"submissions","singlesubmit.json")
        sd = submit_start.Submission_ensemble(bucket_name,submit_path,"111111111")
        sd.config_name = os.path.join(user_name,"configs","fullconfig.json")
        sd.check_existence()
        sd.parse_config()
        assert sd.jobduration == 360
        assert sd.jobsize == 20 
        for cfig in sd.ensembleconfigs:
            assert s3.exists(bucket_name,cfig)
            data = s3.load_json(bucket_name,cfig)
            assert "jobnb" in data.keys()
            s3.s3_resource.Object(bucket_name,cfig).delete()
        
    def test_Submission_ensemble_process_inputs(self,monkeypatch,setup_lambda_env,setup_testing_bucket,create_ami,check_instances):
        ami = create_ami
        session = localstack_client.session.Session()
        monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
        monkeypatch.setattr(ec2,"ec2_resource",session.resource("ec2"))
        monkeypatch.setattr(ssm,"ssm_client",session.client("ssm"))
        
        
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_path = os.path.join(user_name,"submissions","singlesubmit.json")
        sd = submit_start.Submission_ensemble(bucket_name,submit_path,"111111111")
        monkeypatch.setenv("AMI",ami)
        sd.config_name = os.path.join(user_name,"configs","fullconfig.json")
        sd.check_existence()
        sd.parse_config()
        sd.compute_volumesize()
        sd.acquire_instances()
        sd.process_inputs()
        for cfig in sd.ensembleconfigs:
            assert s3.exists(bucket_name,cfig)
            data = s3.load_json(bucket_name,cfig)
            assert "jobnb" in data.keys()
            s3.s3_resource.Object(bucket_name,cfig).delete()


@pytest.mark.skipif(env_check.get_context() == "ci",reason= "aws creds not provided to github actions..")
class Test_Submission_Launch_Monitor():
    def test_Submission_Launch_Monitor(self,setup_lambda_env,setup_testing_bucket_legacy,check_instances):
        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket_legacy[0],setup_testing_bucket_legacy[1]
        sd = submit_start_legacy_wfield_preprocess.Submission_Launch_folder(bucket_name,submit_path)

    def test_Submission_Launch_Monitor_get_costmonitoring(self,setup_lambda_env,setup_testing_bucket_legacy,check_instances,monkeypatch):
        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket_legacy[0],setup_testing_bucket_legacy[1]
        sd = submit_start_legacy_wfield_preprocess.Submission_Launch_folder(bucket_name,submit_path)
        monkeypatch.setenv("MAXCOST",str(1301))
        assert sd.get_costmonitoring()
    def test_Submission_Launch_Monitor_get_costmonitoring_fail(self,setup_lambda_env,setup_testing_bucket_legacy,check_instances,monkeypatch):
        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket_legacy[0],setup_testing_bucket_legacy[1]
        sd = submit_start_legacy_wfield_preprocess.Submission_Launch_folder(bucket_name,submit_path)
        monkeypatch.setenv("MAXCOST",str(1200))
        assert not sd.get_costmonitoring()
    def test_Submission_Launch_Monitor_log_jobs(self,setup_lambda_env,setup_testing_bucket_legacy,check_instances,monkeypatch):
        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket_legacy[0],setup_testing_bucket_legacy[1]
        sd = submit_start_legacy_wfield_preprocess.Submission_Launch_folder(bucket_name,submit_path)
        sd.acquire_instance()
        sd.log_jobs()

