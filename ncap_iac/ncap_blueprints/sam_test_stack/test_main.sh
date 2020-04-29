#!/bin/bash
### Script that automates the testing of submission lambda functions 
set -e

## Set the date and time on the main lambda function dummy event:  
python ../iac_utils/changedate.py ../template_utils/simevents/s3_putevent_userbucket.json

## Test main lambda function


sam local invoke MainLambda --event ../template_utils/simevents/s3_putevent_userbucket_now.json -n ../template_utils/simevents/main_func_env_vars.json 
