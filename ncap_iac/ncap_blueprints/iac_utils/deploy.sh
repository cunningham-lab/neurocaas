#!/bin/bash 
### Script that automates the deployment of analysis stacks from templates. 
set -e
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ncaprootdir="$(dirname "$(dirname "$scriptdir")")"

source "$scriptdir"/paths.sh
## Get the path to this particular file. 
## NOTE: Add the anaconda path if running as admin.  
source activate sam

## Input management: 
## Get the path to the directory where user data is stored: 
[ -d "$1" ] || { echo "ERROR: Must give path to analysis stack directory"; exit; }

PIPEDIR=$(get_abs_filename "$1")
## This can give us the stack name: 

PIPESTR=$(jq ".PipelineName" "$PIPEDIR"/stack_config_template.json)

PIPENAME=$(echo "$PIPESTR" | tr -d '"')


## Check this is alphanumeric: 
python "$scriptdir"/checkpath.py "$PIPENAME"

cd $PIPEDIR
sam package --s3-bucket ctnsampackages --output-template-file compiled_packaged.yaml

sam deploy --template-file compiled_packaged.yaml --stack-name $PIPENAME --capabilities CAPABILITY_NAMED_IAM

aws s3 cp test_resources/computereport_1234567.json s3://$PIPENAME/logs/debug"$PIPENAME"/
aws s3 cp test_resources/computereport_2345678.json s3://$PIPENAME/logs/debug"$PIPENAME"/
aws s3 sync test_resources/ s3://$PIPENAME//test_resources
