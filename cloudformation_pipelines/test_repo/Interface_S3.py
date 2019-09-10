'''
Script to download a video from the relevant amazon S3 bucket into a temporary diretory. 
'''
import sys
import os
import boto3 
from boto3.s3.transfer import S3Transfer 
import botocore 
import threading
## from https://stackoverflow.com/questions/41827963/track-download-progress-of-s3-file-using-boto3-and-callbacks
class ProgressPercentage_d(object):
    def __init__(self,client,BUCKET,KEY):
        self._filename = KEY
        self._size = client.head_object(Bucket=BUCKET,Key=KEY)['ContentLength']
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self,bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round((self._seen_so_far/self._size)*100,2)
            sys.stdout.write(
                        "\r%s  %s / %s  (%.2f%%)" % (
                        self._filename, self._seen_so_far, self._size,
                        percentage))
            sys.stdout.flush()

class ProgressPercentage_u(object):
    def __init__(self,FILEPATH):
        self._filename = FILEPATH
        self._size = float(os.path.getsize(FILEPATH)) 
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self,bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round((self._seen_so_far/self._size)*100,2)
            sys.stdout.write(
                        "\r%s  %s / %s  (%.2f%%)" % (
                        self._filename, self._seen_so_far, self._size,
                        percentage))
            sys.stdout.flush()

def download(BUCKET_NAME,KEY,tempdir = '../vmnt/tmp_videos/'):

    s3 = boto3.resource('s3')
    # for the purposes of temporary storage, we only use the last bit of the name as an indentifier: 
    USEKEY = KEY.split('/')[-1]

    try:
        transfer = S3Transfer(boto3.client('s3','us-east-1')) 
        progress = ProgressPercentage_d(transfer._manager._client,BUCKET_NAME,KEY)
        transfer.download_file(BUCKET_NAME,KEY,tempdir+USEKEY,callback = progress)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
            raise
        else:
            raise
def upload(BUCKET_NAME,FILENAME,FILEPATH,KEYPATH):
    s3 = boto3.resource('s3')
    
    try:
        transfer = S3Transfer(boto3.client('s3','us-east-1'))
        progress = ProgressPercentage_u(FILEPATH+FILENAME)
        transfer.upload_file(FILEPATH+FILENAME,BUCKET_NAME,KEYPATH,callback = progress)

    except OSError as e:
        print("The file does not exist.")
        print(e)


if __name__ == "__main__":
    action = sys.argv[1]

    bucket_name = 'froemkelab.videodata'
    if action == 'download':
        key = sys.argv[2]
        download(bucket_name,key)
    elif action == 'upload':
        filename = sys.argv[2]
        keypath = sys.argv[3]
        upload(bucket_name,filename,keypath)
    else:
        print('not a valid action, please choose "upload" or "download"')






