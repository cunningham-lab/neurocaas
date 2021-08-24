import os 
import json
import pathlib
## Get global parameters:
utildir = pathlib.Path(__file__).parent.absolute()
basedir = os.path.dirname(os.path.dirname(utildir))
with open(os.path.join(basedir,"global_params.json")) as gp:
    gpdict = json.load(gp)

os.environ["BUCKET_NAME"] = "cianalysispermastack"
os.environ["REGION"] = "us-east-1"
os.environ["INDIR"] = "inputs"
os.environ["figlambarn"] = "arn"
os.environ["figlambid"] = "id"
