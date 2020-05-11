#!/bin/bash
source "$(dirname $0)"/paths.sh

rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))

cd $rootpath/ncap_iac/ncap_blueprints
aws cloudformation delete-stack --stack-name "$analysisdirname"
rm -r "$analysisdirname"

cd $rootpath/ncap_iac/user_profiles

aws iam remove-user-from-group --group-name "traviscitestgroup" --user-name "ciuser1us-east-1"
aws iam remove-user-from-group --group-name "traviscitestgroup" --user-name "ciuser2us-east-1"

aws cloudformation delete-stack --stack-name "$userdirname"
rm -r "$userdirname"

