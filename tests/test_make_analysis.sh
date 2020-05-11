#!/bin/bash
source "$(dirname $0)"/paths.sh
rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))
dirname="cianalysisstack"
cd $rootpath/ncap_iac/ncap_blueprints;
bash iac_utils/configure.sh "$dirname"

## Initialize it with the info you would like
python $rootpath/tests/initialize_test_analysis.py "$dirname" 

bash iac_utils/fulldeploy.sh "$dirname"


# Cleanup 
#aws cloudformation delete-stack --stack-name "$dirname"
#rm -r $dirname


