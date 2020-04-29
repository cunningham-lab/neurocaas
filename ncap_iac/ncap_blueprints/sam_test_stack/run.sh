#!/bin/bash

# First activate the correct environment
cd ./anaconda3/bin
source activate pca

## Download the analysis folder 
v1="$(dirname "$1")"

cd ../../

## Navigate to the right directory 
cd ctn_lambda/analysis_code/pca_example

python pca.py "testarray"

ls ../../
cd ../../transfer_utils

python Upload_S3.py ../analysis_code/pca_example/figs/ testfigs ncapctnfigurelogs  
