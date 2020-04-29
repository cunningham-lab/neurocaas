#!/bin/bash
set -e
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

### Instance Setup
## CRITICAL to add cuda drivers to identifiable path. 
source .dlamirc
## CRITICAL to allow for source activate commands. (okay not as critical as the first thing )
export PATH="/home/ubuntu/anaconda3/bin:$PATH"
## Don't worry about these; done inside the dlamirc o

## Activate the environment: 
source activate dlcami

### Parameters: 
## We are executing as a different user, so reference the home directory: 
USERHOME="/home/ubuntu"

### Inputs
part1="$2"
pathname="$(dirname "$(dirname "$2")")"
bucketname="$1"
resultsname="$3"
configpath="$4"
configname="$(basename "$configpath")"

### Filesystem Setup
sudo mkdir -p auxvolume/temp_videofolder
sudo chmod 777 auxvolume/temp_videofolder
sudo mkdir -p auxvolume/temp_outfolder
sudo chmod 777 auxvolume/temp_outfolder
sudo mkdir -p auxvolume/temp_configfolder
sudo chmod 777 auxvolume/temp_configfolder

### Imports

## Download only files of the right extension:
python Video_Pipelining/Download_S3_single.py "$part1" "$bucketname" "$USERHOME/auxvolume/temp_videofolder/" 
python Video_Pipelining/Download_S3_single.py "$configpath" "$bucketname" "$USERHOME/auxvolume/temp_configfolder/" 


### Preprocess:
cd $USERHOME/Video_Pipelining 
python preprocess_video.py "$USERHOME/auxvolume/temp_videofolder" "$USERHOME/auxvolume/temp_configfolder/$configname" 
### Run deeplabcut analysis: 
cd $USERHOME/DeepLabCut/Analysis-tools

python AnalyzeVideos.py

## Activate script to pipeline analyses: 
cd $USERHOME/Video_Pipelining

python Carcea_Postprocess.py "$USERHOME/auxvolume/temp_videofolder" "$USERHOME/auxvolume/temp_outfolder" "$USERHOME/auxvolume/temp_configfolder/$configname" 
python Upload_S3.py "$USERHOME/auxvolume/temp_outfolder/" "$bucketname" "$pathname" "$resultsname" "mp4"

# Delete temp folder
rm -r ../auxvolume/temp_videofolder 
rm -r ../auxvolume/temp_outfolder 

sudo poweroff
