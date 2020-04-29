import os 
import json
import pathlib
## Get global parameters:
utildir = pathlib.Path(__file__).parent.absolute()
basedir = os.path.dirname(os.path.dirname(utildir))
with open(os.path.join(basedir,"global_params.json")) as gp:
    gpdict = json.load(gp)

os.environ["REGION"] = "us-east-1"
os.environ["IAM_ROLE"] = "SSMRole"
os.environ["KEY_NAME"] = "testkeystack-custom-dev-key-pair"
os.environ["SECURITY_GROUPS"] = "testsgstack-SecurityGroupDev-1NQJIDBJG16KK"
os.environ["SHUTDOWN_BEHAVIOR"] = "terminate"
os.environ["cwrolearn"] = "arn:aws:iam::739988523141:role/caiman-ncap-CloudWatchBusRole-1RUXFZTS0DOK0"
os.environ["INDIR"]=gpdict["input_directory"]
os.environ["OUTDIR"]=gpdict["output_directory"]
os.environ["LOGDIR"]=gpdict["log_directory"]
os.environ["CONFIGDIR"]=gpdict["config_directory"]
os.environ["SUBMITDIR"]=gpdict["submission_directory"]
os.environ["versionid"]="pytestingversion"
