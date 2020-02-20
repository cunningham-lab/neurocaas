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
cp stack_config_template_newexample.json "$ncaprootdir"/ncap_blueprints/"$1"/stack_config_template.json 



