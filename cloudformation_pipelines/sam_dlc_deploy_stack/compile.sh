#!/bin/bash 
source activate sam

## Get the directory name: 
PIPEDIR=$PWD

PIPESTR=$(jq ".PipelineName" stack_config_template.json)

PIPENAME=$(echo "$PIPESTR" | tr -d '"')

cd ../template_utils
echo $PIPENAME $PIPESTR
python config_handler_new.py $PIPEDIR/stack_config_template.json #../sam_polleux_stack/stack_config_template.json

cd $PIPEDIR

sam build -t compiled_template.json -m ../lambda_repo/requirements.txt

sam package --s3-bucket ctnsampackages --output-template-file compiled_packaged.yaml

sam deploy --template-file compiled_packaged.yaml --stack-name $PIPENAME --capabilities CAPABILITY_NAMED_IAM

