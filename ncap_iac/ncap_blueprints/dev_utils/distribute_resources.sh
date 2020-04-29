#!/bin/bash
## Bash script to distribute template resources to different aws folders. not under IAC.  

# Arg 1: path to source folder for resources. 
# Arg 2: Target folder containing stack config file for pipeline of interest. Test resources will be distributed to all 
# Arg 3: path that test resources will be distributed from/to (should be inputs or configs). 

#Get the group names from the target folder. 
echo $(jq -r ".UXData.Affiliates" $2/stack_config_template.json)

bucket_name=$(jq -r ".PipelineName" $2/stack_config_template.json)
echo $bucket_name

jq -r ".UXData.Affiliates|keys[]" $2/stack_config_template.json | while read key ; do 
    aff=$(jq ".UXData.Affiliates[$key].AffiliateName" $2/stack_config_template.json | sed 's/"//g')
    echo s3://$bucket_name/$aff/$3/template_$3/
    aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/results/template_materials/$3/

done
