#!/bin/bash

cd ncap_iac/ncap_blueprints/

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

