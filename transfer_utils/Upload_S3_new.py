'''
Script to upload a video to the relevant amazon S3 bucket 
'''
import os
import sys
import boto3 
from boto3.s3.transfer import S3Transfer 
import botocore 
import threading
from Interface_S3 import upload 

if __name__ == "__main__":
    foldername = sys.argv[1]
    keypath = sys.argv[2]
    bucket_name = 'froemkelab.videodata'
    
    print(foldername,keypath)
    ## Only reupload analysis results:
    analysis_results = [os.path.join(dp, f) for dp, dn, fn in os.walk(foldername) for f in fn]
    print(analysis_results)
    for filename in analysis_results:
        if filename.split('.')[-1] == 'png':
            ## give the file the right key prefix: 
            key = keypath+'/'+filename 
            print(key,foldername+'/'+filename)
            upload(bucket_name,filename,'./',key)






