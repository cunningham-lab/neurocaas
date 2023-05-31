## Import and test the lambda business logic in a local environment. Not ideal, but important
import localstack_client.session
import subprocess
import logging
import json
from botocore.exceptions import ClientError
import ncap_iac.protocols.utilsparam.env_vars
import ncap_iac.utils.environment_check as env_check
from ncap_iac.protocols import submit_start, submit_start_legacy_wfield_preprocess
from ncap_iac.protocols.utilsparam import s3,ssm,ec2,events,pricing
import pytest
import re
import os

ec2_resource = localstack_client.session.resource("ec2")
ec2_client = localstack_client.session.client("ec2")

loc = os.path.dirname(os.path.realpath(__file__))
test_log_mats = os.path.join(loc,"test_mats","logfolder")
blueprint_path = os.path.join(loc,"test_mats","stack_config_template.json")
with open(os.path.join(loc,"../../ncap_iac/global_params_initialized.json")) as f:
    gpdict = json.load(f)
bucket_name = "test-submitlambda-analysis"
sep_bucket = "independent"
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

#@pytest.fixture(scope = "module") doesnt seem to work. 
#def start_localstack():
#    infra.start_infra(asynchronous =True)
#    yield "running tests"
#    infra.stop_infra()

@pytest.fixture
def patch_boto3_ec2(monkeypatch):
    ec2_client = localstack_client.session.client("ec2")
    ec2_resource = localstack_client.session.resource("ec2")
    monkeypatch.setattr(ec2,"ec2_resource",localstack_client.session.resource("ec2"))
    monkeypatch.setattr(ec2,"ec2_client",localstack_client.session.client("ec2"))
    yield "patching resources."

@pytest.fixture
def loggerfactory():
    class logger():
        def __init__(self):
            self.logs = []
        def append(self,message):    
            self.logs.append(message)
        def write(self): 
            logging.warning("SEE Below: \n"+str("\n".join(self.logs)))
    yield logger()        

@pytest.fixture
def create_ami():
    instance = ec2_resource.create_instances(MaxCount = 1,MinCount=1)[0]
    ami = ec2_client.create_image(InstanceId=instance.instance_id,Name = "dummy")
    yield ami["ImageId"]

@pytest.fixture
def create_instance_profile():
    profilename = "SSMRole"
    iam_resource = localstack_client.session.resource('iam')
    iam_client = localstack_client.session.client('iam')
    instance_profile = iam_resource.create_instance_profile(
    InstanceProfileName=profilename,
    Path='string'
    )
    yield instance_profile
    iam_client.delete_instance_profile(
    InstanceProfileName=profilename,
    )


@pytest.fixture
def create_securitygroup():
    testgroup = "test_security_localstack_group"
    ec2_client = localstack_client.session.client("ec2")
    ec2_resource = localstack_client.session.resource("ec2")
    ec2_client.create_security_group(Description='test security group',
    GroupName=testgroup)
    yield testgroup
    ec2_client.delete_security_group(GroupName = testgroup)

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
    
    Additionally sets up a separate bucket, "{sep_bucket}", with the following structure:
    /
    |-sep_inputs     %% these for "bucket bypass"
        |-data.json
    |-sep_configs
        |-config.json
    |-sep_results
        |-

    """
    subkeys = {
            "inputs/data1.json":{"data":"value"},
            "inputs/data2.json":{"data":"value"},
            "configs/config.json":{"param":"p1"},
            "configs/fullconfig.json":{"param":"p1","__duration__":360,"__dataset_size__":20,"ensemble_size":5},
            "configs/duration10config.json":{"param":"p1","__duration__":10,"__dataset_size__":20},
            "configs/duration600config.json":{"param":"p1","__duration__":600,"__dataset_size__":20},
            "configs/durationnoneconfig.json":{"param":"p1","__dataset_size__":20},
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
                "configname":os.path.join(user_name,"configs","config22.json")},
            "submissions/10_10submit.json":{ ## These are submit files for testing costmonitoring that takes into account the other instances in a job.
                "dataname":[os.path.join(user_name,"inputs","data1.json") for d in range(10)],
                "configname":os.path.join(user_name,"configs","duration10config.json"),
                "timestamp":"testtimestamp"},
            "submissions/10_600submit.json":{
                "dataname":[os.path.join(user_name,"inputs","data1.json") for d in range(10)],
                "configname":os.path.join(user_name,"configs","duration600config.json"),
                "timestamp":"testtimestamp"},
            "submissions/10_nonesubmit.json":{
                "dataname":[os.path.join(user_name,"inputs","data1.json") for d in range(10)],
                "configname":os.path.join(user_name,"configs","durationnoneconfig.json"),
                "timestamp":"testtimestamp"},
            ## new: bucket skip. 
            "submissions/bucketskipsubmit.json":{
                "dataname":os.path.join("s3://{}".format(sep_bucket),"sep_inputs","datasep.json"),
                "configname":os.path.join("s3://{}".format(sep_bucket),"sep_configs","configsep.json"),
                "timestamp":"testtimestamp",
                "resultpath":"s3://{}/sep_results".format(sep_bucket)}
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
        ## Test storage bypass with additional subkeys     
        s3_client.create_bucket(Bucket = sep_bucket)
        ind_data = {
            "sep_inputs/datasep.json":{"data":"value"},
            "sep_configs/configsep.json":{"param":"p1"}}
        for d in ind_data:
            writeobj = s3_resource.Object(sep_bucket,d)
            content = bytes(json.dumps(ind_data[d]).encode("UTF-8"))
            writeobj.put(Body=content)

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
def kill_instances():
    """Kill if unattended instances have been left running."""
    yield "kill uncleaned instances"
    session = localstack_client.session.Session()
    ec2_resource = session.resource("ec2")
    instances = ec2_resource.instances.filter(Filters = [{"Name":"instance-state-name","Values":["running"]}]) 
    for instance in instances:
        instance.terminate()

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

@pytest.fixture    
def set_price(monkeypatch):
    def staticpricing(region,instance,os):
        return 1 
    monkeypatch.setattr(pricing,"get_price",staticpricing)
    #monkeypatch.setattr(submit_start,"utilsparampricing.get_price",staticpricing)

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
        if type(dataname)!= list:
            sd.data_name_list = [dataname]
        elif type(dataname) == list:    
            sd.data_name_list = dataname
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
    def test_Submission_dev_get_costmonitoring(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_price,patch_boto3_ec2):
        session = localstack_client.session.Session()
        ssm_client = session.client("ssm")
        monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        sd.check_existence() ## check existence of dataset files. Necessary bc we project costs of this job. 
        sd.parse_config()
        assert sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_price,patch_boto3_ec2):
        session = localstack_client.session.Session()
        ssm_client = session.client("ssm")
        monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        sd.check_existence()
        sd.parse_config()
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_fail_active(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_price,patch_boto3_ec2):
        session = localstack_client.session.Session()
        ssm_client = session.client("ssm")
        monkeypatch.setattr(ssm, "ssm_client", session.client("ssm")) 
        #def raiser(ami,other):
        #    raise Exception
        #monkeypatch.setattr(submit_start.Submission_dev,"prices_active_instances_ami",raiser)
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        sd.check_existence()
        sd.parse_config()
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_under,set_price,patch_boto3_ec2):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        sd.check_existence()
        sd.parse_config()
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_over,set_price,patch_boto3_ec2):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        sd.check_existence()
        sd.parse_config()
        assert sd.get_costmonitoring()
    
    def test_Submission_dev_get_costmonitoring_ssm_default_fail(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_other,set_price,patch_boto3_ec2):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1200))
        sd.check_existence()
        sd.parse_config()
        assert not sd.get_costmonitoring()

    def test_Submission_dev_get_costmonitoring_ssm_default(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_other,set_price,patch_boto3_ec2):
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        sd = submit_start.Submission_dev(bucket_name,key_name,"111111111")
        monkeypatch.setenv("MAXCOST",str(1300))
        sd.check_existence()
        sd.parse_config()
        assert sd.get_costmonitoring()

    @pytest.mark.parametrize("submitname,maxcost,response",[("10_10submit.json",1265,False),("10_600submit.json",1266,False),("10_nonesubmit.json",1265,False),("10_10submit.json",1267,True),("10_600submit.json",1365,True),("10_nonesubmit.json",1275,True)]) ## These calculated with a base cost very close to 1265. The default timing (shown at top) is 60 mins.
    def test_Submission_dev_get_costmonitoring_allinsts(self,setup_lambda_env,setup_testing_bucket,check_instances,monkeypatch,set_ssm_budget_other,submitname,maxcost,response,set_price,patch_boto3_ec2):    
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_dir = os.path.dirname(submit_path)
        ## use submit files submissions/{10_10submit.json,10_600submit.json,10_nonesubmit.json}

        sd = submit_start.Submission_dev(bucket_name,os.path.join(submit_dir,submitname),"111111111")
        monkeypatch.setenv("MAXCOST",str(maxcost))
        sd.check_existence()
        sd.parse_config()
        assert sd.get_costmonitoring() == response

    def test_Submission_dev_prices_active_instances_ami(self,create_securitygroup,create_ami,create_instance_profile,setup_lambda_env,setup_testing_bucket,loggerfactory,check_instances,monkeypatch,set_ssm_budget_other,set_price,patch_boto3_ec2,kill_instances):    
        instance_type = "p3.2xlarge"
        ami = create_ami
        monkeypatch.setenv("AMI",ami)
        sg = create_securitygroup
        monkeypatch.setenv("SECURITY_GROUPS",sg)

        logger = loggerfactory 
        number = 20
        add_size = 200
        duration = 5*60
        group = "usergroup" 
        analysis = "ana1"
        job = "job1"

        message = patch_boto3_ec2
        response1 = ec2.launch_new_instances_with_tags_additional(instance_type,ami,logger,number,add_size,duration,group,analysis,job)

        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_dir = os.path.dirname(submit_path)
        ## use submit files submissions/{10_10submit.json,10_600submit.json,10_nonesubmit.json}

        sd = submit_start.Submission_dev(bucket_name,os.path.join(submit_dir,"10_10submit.json"),"111111111")
        price = sd.prices_active_instances_ami(ami)
        assert price == number*duration/60 

    def test_Submission_dev_get_costmonitoring__many_active(self,create_securitygroup,create_ami,create_instance_profile,setup_lambda_env,setup_testing_bucket,loggerfactory,check_instances,monkeypatch,set_ssm_budget_other,set_price,patch_boto3_ec2,kill_instances):    
        instance_type = "p3.2xlarge"
        ami = create_ami
        monkeypatch.setenv("AMI",ami)
        sg = create_securitygroup
        monkeypatch.setenv("SECURITY_GROUPS",sg)

        logger = loggerfactory 
        number = 10
        add_size = 200
        duration = 5*60
        group = "usergroup" 
        analysis = "ana1"
        job = "job1"

        message = patch_boto3_ec2
        response1 = ec2.launch_new_instances_with_tags_additional(instance_type,ami,logger,number,add_size,duration,group,analysis,job,)

        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        submit_dir = os.path.dirname(submit_path)
        ## use submit files submissions/{10_10submit.json,10_600submit.json,10_nonesubmit.json}

        sd = submit_start.Submission_dev(bucket_name,os.path.join(submit_dir,"10_10submit.json"),"111111111")
        monkeypatch.setenv("MAXCOST",str(1296))
        sd.check_existence()
        sd.parse_config()
        assert sd.get_costmonitoring() == False

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

    def test_Submission_dev_acquire_instances(self,create_securitygroup,create_instance_profile,monkeypatch,setup_lambda_env,setup_testing_bucket,create_ami,kill_instances):
        """For this test, we generate fake instances. We need to monkeypatch into ec2 in order to do so.  

        """
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        ami = create_ami
        sg = create_securitygroup

        session = localstack_client.session.Session()
        monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
        monkeypatch.setenv("SECURITY_GROUPS",sg)
        monkeypatch.setattr(ec2,"ec2_resource",session.resource("ec2"))

        sd = submit_start.Submission_dev(bucket_name,submit_path,"111111111")
        monkeypatch.setenv("AMI",ami)
        sd.config_name = os.path.join(user_name,"configs","fullconfig.json")
        sd.check_existence()
        sd.parse_config()
        sd.compute_volumesize()
        sd.acquire_instances()
        info= ec2_client.describe_instances(InstanceIds = [i.id for i in sd.instances])
        for instanceinfo in info["Reservations"][0]["Instances"]:
            tags = instanceinfo["Tags"]
            assert {"Key":"PriceTracking","Value":"On"} in tags
            assert {"Key":"Timeout","Value":"360"} in tags
            assert {"Key":"group","Value":sd.path} in tags
            assert {"Key":"job","Value":sd.jobname} in tags
            assert {"Key":"analysis","Value":sd.bucket_name} in tags

    def test_Submission_dev_skip(self,create_securitygroup,monkeypatch,create_instance_profile,setup_lambda_env,setup_testing_bucket,create_ami,kill_instances):
        """Like the test directly above, but assuming we run in "storage skip" mode. 

        """

        ## set up the os environment correctly. 
        bucket_name,submit_path = setup_testing_bucket[0],setup_testing_bucket[1]
        ami = create_ami
        sg = create_securitygroup

        ## we need the s3 and ec2 relevant modules patched:  
        session = localstack_client.session.Session()
        monkeypatch.setattr(s3,"s3_client",session.client("s3"))
        monkeypatch.setattr(s3,"s3_resource",session.resource("s3"))
        monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
        monkeypatch.setenv("SECURITY_GROUPS",sg)
        monkeypatch.setattr(ec2,"ec2_resource",session.resource("ec2"))
        skipsubmit = os.path.join(os.path.dirname(submit_path),"bucketskipsubmit.json")

        sd = submit_start.Submission_dev(bucket_name,skipsubmit,"111111111")
        assert sd.bypass_data["input"]["bucket"] == sep_bucket
        assert sd.bypass_data["output"]["bucket"] == sep_bucket
        assert sd.bypass_data["input"]["datapath"] == ["sep_inputs/datasep.json"]
        assert sd.bypass_data["input"]["configpath"] =="sep_configs/configsep.json" 
        assert sd.bypass_data["output"]["resultpath"] =="sep_results" 
        monkeypatch.setenv("AMI",ami)
        ## get submit file
        submit= s3.load_json(bucket_name,skipsubmit)

        ## Check that data and config exist at non-traditional location given full path: 
        sd.check_existence()
        ## Check that output directory exists: 
        assert len(s3.ls_name(sep_bucket,os.path.join("sep_results","job__test-submitlambda-analysis_testtimestamp","logs"))) > 0

        ## Check bucket name and path are not altered for all other processing:  
        assert sd.bucket_name == bucket_name
        assert sd.path == re.findall('.+?(?=/'+os.environ["SUBMITDIR"]+')',skipsubmit)[0]
        sd.parse_config()
        sd.compute_volumesize()
        sd.acquire_instances()
        #sd.start_instance()
        commands = sd.process_inputs(dryrun=True)
        assert commands[0] == os.environ["COMMAND"].format(sep_bucket,"sep_inputs/datasep.json","s3://independent/sep_results/job__test-submitlambda-analysis_testtimestamp","sep_configs/configsep.json")
        info= ec2_client.describe_instances(InstanceIds = [i.id for i in sd.instances])
        #for instanceinfo in info["Reservations"][0]["Instances"]:
        #    tags = instanceinfo["Tags"]
        #    assert {"Key":"PriceTracking","Value":"On"} in tags
        #    assert {"Key":"Timeout","Value":"360"} in tags
        #    assert {"Key":"group","Value":sd.path} in tags
        #    assert {"Key":"job","Value":sd.jobname} in tags
        #    assert {"Key":"analysis","Value":sd.bucket_name} in tags

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
        
    def test_Submission_ensemble_process_inputs(self,create_securitygroup,create_instance_profile,monkeypatch,setup_lambda_env,setup_testing_bucket,create_ami,kill_instances):
        """This test is expected to leave something running. Kill afterwards. 

        """
        ami = create_ami
        sg = create_securitygroup
        session = localstack_client.session.Session()
        monkeypatch.setattr(ec2,"ec2_client",session.client("ec2"))
        monkeypatch.setenv("SECURITY_GROUPS",sg)
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
    def test_Submission_Launch_Monitor(self,setup_lambda_env,setup_testing_bucket_legacy,kill_instances,check_instances):
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

