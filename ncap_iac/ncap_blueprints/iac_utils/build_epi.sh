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
echo $1
[ -d "$1" ] || { echo "ERROR: Must give path to analysis stack directory"; exit; }

PIPEDIR=$(get_abs_filename "$1")
## This can give us the stack name: 

PIPESTR=$(jq ".PipelineName" "$PIPEDIR"/stack_config_template.json)

PIPENAME=$(echo "$PIPESTR" | tr -d '"')

## Check this is alphanumeric: 
python "$scriptdir"/checkpath.py "$PIPENAME"

## Give the path to the root directory for ncap (we like absolute paths) 

cd $ncaprootdir/ncap_blueprints/template_utils
## Run different deployment scripts based on version:
version=$(jq ".PipelineVersion" "$PIPEDIR"/stack_config_template.json ) 
versint=$(echo $version | tr -d '"')
if [ "$versint" == "null" ] 
then 
    echo "latest version"
    python postprocess_lambda.py $PIPEDIR/stack_config_template.json 
elif [ "$versint" -eq 1 ]
then
    echo "version 1"
    python config_handler.py $PIPEDIR/stack_config_template.json 
else
    echo "not a valid option, ending"
    exit 1
fi 

## We need to navigate to the pipeline directory because we have a relative path in our compilation code. 
cd $PIPEDIR

sam build -t compiled_template.json -m "$ncaprootdir"/ncap_blueprints/lambda_repo/requirements_epi.txt

