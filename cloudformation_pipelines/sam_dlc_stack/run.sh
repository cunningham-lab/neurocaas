#!/bin/bash
## CRITICAL to add cuda drivers to identifiable path. 
source .dlamirc
## CRITICAL to allow for source activate commands. (okay not as critical as the first thing )
export PATH="/home/ubuntu/anaconda3/bin:$PATH"
## Don't worry about these; done inside the dlamirc o
#export LD_LIBRARY_PATH="/usr/local/cuda-9.0:$LD_LIBRARY_PATH"
#export CUDA_HOME="/usr/local/cuda-9.0:$CUDA_HOME" 

## Activate the environment: 
source activate dlcami

#echo $LD_LIBRARY_PATH
#echo $PATH
#echo $PKG_CONFIG_PATH
#echo $PYTHONPATH
part1="$2"
pathname="$(dirname "$(dirname "$2")")"
bucketname="$1"
resultsname="$3"

#python gpuscript.py

sudo mkdir -p auxvolume/temp_videofolder
sudo chmod 777 auxvolume/temp_videofolder

## Download only mp4s:
python Video_Pipelining/Download_S3_single.py "$part1" "$bucketname" "auxvolume/temp_videofolder/" 

## Run deeplabcut analysis: 
cd DeepLabCut/Analysis-tools

python AnalyzeVideos.py

## Activate script to pipeline analyses: 
cd ../../Video_Pipelining

python Upload_S3.py '../auxvolume/temp_videofolder/' "$bucketname" "$pathname" "$resultsname" "mp4"

## Delete temp folder
rm -r ../auxvolume/temp_videofolder 

sudo poweroff
