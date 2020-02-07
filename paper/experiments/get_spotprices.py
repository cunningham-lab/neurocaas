import boto3
import numpy as np
from datetime import datetime
## Script to get an average spot instance cost

## Parameters
## Time period over which to calculate prices 
starttime = datetime(2019,9,10)
endtime = datetime(2019,9,12)

## Instance types:
## Instance types to analyze
instance_types = ["p2.xlarge","p3.2xlarge","m5.16xlarge"]

## Produce Descriptions: 
os = "Linux/UNIX"

## Fetch
client = boto3.client("ec2")

def getprice(histelement):
    return float(histelement["SpotPrice"])

for itype in instance_types: 
    output = client.describe_spot_price_history(AvailabilityZone = "us-east-1a",StartTime = starttime,EndTime = endtime,InstanceTypes = [itype],ProductDescriptions = [os])
    history = output["SpotPriceHistory"]

    prices = list(map(getprice, history))
    print(prices)
    print(np.mean(prices),np.std(prices))


