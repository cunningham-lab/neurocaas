#!/bin/bash 
source activate sam

## Get the directory name: 
PIPEDIR=$PWD
## This can double as the stack name: 

PIPENAME=$(basename "$PIPEDIR")


cd ../template_utils
python user_maker.py $PIPEDIR/user_config_template.json #../sam_polleux_stack/stack_config_template.json

cd $PIPEDIR

sam build -t compiled_users.json -m ../lambda_repo/requirements.txt

sam package --s3-bucket ctnsampackages --output-template-file compiled_users.yaml

sam deploy --template-file compiled_users.yaml --stack-name $PIPENAME --capabilities CAPABILITY_NAMED_IAM


