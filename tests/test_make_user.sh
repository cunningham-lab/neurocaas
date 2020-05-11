#!/bin/bash
source "$(dirname $0)"/paths.sh
rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))
dirname="ciuserstack"
cd $rootpath/ncap_iac/user_profiles;
bash iac_utils/configure.sh "$dirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_user.py "$dirname" 

bash iac_utils/deploy.sh "$dirname"


## Cleanup 
aws cloudformation delete-stack --stack-name "$dirname"
rm -r $dirname


