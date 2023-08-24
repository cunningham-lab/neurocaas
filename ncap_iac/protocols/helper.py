## Module containing all custom resources. 
try:
    import os 
    import json 
    import traceback
    from submit_start import respond
    import utilsparam.s3
    import utilsparam.ssm
    import utilsparam.ec2
    import utilsparam.serverless
except Exception as e:
    try:
        ## Most likely this comes from pytest and relative imports.
        from ncap_iac.protocols.utilsparam import s3 as utilsparams3
        from ncap_iac.protocols.utilsparam import ssm as utilsparamssm
        from ncap_iac.protocols.utilsparam import ec2 as utilsparamec2
        from ncap_iac.protocols.utilsparam import events as utilsparamevents
        from ncap_iac.protocols.utilsparam import pricing as utilsparampricing
    except:
        error = str(e)
        stacktrace = json.dumps(traceback.format_exc())
        message = "Exception: " + error + "  Stacktrace: " + stacktrace
        err = {"message": message}
        print(err)

def handler_mkdir(event,context):
    """The function corresponding to a cloudformation lambda-backed custom resource that creates new directories in S3 buckets. 

    :param event: standard lambda event payload documenting the cloudformation event that triggered this lambda function.  
    :type event: dict
    :param context: additional information about the cloudformation event that triggered this lambda function, not used but required in lambda signature.  
    :type context: dict
    :raises Exception: we have a catch-all exception that will correctly send back a "FAILED" signal to cloudformation. This is critical, as without it the entire cloudformation build process can hang indefinitely.  
    :return: None 
    :rtype: None
    """
    responseData = {}
    print(event,"event")
    print(context,"context")
    ## Get properties: 
    try:
        if event['RequestType'] == 'Create':
            props = event['ResourceProperties']
            ## Get individual properties: 
            bucket = props['BucketName']
            path = props['Path']
            dirname = props['DirName']
            ## Now plug in:
            utilsparam.s3.mkdir(bucket,path,dirname)
        else:
            print(event['RequestType'])
        utilsparam.serverless.sendResponse(event,context,"SUCCESS",responseData)

    except Exception as e:
        error = str(e)
        utilsparam.serverless.sendResponse(event,context,"FAILED",{"data":traceback.format_exc()})
        #stacktrace = json.dumps(traceback.format_exc())
        #message = "Exception: " + error + "  Stacktrace: " + stacktrace
        #err = {"message": message}
        #print(err)

def handler_deldir(event, context):
    """The function corresponding to a cloudformation lambda-backed custom resource that deletes the contents of one directory in an S3 bucket.  Necessary to delete folders in other buckets when adding and deleting users from other buckets.  

    :param event: standard lambda event payload documenting the cloudformation event that triggered this lambda function.  
    :type event: dict
    :param context: additional information about the cloudformation event that triggered this lambda function, not used but required in lambda signature.  
    :type context: dict
    :raises Exception: we have a catch-all exception that will correctly send back a "FAILED" signal to cloudformation. This is critical, as without it the entire cloudformation build process can hang indefinitely.  
    :return: None 
    :rtype: None
    """
    responseData = {}
    print(event,"event")
    print(context,"context")
    try:
        if event['RequestType'] == 'Delete':
            props = event['ResourceProperties']
            ## Get individual properties: 
            bucket = props['BucketName']
            path = props['Path']
            dirname = props["DirName"]
            ## Important, we want to delete the directory, not its parents. 
            fullpath = os.path.join(path,dirname)
            utilsparam.s3.deldir(bucket,fullpath)

        utilsparam.serverless.sendResponse(event,context,"SUCCESS",responseData)
    except Exception as e:
        error = str(e)
        utilsparam.serverless.sendResponse(event,context,"FAILED",{"data":traceback.format_exc()})

def handler_delbucket(event, context):
    """The function corresponding to a cloudformation lambda-backed custom resource that deletes the whole contents of an S3 bucket. Necessary to delete s3 buckets when deleting cloudformation stacks. 

    :param event: standard lambda event payload documenting the cloudformation event that triggered this lambda function.  
    :type event: dict
    :param context: additional information about the cloudformation event that triggered this lambda function, not used but required in lambda signature.  
    :type context: dict
    :raises Exception: we have a catch-all exception that will correctly send back a "FAILED" signal to cloudformation. This is critical, as without it the entire cloudformation build process can hang indefinitely.  
    :return: None 
    :rtype: None
    """
    responseData = {}
    print(event,"event")
    print(context,"context")
    try:
        if event['RequestType'] == 'Delete':
            bucket = event['ResourceProperties']['BucketName']
            s3 = utilsparam.s3.delbucket(bucket)

        utilsparam.serverless.sendResponse(event,context,"SUCCESS",responseData)
    except Exception as e:
        error = str(e)
        utilsparam.serverless.sendResponse(event,context,"FAILED",{"data":traceback.format_exc()})


