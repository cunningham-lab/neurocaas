#!/bin/bash
set -e 
source "$(dirname $0)"/paths.sh
rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))
userdirname="ciuserstack"
cd $rootpath/ncap_iac/user_profiles;
bash iac_utils/configure.sh "$userdirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_user.py "$userdirname"

bash iac_utils/deploy.sh "$userdirname"

analysisdirname="cianalysisstack"
cd $rootpath/ncap_iac/ncap_blueprints;
bash iac_utils/configure.sh "$analysisdirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_analysis.py "$analysisdirname" 

bash iac_utils/fulldeploy.sh "$analysisdirname"

# Cleanup
aws cloudformation delete-stack --stack-name "$analysisdirname"
rm -r "$analysisdirname"

cd $rootpath/ncap_iac/user_profiles
aws cloudformation delete-stack --stack-name "$userdirname"
rm -r "$userdirname"

