#!/bin/bash 
# Script that automates the testing of analysis stacks from templates. 
## Three different types of tests: 
## 1. sam-lambda tests on their own using test resources in the bucket.  
## 2. tests with fake events you initially had on the repo. 
## 3. tests for correct configuration of ec2 instance (same as 2?)

set -e
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ncaprootdir="$(dirname "$(dirname "$scriptdir")")"

storagebucketname=$(jq .bucketname "$ncaprootdir/global_params_initialized.json" | sed 's/\"//g')

source "$scriptdir"/paths.sh
## Get the path to this particular file. 
## NOTE: Add the anaconda path if running as admin.  
export PATH="/miniconda/bin:$PATH"
source "$HOME/miniconda/etc/profile.d/conda.sh"
conda activate neurocaas

## Input management: 
## Get the path to the directory where user data is stored: 
[ -d "$1" ] || { echo "ERROR: Must give path to analysis stack directory"; exit; }

PIPEDIR=$(get_abs_filename "$1")
## This can give us the stack name: 

PIPESTR=$(jq ".PipelineName" "$PIPEDIR"/stack_config_template.json)

PIPENAME=$(echo "$PIPESTR" | tr -d '"')

## Check this is alphanumeric: 
python "$scriptdir"/checkpath.py "$PIPENAME"

## Give the path to the root directory for ncap (we like absolute paths) 

cd $ncaprootdir/utils
stage=$(jq ".STAGE" "$PIPEDIR"/stack_config_template.json ) 
stagestr=$(echo $stage | tr -d '"')
echo $stagestr
python dev_builder.py $PIPEDIR/stack_config_template.json "$stagestr"
cd $PIPEDIR

## main lambda test
sam local invoke MainLambda --event test_resources/s3_putevent.json -n test_resources/main_func_env_vars.json 

## search lambda test 
aws s3 cp test_resources/i-1234567890abcdef0.json s3://"$stackname"/logs/active/

sam local invoke FigLambda --template .aws-sam/build/template.yaml --event test_resources/cloudwatch_startevent.json -n test_resources/main_func_env_vars.json
sam local invoke FigLambda --template .aws-sam/build/template.yaml --event test_resources/cloudwatch_termevent.json -n test_resources/main_func_env_vars.json

## Make tests for jobs. 
### check budgeting function can't launch too many jobs at once. 

### check tags 

