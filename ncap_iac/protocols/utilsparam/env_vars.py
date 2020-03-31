import os 
import json
## Get global parameters:
with open("../../global_params.json") as gp:
    gpdict = json.load(gp)

os.environ["REGION"] = "us-east-1"
os.environ["IAM_ROLE"] = "pmd-s3-ssm"
os.environ["KEY_NAME"] = "ta_testkey"
os.environ["SECURITY_GROUPS"] = "launch-wizard-34"
os.environ["SHUTDOWN_BEHAVIOR"] = "terminate"
os.environ["cwrolearn"] = "arn:aws:iam::739988523141:role/caiman-ncap-CloudWatchBusRole-1RUXFZTS0DOK0"
os.environ["INDIR"]=gpdict["input_directory"]
os.environ["OUTDIR"]=gpdict["output_directory"]
os.environ["LOGDIR"]=gpdict["log_directory"]
