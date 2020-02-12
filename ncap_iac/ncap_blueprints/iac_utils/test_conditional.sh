#!/bin/bash 
PIPEDIR="$1"
version=$(jq ".PipelineVersion" "$PIPEDIR"/stack_config_template.json ) 
versint=$(echo $version | tr -d '"')
versint=3
if [ "$versint" == "null" ] 
then 
   echo "version 2"
   echo "first command"
elif [ "$versint" -eq 1 ]
then
   echo "version 1"
else
   echo "not a valid option, ending"
   exit 1
fi 


