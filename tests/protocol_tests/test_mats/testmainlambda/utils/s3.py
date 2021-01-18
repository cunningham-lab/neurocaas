import os
import datetime
import json

import boto3
from botocore.errorfactory import ClientError

from .config import REGION, LOGDIR, LOGFILE

# Boto3 Resources & Clients
s3_resource = boto3.resource('s3')
s3_client = boto3.client('s3', region_name=REGION)


def mkdir(bucket, path, dirname):
    """ Makes new directory path in bucket
    :param bucket: s3 bucket object within which directory is being created
    :type bucket: boto3 bucket object
    :param path: string local path where directory is to be created
    :type path: string
    :param dirname: string name of directory to be created
    :type dirname: string
    :return: path to new directory
    :rtype: string
    """
    new_path = os.path.join(path, dirname, '')
    try:
        s3_client.head_object(Bucket=bucket, Key=new_path)
    except ClientError:
        s3_client.put_object(Bucket=bucket, Key=new_path)
    return new_path

def deldir(bucket,path):
    """ Deletes all objects under directory path (and the directory itself in bucket. )
    :param bucket: s3 bucket object within which directory is being deleted
    :type bucket: boto3 bucket object
    :param path: string local path where directory is to be deleted
    :type path: string
    """
    bucket = s3_resource.Bucket(bucket)
    for obj in bucket.objects.filter(Prefix=path):
        s3.Object(bucket.name, obj.key).delete()

def delbucket(bucket):
    """ Deletes all objects in a bucket.
    :param bucket: s3 bucket object within which directory is being deleted
    :type bucket: boto3 bucket object
    """

def ls(bucket, path):
    """ Get all objects with bucket as strings"""
    return [
        objname.key for objname in bucket.objects.filter(Prefix=path)
    ]


def load_json(bucket_name, key):
    """ """
    file_object = s3_resource.Object(bucket_name, key)
    raw_content = file_object.get()['Body'].read().decode('utf-8')
    json_content = json.loads(raw_content)
    return json_content 

class WriteMetric():
    """ Utility Class For Benchmarking performance """

    def __init__(self, bucket_name, path,instance,time):
        """ """
        self.bucket = s3_resource.Bucket(bucket_name) 
        self.instance = instance
        self.path = os.path.join(path, instance, '')#mkdir(bucket_name, path,instance)
        self.time = time
        self._logs = []

    def append(self, string):
        """ """
        self._logs.append(
            self.time + ": " + string + "\n"
        )

    def write(self):
        """ """
        encoded_text = "\n".join(self._logs).encode("utf-8")
        self.bucket.put_object(
            Key=os.path.join(self.path,self.time+'.txt'),
            Body=encoded_text
        )

class Logger():
    """ Utility Class For Collection Logs & Writing To S3 """

    def __init__(self, bucket_name, path):
        """ """
        self.bucket = s3_resource.Bucket(bucket_name) 
        self.path = os.path.join(bucket_name, path, LOGDIR)#mkdir(bucket_name, path, LOGDIR)
        self._logs = []

    def append(self, string):
        """ """
        self._logs.append(
            str(datetime.datetime.now()) + ": " + string + "\n"
        )

    def write(self):
        """ """
        encoded_text = "\n".join(self._logs).encode("utf-8")
        self.bucket.put_object(
            Key=os.path.join(self.path, LOGFILE),
            Body=encoded_text
        )

#def check_for_config(upload, config):
#    """ """
#    contents = ls(bucket=bucket, path=local_path)
#    assert (os.path.joing(local_path, CONFIG) in contents), MISSING_CONFIG_ERROR
