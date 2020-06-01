#!/bin/bash

## We will first ask if each stack already exists: 

## Initialize AWS resources necessary to launch instances autonomously. 
aws cloudformation describe-stacks --stack-name testutilsstack > init_log.txt 2>&1
existscode=$?
if [ $existscode -eq 255 ] 
then
    echo "Resource Roles do not exist, creating."
    echo "Resource Roles do not exist, creating." >> init_log.txt 2>&1
    aws cloudformation create-stack --stack-name testutilsstack --template-body file://resource_roles.json  --capabilities CAPABILITY_NAMED_IAM

    aws cloudformation wait stack-create-complete --stack-name testutilsstack
elif [ $existscode -eq 0 ]
then 
    echo "Stack testutilsstack already exists, skipping creation."
    echo "Stack testutilsstack already exists, skipping creation." >> init_log.txt 2>&1
else
    echo "Unknown error code $existscode. Exiting" 
    echo "Unknown error code $existscode. Exiting" >> init_log.txt 2>&1
    exit 1
fi

ssmstackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "SSMRole") | .PhysicalResourceId' | sed 's/\"//g')
lambdastackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "LambdaRole") | .PhysicalResourceId' | sed 's/\"//g')
ec2stackoutput=$(aws cloudformation describe-stack-resources --stack-name testutilsstack | jq '.StackResources[] | select(.LogicalResourceId == "EC2Role") | .PhysicalResourceId' | sed 's/\"//g')


## Now create a stack creating security groups:
aws cloudformation describe-stacks --stack-name testsgstack >> init_log.txt 2>&1
existscode=$?
if [ $existscode -eq 255 ]
then
    echo "Security groups do not exist yet. Creating."
    echo "Security groups do not exist yet. Creating." >> init_log.txt 2>&1
    aws cloudformation create-stack --stack-name testsgstack --template-body file://security_groups.json  --capabilities CAPABILITY_IAM

    aws cloudformation wait stack-create-complete --stack-name testsgstack
elif [ $existscode -eq 0 ]
then 
    echo "Stack testsgstack already exists, skipping creation."
    echo "Stack testsgstack already exists, skipping creation." >> init_log.txt 2>&1
else 
    echo "Unknown error code $existscode. Exiting."
    echo "Unknown error code $existscode. Exiting." >> init_log.txt 2>&1
    exit 1
fi

## get the names of the security groups you made here
sgdevoutput=$(aws cloudformation describe-stack-resources --stack-name testsgstack | jq '.StackResources[] | select(.LogicalResourceId == "SecurityGroupDev") | .PhysicalResourceId' | sed 's/\"//g')
sgdeployoutput=$(aws cloudformation describe-stack-resources --stack-name testsgstack | jq '.StackResources[] | select(.LogicalResourceId == "SecurityGroupDeploy") | .PhysicalResourceId' | sed 's/\"//g')

## Now create a stack creating storage for cfn artifacts:
aws cloudformation describe-stacks --stack-name teststoragestack >> init_log.txt 2>&1
existscode=$?
if [ $existscode -eq 255 ]
then 
    echo "Storage bucket for build artifacts does not exist yet. Creating."
    echo "Storage bucket for build artifacts does not exist yet. Creating." >> init_log.txt 2>&1
    aws cloudformation create-stack --stack-name teststoragestack --template-body file://cfn_storage.json  

    aws cloudformation wait stack-create-complete --stack-name teststoragestack
elif [ $existscode -eq 0 ]
then
    echo "Stack teststoragestack already exists, skipping creation."
    echo "Stack teststoragestack already exists, skipping creation." >> init_log.txt 2>&1
else
    echo "Unknown error code $existscode. Exiting."
    echo "Unknown error code $existscode. Exiting." >> init_log.txt 2>&1
    exit 1
fi
## Get the name (Physical Resource ID) of the bucket that you created. 
storageoutput=$(aws cloudformation describe-stack-resources --stack-name teststoragestack |jq '.StackResources[] | select(.LogicalResourceId == "SubstackTemplateBucket") | .PhysicalResourceId' | sed 's/\"//g')

#Initialize a global parameter template that contains the output of these operations that can be referenced by stack builds.
jq --arg storage $storageoutput --arg lstack $lambdastackoutput --arg sstack $ssmstackoutput --arg estack $ec2stackoutput --arg sgdev $sgdevoutput --arg sgdeploy $sgdeployoutput '. + {"bucketname":"$storageoutput","lambdarolename":$lstack,"ssmrolename":$sstack,"ec2rolename":$estack,"securitygroupdevname":$sgdev,"securitygroupdeployname":$sgdeploy}' ../../global_params.json > ../../global_params_initialized.json

## Resources without a given output: 
## Create a stack based on an existing binx repo for generating ssh keys with cfn. 
aws cloudformation describe-stacks --stack-name testkeystack >> init_log.txt 2>&1
existscode=$?
if [ $existscode -eq 255 ]
then
    echo "ssh keys do not exist yet. Creating."
    echo "ssh keys do not exist yet. Creating." >> init_log.txt 2>&1
    aws cloudformation create-stack --stack-name testkeystack --template-body file://keygenerator.yaml 
    
    aws cloudformation wait stack-create-complete --stack-name testkeystack
elif [ $existscode -eq 0 ]
then 
    echo "Stack testkeystack already exists, skipping creation."
    echo "Stack testkeystack already exists, skipping creation." >> init_log.txt 2>&1
else 
    echo "Unknown error code $existscode. Exiting."
    echo "Unknown error code $existscode. Exiting." >> init_log.txt 2>&1
    exit 1
fi
## Now initialize and package the user substack template so it can be freely referenced by all pipeline stacks:
sam build -t user_subtemplate.json -m "../../protocols/requirements.txt"
sam package --s3-bucket "$storageoutput" --output-template-file user_subtemplate_packaged.yaml
#aws cloudformation create-stack --stack-name automationdocstack --template-body file://automationdoc.yaml 

