#!/bin/bash 
## Script to test delete lambda. 
source activate sam

## Get the directory name: 
PIPEDIR=$PWD

PIPESTR=$(jq ".PipelineName" stack_config_template.json)

PIPENAME=$(echo "$PIPESTR" | tr -d '"')

cd ../template_utils
echo $PIPENAME $PIPESTR
python config_handler.py $PIPEDIR/stack_config_template.json #../sam_polleux_stack/stack_config_template.json

cd $PIPEDIR

sam build -t compiled_template.json -m ../lambda_repo/requirements.txt

## Test main lambda function
sam local invoke MainLambda --event ../template_utils/simevents/s3_putevent.json -n ../template_utils/simevents/main_func_env_vars_full.json 


