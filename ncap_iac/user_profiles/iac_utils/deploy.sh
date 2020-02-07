#!/bin/bash 
### Script that automates the deployment of user profiles from templates. 
set -e
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ncaprootdir="$(dirname "$(dirname "$scriptdir")")"

source "$scriptdir"/paths.sh
## Get the path to this particular file. 
## NOTE: Add the anaconda path if running as admin.  
source activate sam

## Input management: 
## Get the path to the directory where user data is stored: 
[ -d "$1" ] || { echo "ERROR: Must give path to user profile directory"; exit; }

PIPEDIR=$(get_abs_filename "$1")
## This can double as the stack name: 
PIPENAME=$(basename "$PIPEDIR")

## Give the path to the root directory for ncap (we like absolute paths) 

cd $ncaprootdir/ncap_blueprints/template_utils
python user_maker.py "$PIPEDIR"/user_config_template.json 

cd "$PIPEDIR"

sam build -t compiled_users.json -m $ncaprootdir/ncap_blueprints/lambda_repo/requirements.txt

sam package --s3-bucket ctnsampackages --output-template-file compiled_users.yaml

sam deploy --template-file compiled_users.yaml --stack-name $PIPENAME --capabilities CAPABILITY_NAMED_IAM

## Added February 4th:
cd $ncaprootdir/ncap_blueprints/template_utils
python export_credentials.py $PIPEDIR 

########
