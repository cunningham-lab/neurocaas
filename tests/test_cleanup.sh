#!/bin/bash
aws cloudformation delete-stack --stack-name "$analysisdirname"
rm -r "$analysisdirname"

cd $rootpath/ncap_iac/user_profiles
aws cloudformation delete-stack --stack-name "$userdirname"
rm -r "$userdirname"

