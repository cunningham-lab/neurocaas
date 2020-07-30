import os
import datetime
import json
import yaml

import boto3
from botocore.errorfactory import ClientError

#####from .config import REGION, LOGDIR, LOGFILE

# Boto3 Resources & Clients
s3_resource = boto3.resource('s3', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])


def mkdir(bucket, path, dirname):
    """ Makes new directory path in bucket
    :param bucket: s3 bucket object within which directory is being created
    :param path: string local path where directory is to be created
    :param dirname: string name of directory to be created
    :return: path to new directory
    """
    new_path = os.path.join(path, dirname, '')
    try:
        s3_client.head_object(Bucket=bucket, Key=new_path)
    except ClientError:
        s3_client.put_object(Bucket=bucket, Key=new_path)
    return new_path

def mkdir_reset(bucketname, path, dirname):
    """ Makes new directory path in bucket, if exists, wipes and recreates.
    :param bucketname: s3 bucket object within which directory is being created
    :param path: string local path where directory is to be created
    :param dirname: string name of directory to be created
    :return: path to new directory
    """
    new_path = os.path.join(path, dirname, '')
    try:
        s3_client.head_object(Bucket=bucketname, Key=new_path)
        s3_resource.Bucket(bucketname).objects.filter(Prefix=new_path).delete()
        s3_client.put_object(Bucket=bucketname, Key=new_path)
    except ClientError:
        s3_client.put_object(Bucket=bucketname, Key=new_path)
    return new_path

def ls(bucket, path):
    """ Get all objects with bucket as strings"""
    return [
        objname.key for objname in bucket.objects.filter(Prefix=path)
    ]
    
def ls_name(bucket_name, path):
    """ Get all objects with bucket as strings"""
    bucket = s3_resource.Bucket(bucket_name)
    return [
        objname.key for objname in bucket.objects.filter(Prefix=path)
    ]

def exists(bucket_name, path):
    """ checks if there is any data under the given (Prefix) path for the given bucket. """
    bucket = s3_resource.Bucket(bucket_name)
    objlist = [objname.key for objname in bucket.objects.filter(Prefix=path)]
    return len(objlist) >0

def cp(bucket_name,pathfrom,pathto): 
    """
    Implement a copy function from [pathfrom] to [pathto] within the same bucket. 
    inputs:
    bucket_name (str): the name of the bucket 
    pathfrom (str): the path from which to copy. Must include filename.
    pathto (str): the path to which we will copy. Must include filename. 
    """
    #s3_resource.Object(bucket_name,pathto).copy_from(CopySource = pathfrom)
    s3_resource.meta.client.copy({"Bucket":bucket_name,"Key":pathfrom},bucket_name,pathto)

def mv(bucket_name,pathfrom,pathto):
    """
    Implements a move function from [pathfrom] to [pathto] within the same bucket. 
    bucket_name (str): the name of the bucket 
    pathfrom (str): the path from which to copy. Must include filename.
    pathto (str): the path to which we will copy. Must include filename. 
    """
    cp(bucket_name,pathfrom,pathto)
    s3_resource.Object(bucket_name,pathfrom).delete()

def load_json(bucket_name, key):
    """ """
    print("entered load json")
    try:
        file_object = s3_resource.Object(bucket_name, key)
    except ClientError as e:
        print("printing clienterror")
        print(e.response["Error"])
        raise ClientError("S3 resource object declaration (and first aws api call) failed.")
    print("loaded file object.")
    try:
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(raw_content)
    except ValueError as ve:
        raise ValueError("[JOB TERMINATE REASON] Could not load config file. From parser: {}".format(ve))
    print("exited load json")

    ## Transfer type 
    return json_content 

def load_yaml(bucket_name, key):
    """ """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        yaml_content = yaml.safe_load(raw_content)
    except ValueError as ve:
        raise ValueError("[JOB TERMINATE REASON] Could not load config file. From parser: {}".format(ve))
    return yaml_content

def extract_files(bucket_name,prefix,ext = None):
    """
    Filters out the actual filenames being used to process data from the prefix that is given. 
    Inputs:
    bucket_name (str): the name of the s3 bucket. 
    prefix (str): the "folder name" that we care about 
    ext (optional): if provided, will filter filenames to be of the given extension. 
    """
    bucket = s3_resource.Bucket(bucket_name)
    objgen = bucket.objects.filter(Prefix = prefix)
    if ext is None:
        file_list = [obj.key for obj in objgen if obj.key[-1] != "/"]
    else:
        file_list = [obj.key for obj in objgen if obj.key[-1] != "/" and obj.key.split(".")[-1] == ext]

    return file_list 

def write_endfile(bucketname,resultpath):
    """
    Given the name of a bucket and a path to a result directory, writes an "end.txt" file to that bucket.
    """
    bucket = s3_resource.Bucket(bucketname)
    bucket.put_object(
            Key = os.path.join(resultpath,"process_results","end.txt"),
            Body = bytes("end of analysis marker".encode('UTF-8'))
            )


def write_active_monitorlog(bucketname,name,log):
    """
    Given the name of a bucket, writes an active monitoring log to that bucket.  
    inputs:
    bucketname (str): the name of the bucket that we are writing this log to. the path is already known.
    name (str): the name of the instance we are setting up monitoring for. 
    log (dict): the contents of the log file. 
    """
    bucket = s3_resource.Bucket(bucketname)
    bucket.put_object(
            Key = os.path.join("logs","active",name),
            Body = bytes(json.dumps(log,indent = 2).encode('UTF-8'))
            )

def delete_active_monitorlog(bucketname,name):
    """
    Given the name of a bucket, deletes an active monitoring log from that bucket.  
    inputs:
    bucketname (str): the name of the bucket that we are writing this log to. the path is already known.
    name (str): the name of the instance we are setting up monitoring for. 
    log (dict): the contents of the log file. 
    """
    Key = os.path.join("logs","active",name)
    s3_client.delete_object(Bucket = bucketname,Key = Key)

def update_monitorlog(bucketname,name,status,time):
    """
    Called by the monitor_updater lambda function. Updates existing log files. 
    """
    bucket = s3_resource.Bucket(bucketname)
    key = "logs/active/{}".format(name)
    print(key,"key")
    log_translate = {"running":"start","shutting-down":"end"}

    try:
        log = load_json(bucketname,key)
        log[log_translate[status]] = time
        bucket.put_object(
                Key = os.path.join("logs","active",name),
                Body = bytes(json.dumps(log,indent = 2).encode('UTF-8'))
                )
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            print("log {} does not exist".format(key))
            raise Exception("[JOB TERMINATE REASON] active log could not be found in folder.")
        else:
            print("unhandled exception.")
            raise Exception("[JOB TERMINATE REASON] Unhandled exception while retrieving data. Contact NeuroCAAS admin.")

    return log

    

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
        self.path = os.path.join(path, os.environ['LOGDIR'],'')#mkdir(bucket_name, path, LOGDIR)
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
            Key=os.path.join(self.path, os.environ['LOGFILE']),
            Body=encoded_text
        )

class JobLogger(Logger):
    """
    Updated utility class to write logs in format amenable to figure updating. 
    """
    def __init__(self,bucket_name,path):
        self.bucket = s3_resource.Bucket(bucket_name) 
        self.bucket_name = bucket_name
        self.path = os.path.join(path, os.environ['LOGDIR'],"certificate.txt")#mkdir(bucket_name, path, LOGDIR)
        ## Stupid, fix this TODO
        self.basepath = path
        ## Declare the object you will write to: 
        self.writeobj = s3_resource.Object(bucket_name,self.path)
        self._logs = []
        self._datasets = {}
        self._config = {}
        self._struct = {"logs":"no logs","datasets":"data not loaded","config":"config not loaded"}

    def append_lambdalog(self,string):
        """
        Unambiguously named wrapper for append. 
        Inputs: 
        string: the string to append to the lambda log. 
        """
        self.append(string)

    def initialize_datasets_dev(self,dataset,instanceid,commandid):
        """
        Initialize datasets by assigning to each a dictionary specifying instance data will be run on, command id, status, job description, reason, most recent output. 
        Inputs:
        dataset: the path to the data *file* analyzed by the instance. 
        instanceid (str): the string specifying what instance we will run analysis on. 
        commandid (str): the string specifying what the command id corresonding to this instance is. 
        """
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","input":dataset,"instance":instanceid,"command":commandid}
        ##TODO: check that these instances and commands exist. 
        self._datasets[dataset] = template_dict
        dataset_basename = os.path.basename(dataset)
        datapath = os.path.join(self.basepath, os.environ['LOGDIR'],"DATASET_NAME:"+dataset_basename+"_STATUS.txt")#mkdir(bucket_name, path, LOGDIR)
        dataobj = s3_resource.Object(self.bucket_name,datapath)
        dataobj.put(Body = (bytes(json.dumps(template_dict).encode("UTF-8"))))

    def initialize_datasets(self,dataset,instanceid,commandid):
        """
        Initialize datasets by assigning to each a dictionary specifying instance data will be run on, command id, status, job description, reason, most recent output. 
        Inputs:
        dataset: the path to the data *file* analyzed by the instance. 
        instanceid (str): the string specifying what instance we will run analysis on. 
        commandid (str): the string specifying what the command id corresonding to this instance is. 
        """
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","instance":instanceid,"command":commandid}
        ##TODO: check that these instances and commands exist. 
        self._datasets[dataset] = template_dict
        ## Additionally (later substitute), write these datasets to their own objects.`

    def assign_config(self,configpath):
        """
        Configuration assignment. Includes version of config file .
        Inputs: 
        configpath (str): path to config file
        """
        self._config['name'] = configpath # TODO Turn on versioning for user buckets so we can trace configs. 

    def update(self):
        """
        Updates the struct object. 
        """
        self._struct['logs'] = self._logs
        self._struct['datasets'] = self._datasets
        self._struct['config'] = self._config

    def write(self):
        """ 
        Updates the struct object, and writes the resulting dictionary.  
        """
        self.update()
        self.writeobj.put(Body = (bytes(json.dumps(self._struct).encode("UTF-8"))))
        

class JobLogger_demo(Logger):
    """
    Updated utility class to write logs in format amenable to figure updating. Updated for cosyne EPI demo to write only clean logs to s3 certificate.txt  
    """
    def __init__(self,bucket_name,path):
        self.bucket = s3_resource.Bucket(bucket_name) 
        self.bucket_name = bucket_name
        self.path = os.path.join(path, os.environ['LOGDIR'],"certificate.txt")#mkdir(bucket_name, path, LOGDIR)
        ## Stupid, fix this TODO
        self.basepath = path
        ## Declare the object you will write to: 
        self.writeobj = s3_resource.Object(bucket_name,self.path)
        self.basetime = datetime.datetime.now()
        self._logs = []
        self._datasets = {}
        self._config = {}
        self._struct = {"logs":"no logs","datasets":"data not loaded","config":"config not loaded"}

    def append_lambdalog(self,string):
        """
        Unambiguously named wrapper for append. 
        Inputs: 
        string: the string to append to the lambda log. 
        """
        self.append(string)

    def initialize_datasets_dev(self,dataset,instanceid,commandid):
        """
        Initialize datasets by assigning to each a dictionary specifying instance data will be run on, command id, status, job description, reason, most recent output. 
        Inputs:
        dataset: the path to the data *file* analyzed by the instance. 
        instanceid (str): the string specifying what instance we will run analysis on. 
        commandid (str): the string specifying what the command id corresonding to this instance is. 
        """
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","input":dataset,"instance":instanceid,"command":commandid}
        ##TODO: check that these instances and commands exist. 
        self._datasets[dataset] = template_dict
        dataset_basename = os.path.basename(dataset)
        datapath = os.path.join(self.basepath, os.environ['LOGDIR'],"DATASET_NAME:"+dataset_basename+"_STATUS.txt")#mkdir(bucket_name, path, LOGDIR)
        dataobj = s3_resource.Object(self.bucket_name,datapath)
        dataobj.put(Body = (bytes(json.dumps(template_dict).encode("UTF-8"))))

    def initialize_datasets(self,dataset,instanceid,commandid):
        """
        Initialize datasets by assigning to each a dictionary specifying instance data will be run on, command id, status, job description, reason, most recent output. 
        Inputs:
        dataset: the path to the data *file* analyzed by the instance. 
        instanceid (str): the string specifying what instance we will run analysis on. 
        commandid (str): the string specifying what the command id corresonding to this instance is. 
        """
        template_dict = {"status":"INITIALIZING","reason":"NONE","stdout":"not given yet","stderr":"not given yet","instance":instanceid,"command":commandid}
        ##TODO: check that these instances and commands exist. 
        self._datasets[dataset] = template_dict
        ## Additionally (later substitute), write these datasets to their own objects.`

    def assign_config(self,configpath):
        """
        Configuration assignment. Includes version of config file .
        Inputs: 
        configpath (str): path to config file
        """
        self._config['name'] = configpath # TODO Turn on versioning for user buckets so we can trace configs. 

    def update(self):
        """
        Updates the struct object. 
        """
        self._struct['logs'] = self._logs
        self._struct['datasets'] = self._datasets
        self._struct['config'] = self._config

    def append(self, string):
        """ """
        self._logs.append(
                string + "\t [+{}]".format(str(datetime.datetime.now()-self.basetime)[:-4]) 
        )
    def printlatest(self):
        """ print the most recent item appended to logs. """
        print(self._logs[-1])

    def write(self):
        """ 
        Updates the struct object, and writes the resulting dictionary.  
        """
        self.update()
        encoded_text = "\n".join(self._logs).encode("utf-8")
        #self.writeobj.put(Body = (bytes(json.dumps("\n".join(self._logs)).encode("UTF-8"))))
        self.writeobj.put(Body = encoded_text)

    def initialize_monitor(self):
        """
        To be run last, after all processing is done. Gets the information about acquired datasets and uses them to start up a monitor  
        """
        dataset_template = "DATANAME: {n} | STATUS: {s} | TIME: {t} | LAST COMMAND: {r}"
        datasets_init = [dataset_template.format(n = dset, s = self._datasets[dset]["status"], t = str(datetime.datetime.now()), r = self._datasets[dset]["reason"]) for dset in self._datasets]
        template_start = ["PER ENVIRONMENT MONITORING:","================"]
        #template_end = ["================","Once jobs start, these logs will be updated regularly.","DATANAME: the path to the dataset being analyzed in an immutable analysis environment.","STATUS: the status of the script running analysis. Can be INITIALIZING, IN PROGRESS, SUCCESS, or FAILED", "TIME: The time when this log was last updated.", "LAST COMMAND: The last command that ran successfully.","For more information, see DATASET_NAME: files for stdout and stderr output.","++++++++++++++++++ ","JOB MONITOR LOG"]
        template_end = ["================","Once jobs start, these logs will be updated regularly. Allow some time [~1 minute] after all jobs finish for results to appear.","For more information, see DATASET_NAME: files for stdout and stderr output."," ","++++++++++++++++++"," ","JOB MANAGER SETUP LOG:"]
        full_log_list = template_start+datasets_init+template_end
        full_log_init = "\n".join(full_log_list+self._logs).encode("utf-8")
        self.writeobj.put(Body = full_log_init)

#def check_for_config(upload, config):
#    """ """
#    contents = ls(bucket=bucket, path=local_path)
#    assert (os.path.joing(local_path, CONFIG) in contents), MISSING_CONFIG_ERROR
