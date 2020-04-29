import boto3 
import json
import os
from pkg_resources import resource_filename


## Declare resources and clients: 
region_id = os.environ["REGION"]
client = boto3.client('pricing',region_name=region_id)
ec2client = boto3.client("ec2")


## TAKEN FROM: https://stackoverflow.com/questions/51673667/use-boto3-to-get-current-price-for-given-ec2-instance-type
## Filter definition: 
FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},'\
      '{{"Field": "operatingSystem", "Value": "{o}", "Type": "TERM_MATCH"}},'\
      '{{"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"}},'\
      '{{"Field": "instanceType", "Value": "{t}", "Type": "TERM_MATCH"}},'\
      '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},'\
      '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'
# Get current AWS price for an on-demand instance
def get_price(region, instance, os="Linux"):
    f = FLT.format(r=region, t=instance, o=os)
    data = client.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f))
    od = json.loads(data['PriceList'][0])['terms']['OnDemand']
    id1 = list(od)[0]
    id2 = list(od[id1]['priceDimensions'])[0]
    return float(od[id1]['priceDimensions'][id2]['pricePerUnit']['USD'])

# Translate region code to region name
def get_region_name(region_code):
    default_region = 'US East (N. Virginia)'
    endpoint_file = resource_filename('botocore', 'data/endpoints.json')
    try:
        with open(endpoint_file, 'r') as f:
            data = json.load(f)
        return data['partitions'][0]['regions'][region_code]['description']
    except IOError:
        return default_region

#### write one function that gets the price given the instance.

def price_instance(instance,os="Linux"):
    """
    """
    ##First determine if the instance is a spot instance or a standard instance. 
    if instance.spot_instance_request_id: 
        instance_type = "spot"
    else:
        instance_type = "standard"

    ## If it's a standard instance: 
    if instance_type == "standard":
        price = get_price(get_region_name(region_id),instance.instance_type,os = os)
    ## If it's a spot instance. 
    elif instance_type == "spot":
        price = float(ec2client.describe_spot_instance_requests(SpotInstanceRequestIds=[instance.spot_instance_request_id])["SpotInstanceRequests"][0]["ActualBlockHourlyPrice"]) 
    return price


