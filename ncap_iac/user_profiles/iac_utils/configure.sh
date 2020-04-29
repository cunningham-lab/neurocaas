#!/bin/bash 
### Script that automates the creation of new user profile templates. 
set -e
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ncaprootdir="$(dirname "$(dirname "$scriptdir")")"

source "$scriptdir"/paths.sh

source activate sam

## Input management: 
## Get the path to the directory where user data is stored: 
[ "$#" == 1 ] || { echo "ERROR: input is template name to be created"; exit; }
## Check the name is valid. 
python "$scriptdir"/checkpath.py "$1"

#Now make a directory: 
cd "$ncaprootdir"/user_profiles
mkdir "$1"
cp user_config_template.json "$ncaprootdir"/user_profiles/"$1"/user_config_template.json 



