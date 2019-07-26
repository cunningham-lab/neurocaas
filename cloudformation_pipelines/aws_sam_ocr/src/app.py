from __future__ import print_function
import boto3
from decimal import Decimal
import json
import urllib
import uuid
import datetime
import time
import os

rekognition_client = boto3.client('rekognition')
s3_client = boto3.client('s3')
dynamo_client = boto3.client('dynamodb')

# Get the table name from the Lambda Environment Variable
table_name = os.environ['TABLE_NAME']

# --------------- Helper Functions to call Rekognition APIs ------------------

def detect_text(bucket, key):
    response = rekognition_client.detect_text(Image={"S3Object": {"Bucket": bucket, "Name": key}})
    return response

def detect_labels(bucket, key):
    response = rekognition_client.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}})
    return response

# --------------- Main handler ------------------
def lambda_handler(event, context):
    '''
    Uses Rekognition APIs to detect text and labels for objects uploaded to S3
    and store the content in DynamoDB.
    '''
    # Log the the received event locally.
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event.
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    try:
        # Call rekognition DetectText API to detect Text in S3 object.
        response = detect_text(bucket, key)
        textDetections = [text['DetectedText'] for text in response['TextDetections']]

        # Log text detected.
        # for text in textDetections:
        #    print (text)

        # Call rekognition DetectLabels API to detect labels in S3 object.
        response = detect_labels(bucket, key)
        labels = [{label_prediction['Name']: Decimal(str(label_prediction['Confidence']))} for label_prediction in response['Labels']]
        
        # Log labels detected.
        # for label in labels:
        #    print (label)

        # Get the timestamp.
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

        # Write to DynamoDB.
        table = boto3.resource('dynamodb').Table(table_name)
        item={'id':key, 'DateTime':timestamp, 'Labels':labels, 'Text':textDetections}
        table.put_item(Item=item)

        return 'Success'
    except Exception as e:
        print("Error processing object {} from bucket {}. Event {}".format(key, bucket, json.dumps(event, indent=2)))
        raise e
