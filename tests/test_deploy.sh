#!/bin/bash
## Requires that you set the variables "userdirname" and "analysisdirname" ahead of time in the environment.  
if [ -z "$userdirname" ]
then
    echo "required variable userdirname not set"
    exit 1
elif [ -z "$analysisdirname" ]
then
    echo "required variable analysisdirname not set"
    exit 1
else
    echo "required variables set, proceeding"
fi


set -e 
source "$(dirname $0)"/paths.sh

rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))

## First, set up the user and analysis stacks you will use to underlie future tests.

## User stack setup:

## Make a directory to store creds for later steps. 
mkdir "$(dirname $rootpath)"/ncap_user_creds
cd $rootpath/ncap_iac/user_profiles;
bash iac_utils/configure.sh "$userdirname"

python $rootpath/tests/initialize_test_user.py "$userdirname"

bash iac_utils/deploy.sh "$userdirname"

## Analysis stack setup 
bash iac_utils/configure.sh "$analysisdirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_analysis.py "$analysisdirname"

bash iac_utils/fulldeploy.sh "$analysisdirname"

## Now run tests:
cd $rootpath/ncap_iac/ncap_blueprints

statusbuild=$(bash iac_utils/build.sh epi_web_stack)
statustest=$(bash iac_utils/test_main.sh epi_web_stack)

if [ $statustest -eq 0 ]
then
    code=0
else
    echo $statustest
    code=99
fi
echo $code
echo $statustest statustest
echo $statustest >> status.txt
echo $code >> status.txt
echo $statusbuild >> status.txt
exit $code



