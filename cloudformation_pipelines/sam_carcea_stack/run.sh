#!/bin/bash

## Make temporary directory: 

if [ ! -f "./vmnt/tmp_videos" ]; then sudo mkdir ./vmnt/tmp_videos; fi
sudo chmod 777 ./vmnt/tmp_videos

# Run the script: 
cd anaconda3/bin
source activate video
cd ../../Video_Pipelining
python Download_Segment_Upload.py "$*" 

## Remove 
cd ..
sudo rm -r ./vmnt/tmp_videos

