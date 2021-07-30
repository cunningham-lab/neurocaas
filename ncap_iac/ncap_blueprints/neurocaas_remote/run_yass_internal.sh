#!/bin/bash

## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
echo execpath
echo "here is the processdir: "
echo $processdir
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Set up error logging. 
errorlog

## Custom setup for this workflow.
source .dlamirc

## Environment setup
export PATH="/home/ubuntu/anaconda3/bin:$PATH"
source activate yass

## Declare local storage locations: 
userhome="/home/ubuntu"
## .bin data, geom.txt, and config.yaml all in same directory
datastore="yass/samples/localdata"
outstore="yass/samples/localdata/tmp"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
# download "$inputpath" "$bucketname" "$datastore"
aws s3 cp "s3://$bucketname/$inputpath" "$datastore"
aws s3 cp "s3://$bucketname/$(dirname "$inputpath")/geom.txt" "$datastore"


## Stereotyped download script for config: 
# download "$configpath" "$bucketname" "$datastore"
aws s3 cp "s3://$bucketname/$configpath" "$datastore"

## Go to data directory and call yass sort
cd "$userhome/$datastore"
echo "Starting analysis..."
yass sort config.yaml
echo "Done."

## Go to result directory
cd "$userhome/$outstore"
aws s3 sync ./ "s3://$bucketname/$groupdir/$processdir"
cd "$userhome"
