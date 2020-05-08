#!/bin/bash
## Bash script to distribute template resources to different aws folders. not under IAC.  

# Arg 1: path to source folder for resources. 
# Arg 2: Target local folder containing stack config file for pipeline of interest. Test resources will be distributed to all 
# Arg 3: path that test resources will be distributed from/to (should be inputs or configs) (if configs, path will e changed appropriately). 
# Arg 4: affiliate group name. Can be "all" if distributing to all memebers.  

#Get the group names from the target folder. 
#echo $(jq -r ".UXData.Affiliates" $2/stack_config_template.json)

bucket_name=$(jq -r ".PipelineName" $2/stack_config_template.json)
echo $bucket_name

## If configs, we write locally, then read back. 
## If all, we apply to all groups. otherwise, we interact with only one. 
if [ $3 == "configs" ]
then
    if [ $4 == "all" ]
    then 
        jq -r ".UXData.Affiliates|keys[]" $2/stack_config_template.json | while read key ; do 
        aff=$(jq ".UXData.Affiliates[$key].AffiliateName" $2/stack_config_template.json | sed 's/"//g')
        # first copy locally to change the paths. 
        aws s3 sync s3://neurocaastemplatedata/$1/$3 ./tmp_config/
        for entry in ./tmp_config/*
            do 
                echo $entry
                sed -i '' 's/{NEUROCAASPATH}/'$aff'/g' $entry
            done
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/results/template_materials/$3/
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/$3/
        echo s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/results/template_materials/$3/
        done
    else
        aws s3 sync s3://neurocaastemplatedata/$1/$3 ./tmp_config/
        for entry in ./tmp_config/*
            do 
                echo $entry
                sed -i '' 's/{NEUROCAASPATH}/'$aff'/g' $entry
            done
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/results/template_materials/$3/
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/$3/
        echo s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/results/template_materials/$3/
    fi

elif [ $3 == "inputs" ]
then
    if [ $4 == "all" ] 
    then
        jq -r ".UXData.Affiliates|keys[]" $2/stack_config_template.json | while read key ; do 
        aff=$(jq ".UXData.Affiliates[$key].AffiliateName" $2/stack_config_template.json | sed 's/"//g')
        echo s3://$bucket_name/$aff/$3/template_$3/
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/results/template_materials/$3/
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/$3/
        echo s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$aff/results/template_materials/$3/

        done
    else 
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/results/template_materials/$3/
        aws s3 sync s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/$3/
        echo s3://neurocaastemplatedata/$1/$3/ s3://$bucket_name/$4/results/template_materials/$3/
    fi
else
    echo "argument $3 not recognized"
fi 

