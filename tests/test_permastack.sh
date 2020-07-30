#!/bin/bash
set -e
## This is a test of the "MainLambda" function as contained in the ncap_iac/protocols/submit_start.py module. It makes use of a permanently built stack (cianalysispermastack), and will use the FigLambda function there as part of its testing. Note that a semi-exhaustive set of 30 test cases for this function is contained in the "envs" section of the .travis.yml file above. This is a nice building block to assure that the main lambda function is correctly functioning.  

analysisdirname=cianalysispermastack
testgroupid=traviscipermagroup

source "$(dirname $0)"/paths.sh

rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))
cd $rootpath/ncap_iac/ncap_blueprints/

bash $rootpath/tests/create_profile.sh

statusbuild=$(bash iac_utils/build.sh $analysisdirname)
buildcode=$?

statustest=$(bash iac_utils/test_main_multievent.sh "$analysisdirname" "$1")
testcode=$?
#newtest=$(bash iac_utils/test_monitor.sh $analysisdirname)
echo "start line: the statustest code is: $testcode .this is from outside the statustest"

if [ $testcode -eq 0 ]
then
    code=0
else
    echo $testcode
    code=99
fi
echo $code
echo $statustest statustest
echo $statustest >> status.txt
echo $code >> status.txt
echo $statusbuild >> status.txt
exit $code




