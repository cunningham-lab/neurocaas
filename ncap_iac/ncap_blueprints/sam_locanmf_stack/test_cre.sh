#!/bin/bash 
## Script to test create lambda. 
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

sam local invoke S3PutObjectFunction --event ../template_utils/simevents/cfn_createevent.json -n ../template_utils/simevents/cfn_funcs_env_vars.json



