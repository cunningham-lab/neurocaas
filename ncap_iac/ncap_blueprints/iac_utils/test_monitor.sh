#!/bin/bash
### Script that automates the testing of submission lambda functions 
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
cd $PIPEDIR

## Test main lambda function
aws s3 cp test_resources/i-1234567890abcdef0.json s3://epi-ncap-stable/logs/active/
sam local invoke FigLambda --event test_resources/cloudwatch_startevent.json -n ../../utils/simevents/main_func_env_vars.json 
sam local invoke FigLambda --event test_resources/cloudwatch_termevent.json -n ../../utils/simevents/main_func_env_vars.json 
