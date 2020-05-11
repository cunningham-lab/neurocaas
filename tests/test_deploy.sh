#!/bin/bash
set -e 
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

source "$(dirname $0)"/paths.sh

rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))

## First, set up the user and analysis stacks you will use to underlie future tests.

## User stack setup:
#Declare some variables: 
testgroupid="traviscitestgroup"
testuserlist=("ciuser1" "ciuser2")

## Make a directory to store creds for later steps. 
mkdir -p "$(dirname $rootpath)"/ncap_user_creds
cd $rootpath/ncap_iac/user_profiles;
bash iac_utils/configure.sh "$userdirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_user.py "$userdirname" "$testgroupid" "${testuserlist[@]}"

bash iac_utils/deploy.sh "$userdirname"

## Analysis stack setup 
cd $rootpath/ncap_iac/ncap_blueprints
bash iac_utils/configure.sh "$analysisdirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_analysis.py "$analysisdirname" "$testgroupid" "${testuserlist[@]}"

bash iac_utils/fulldeploy.sh "$analysisdirname"

echo $(jq .Records[0].s3.bucket.name "$analysisdirname"/test_resources/s3_putevent.json)
echo $(jq .Records[0].s3.bucket.arn "$analysisdirname"/test_resources/s3_putevent.json)
### Now run tests:

## upload useful resources to the user's area. 
python $rootpath/tests/initialize_test_resources.py "$analysisdirname" "$testgroupid"

python $rootpath/tests/initialize_test_submit.py "$analysisdirname" "$testgroupid"
statusbuild=$(bash iac_utils/build.sh $analysisdirname)
statustest=$(bash iac_utils/test_main.sh $analysisdirname)

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



