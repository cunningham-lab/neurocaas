#!/bin/bash

## Initialize AWS resources necessary to launch templates. 

aws cloudformation update-stack --stack-name testutilsstack --template-body file://resource_roles.json  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-update-complete --stack-name testutilsstack

ssmstackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "SSMRole") | .PhysicalResourceId')
lambdastackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "LambdaRole") | .PhysicalResourceId')
ec2stackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "EC2Role") | .PhysicalResourceId')


## Now do the other stack:
aws cloudformation update-stack --stack-name testsgstack --template-body file://security_groups.json  --capabilities CAPABILITY_IAM

#aws cloudformation wait stack-update-complete --stack-name testsgstack

## get the names of the security groups you made here
sgdevoutput=$(aws cloudformation describe-stack-resources --stack-name testsgstack | jq '.StackResources[] | select(.LogicalResourceId == "SecurityGroupDev") | .PhysicalResourceId')
sgdeployoutput=$(aws cloudformation describe-stack-resources --stack-name testsgstack | jq '.StackResources[] | select(.LogicalResourceId == "SecurityGroupDeploy") | .PhysicalResourceId')

jq --arg lstack $lambdastackoutput --arg sstack $ssmstackoutput --arg estack $ec2stackoutput --arg sgdev $sgdevoutput --arg sgdeploy $sgdeployoutput '. + {"lambdarolename":$lstack,"ssmrolename":$sstack,"ec2rolename":$estack,"securitygroupdevname":$sgdev,"securitygroupdeployname":$sgdeploy}' ../../global_params.json > ../../global_params_initialized.json

aws cloudformation create-stack --stack-name testkeystack --template-body file://keygenerator.yaml 

aws cloudformation create-stack --stack-name automationdocstack --template-body file://automationdoc.yaml 

