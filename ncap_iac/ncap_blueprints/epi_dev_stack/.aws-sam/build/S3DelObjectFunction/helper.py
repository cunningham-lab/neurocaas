## Module contianing all custom resources. 
import os 
import json 
import traceback
from submit_start import respond
try:
    import utils.s3
    import utils.ssm
    import utils.ec2
    import utils.serverless
except Exception as e:
    error = str(e)
    stacktrace = json.dumps(traceback.format_exc())
    message = "Exception: " + error + "  Stacktrace: " + stacktrace
    err = {"message": message}
    print(err)

def handler_mkdir(event,context):
    responseData = {}
    ## Get properties: 
    try:
        if event['RequestType'] in ['Create','Update']:
            print(event['RequestType'])
            props = event['ResourceProperties']
            ## Get individual properties: 
            bucket = props['BucketName']
            path = props['Path']
            dirname = props['DirName']
            ## Now plug in:
            utils.s3.mkdir(bucket,path,dirname)
        else:
            print(event['RequestType'])
        utils.serverless.sendResponse(event,context,"SUCCESS",responseData)

    except Exception as e:
        error = str(e)
        utils.serverless.sendResponse(event,context,"FAILED",{"data":traceback.format_exc()})
        #stacktrace = json.dumps(traceback.format_exc())
        #message = "Exception: " + error + "  Stacktrace: " + stacktrace
        #err = {"message": message}
        #print(err)

def handler_deldir(event, context):
    responseData = {}
    try:
        if event['RequestType'] == 'Delete':
            bucket = event['ResourceProperties']['BucketName']
            print(event,'event request type')
            s3 = utils.s3.s3_resource
            bucket = s3.Bucket(bucket)
            for obj in bucket.objects.all():
                print(obj.key,'keys')
                s3.Object(bucket.name, obj.key).delete()

        utils.serverless.sendResponse(event,context,"SUCCESS",responseData)
    except Exception as e:
        error = str(e)
        utils.serverless.sendResponse(event,context,"FAILED",{"data":traceback.format_exc()})

