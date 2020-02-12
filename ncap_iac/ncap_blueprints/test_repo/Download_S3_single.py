'''
Script to download videos from the relevant amazon S3 bucket into a temporary diretory. Old version just took parameter for source bucket "folder". New version (this one) takes additional parameter giving destination. This new version is more barebones, in that it does not ask for the config file (see commented out). This version additionally takes multiple flags for file endings, as we need both the mp4 and the h5 file to do processing here.  
'''
import os
import sys
import boto3 
from boto3.s3.transfer import S3Transfer 
import botocore 
import threading
from Interface_S3 import download

if __name__ == "__main__":
    key = sys.argv[1]
    bucket_name = sys.argv[2]
    targetdir = sys.argv[3]
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket_name)
    for object in my_bucket.objects.filter(Prefix = key):
        print(object.key,'the key we would see')
    download(bucket_name,key,tempdir = targetdir)
    ### Get the config file too (annoying):
    ## First get the path to the directory directly above: 
    #key_split = prekey.split('/')[:-1]
    #main_direct = os.path.join(*key_split)
    #configkey = main_direct+'/'+'config.py'
    #download(bucket_name,configkey,tempdir = './auxvolume/temp_videofolder/')





