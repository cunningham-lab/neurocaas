## A module to work with AMIs for the purpose of debugging and updating. 
import boto3 
import sys 
import os 
import json 

## Given the path to a pipeline, launches an instance of the ami currently tethered to that ami as the default.  
def launch_default_ami(path):
    ## Get the configuration file from the current pipeline: 
    config_filepath = 'stack_config_template.json'
    config_fullpath = os.path.join(path,config_filepath)
    print(config_fullpath)
    ## Load in:
    with open(config_fullpath,'r') as f:
        config = json.load(f)
    ## Get ami id
    ami_id = config['Lambda']['LambdaConfig']['AMI']
    

