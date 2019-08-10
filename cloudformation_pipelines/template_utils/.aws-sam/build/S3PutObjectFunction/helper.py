## Module contianing all custom resources. 
import os 
import json 
import traceback
from submit_start import respond
try:
    import lambda_utils.config as config
    import lambda_utils.s3
    import lambda_utils.ssm
    import lambda_utils.ec2
    import lambda_utils.serverless
except Exception as e:
    error = str(e)
    stacktrace = json.dumps(traceback.format_exc())
    message = "Exception: " + error + "  Stacktrace: " + stacktrace
    err = {"message": message}
    print(err)

def handler_mkdir(event,context):
    responseStatus = "SUCCESS"
    responsedata = {}
    ## Get properties: 
    try:
        props = event['ResourceProperties']
        ## Get individual properties: 
        bucket = props['BucketName']
        path = props['Path']
        dirname = props['DirName']
        ## Now plug in:
        lambda_utils.s3.mkdir(bucket,path,dirname)
        lamba_utils.serverless.sendResponse(event,context,responseStatus,responseData)

    except Exception as e:
        error = str(e)
        lambda_utils.serverless.sendResponse(event,context,responseStatus,{"data":traceback.format_exc()})
        #stacktrace = json.dumps(traceback.format_exc())
        #message = "Exception: " + error + "  Stacktrace: " + stacktrace
        #err = {"message": message}
        #print(err)


