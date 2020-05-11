#!/bin/bash 
### Script that automates the creation of new analysis blueprint projects. Given a name for a new project, creates a folder, installs a blueprint template inside. 
set -e
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ncaprootdir="$(dirname "$(dirname "$scriptdir")")"

source "$scriptdir"/paths.sh

source activate sam

## Input management: 
## Get the path to the directory where user data is stored: 
[ "$#" == 1 ] || { echo "ERROR: input is template name to be created"; exit; }
## Check the name is valid. 
#python $scriptdir/checkpath.py "$1"

#Now make a directory: 
echo $scriptdir, $ncaprootdir
cd "$ncaprootdir"/ncap_blueprints
mkdir "$1"
# Make a subdirectory for testing materials 
mkdir "$1"/test_resources

## Copy in the stack config template: 
cp ../utils/templates/stack_config_template_newexample.json "$ncaprootdir"/ncap_blueprints/"$1"/stack_config_template.json 

## Now alter variables to match what are given in initialized global parameters: 
secgroup=$(jq '.securitygroupdeployname' "$ncaprootdir"/global_params_initialized.json | sed 's/"//g')
tmp=$(mktemp)
jq --arg secgroup $secgroup '.Lambda.LambdaConfig.SECURITY_GROUPS = $secgroup' "$ncaprootdir"/ncap_blueprints/"$1"/stack_config_template.json > $tmp && mv $tmp "$ncaprootdir"/ncap_blueprints/"$1"/stack_config_template.json 

# Also copy in testing materials: 
cp ../utils/templates/exampledevsubmit.json "$ncaprootdir"/ncap_blueprints/"$1"/test_resources/exampledevsubmit.json
cp ../utils/simevents/s3_putevent.json "$ncaprootdir"/ncap_blueprints/"$1"/test_resources/s3_putevent.json
cp ../utils/simevents/{cloudwatch_startevent.json,cloudwatch_termevent.json} "$ncaprootdir"/ncap_blueprints/"$1"/test_resources/
cp ../utils/templates/{computereport_1234567.json,computereport_2345678.json} "$ncaprootdir"/ncap_blueprints/"$1"/test_resources/ 

#git add "$ncaprootdir"/ncap_blueprints/"$1"/ 
#git commit -m "automatic commit: deployed pipeline '$1'" 
#git push
