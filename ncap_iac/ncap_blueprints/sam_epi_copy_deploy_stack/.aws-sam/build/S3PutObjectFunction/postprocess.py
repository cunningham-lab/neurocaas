import json
import os
import boto3
import numpy as np
import pandas as pd
import csv

s3_resource = boto3.resource("s3")

## Function to count the number of datasets in a given job. Right now, counts based
## on the number of generated Dataset status files, we could think of alternatives. 
def count_datasets(bucket,jobpath):
    """
    Assumes that the given path points to the job path of a given analysis. 
    Looks within the log path of that same analysis, and counts the number of dataset files
    generated for it. 
    Inputs: 
    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
    jobpath: (str) the path of the job directory for a particular analysis. 
    """
    logsdir = os.path.join(jobpath,"logs/")
    ## TODO: make this reference the environment variable indicating the right log directory. 
    ## Now look within for datasets with a certain prefix: 
    all_logs = [i.key for i in bucket.objects.filter(Prefix=logsdir)]
    ## Filter this by the DATASET_NAME prefix:
    dataset_logs = [l for l in all_logs if l.split(logsdir)[-1].startswith("DATASET_NAME")]
    return dataset_logs
    
## Now figure out how many of the dataset logs indicate success: 
def check_status(bucket, dataset_logs):
    """
    Checks for the status ["SUCCESS", "IN PROGRESS", "FAILED"] of the individual jobs that we look at. 
    inputs: 
    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
    dataset_logs: (list) A list of strings giving the full paths to the dataset status files.
    ##TODO: Check that 1024 is enough bandwidth for this function. 
    outputs:
    (boolean): boolean giving the status of each job that was found. 
    """
    statuses = []
    for log in dataset_logs:
        object = bucket.Object(log)
        f = object.get()["Body"]
        obj = json.load(f)
        statuses.append(obj["status"] == "SUCCESS")
        
    return statuses

def check_csvs(bucket,jobpath):
    """
    Checks if the csv output that we expect from all datasets being finished are in existence. 
    inputs:
    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
    jobpath: (string): a string giving the s3 path to the job folder we care about. 
    returns:
    (list): a list of strings giving the path to each opt_data.csv that has been generated thus far. 
    """
    ## First match on all of the D4 outputs TODO: route from a subdirectory later. 
    prefix_string = "per_hp"
    all_logs = [i.key for i in bucket.objects.filter(Prefix=os.path.join(jobpath,prefix_string)) if i.key.endswith("opt_data.csv")]
    return all_logs

#def update_logs(bucket,jobpath,all_logs):
#    """
#    Takes the list of existing csv logs, and updates the certificate.txt fiile found in the logs directory. 
#    inputs:
#    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
#    jobpath: (string): a string giving the s3 path to the job folder we care about. 
#    all_logs: (list): a list of the strings giving the path to each opt_data.csv that has been generated thus far. 
#    """
#    ## TODO: for right now, we're going to hardcode in the mapping from random seeds to parameter values. 
#    mapping_dict = {
#            "D4_C3_L2_U21_rs1":1,
#            "D4_C3_L1_U23_rs1":2,
#            "D4_C3_L1_U18_rs1":3,
#            "D4_C3_L1_U24_rs1":4,
#            "D4_C3_L2_U24_rs1":5,
#            "D4_C3_L1_U19_rs1":6,
#            "D4_C3_L2_U10_rs1":7,
#            "D4_C3_L2_U14_rs1":8,
#            "D4_C3_L1_U22_rs1":9,
#            "D4_C3_L2_U23_rs1":10,
#            } 
#
#    ## Now get the certificate: 
#    certificatepath = os.path.join(jobpath,"logs","certificate.txt")
#    certificate = bucket.Object(certificatepath)
#    certificatefile = certificate.get()["Body"].read().decode('utf-8')
#    certificatelist = certificatefile.split("\n")
#
#    ## Now get the status messages that relate to individual analyses:  
#    for line in certificatelist: 
#        dataset_val = re.findall('^Starting analysis ([0-9]+) with parameter set$', line)
#        print(line,dataset_val,"dasf")
        


## Now a function to get the data from each folder: 
def extract_csvs(bucket,csvpath):
    """
    A function to extract the relevant information from csvs given a path. 
    inputs: 
    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
    csvpath: (str) string giving path to the s3 object. 
    """
    #todo: replace with pandas read. 
    opts_file = bucket.Object(csvpath)
    f = opts_file.get()["Body"].read().decode('utf-8')
    # with open(f,'rb') as csvfile:
    #data = csv.DictReader(f)
    rows = f.split('\n')
    all_entropy = []
    for row in rows[1:-1]:
        entropy = float([entry for entry in row.split(',')][3])
        all_entropy.append(entropy)
    return np.array(all_entropy)#[print(d) for d in data]
    
def extract_pd(bucket,csvpath):
    """
    A function to extract the relevant information into a pandas array from csvs given a path. First saves into /tmp 
    inputs: 
    bucket: (boto3 obj): an s3 boto3 resource object declaring the bucket this comes from. 
    csvpath: (str) string giving path to the s3 object. 
    returns: 
    (pandas array): array of optimization results. 
    """
    #todo: replace with pandas read. 
    local_filename = os.path.join("/tmp",os.path.basename(csvpath))
    bucket.download_file(csvpath,local_filename)
    #opts_file = bucket.Object(csvpath)
    
    f = pd.read_csv(local_filename)
    #f = opts_file.get()["Body"].read().decode('utf-8')
    # with open(f,'rb') as csvfile:
    #data = csv.DictReader(f)
    #rows = f.split('\n')
    #all_entropy = []
    #for row in rows[1:-1]:
    #    entropy = float([entry for entry in row.split(',')][3])
    #    all_entropy.append(entropy)
    #return np.array(all_entropy)#[print(d) for d in data]
    return f

def epipostprocess(event, context):
    ## First get out the path to the job that you care about. 
    
    for record in event['Records']:
        time = record['eventTime']
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
    ## Declare the bucket 
    bucket = s3_resource.Bucket(bucket_name)
    
    ## Now key should be altered find the path two dirs up.    
    jobpath = os.path.dirname(os.path.dirname(os.path.dirname(key)))
    jobpath_corrected = ':'.join(jobpath.split("%3A"))

    
    ## Now get the name of the individual dataset logs involved 
    dataset_logs = count_datasets(bucket,jobpath_corrected)
    print(dataset_logs,"these are the dataset logs")
    
    ## We can then recover the number of datasets we require in order to proceed with analysis.
    num_analyzed = len(dataset_logs)

    ## Now check if we have enough passing datasets: 
    passed = check_status(bucket,dataset_logs)
    
    ## Now check that we have enough of the opt_csv files that we want. 
    ## Match on the filename prefix. 
    results_existing = check_csvs(bucket,jobpath_corrected)

    ## Now read and modify the certificate file to reflect the number of datasets that have completed processing!  
    #update_logs(bucket,jobpath_corrected,results_existing)
    

    ## We have two conditions we care about: 
    ## if np.all(passed) and len(results_existing) == num_analyzed:
    ## TODO: for the demo right now, we only care about the second one. status messages get stuck as in progress sometimes. 
    if len(results_existing) == num_analyzed:
        message = "analyzing, statuses are success: {}, csv exists for {} of {}".format(passed,len(results_existing),num_analyzed)
        ## If criteria are satisfied, we execute Sean's hp search code.
        max_H = np.NINF
        max_H_opt_path = None
        max_H_opt = None
        for csv_path in results_existing:
            opt_data = extract_pd(bucket,csv_path)
            conv_inds = opt_data["converged"] == True
            #if (sum(conv_inds) == 0):
            #    continue
            Hs = opt_data[conv_inds]['H']
            max_H_i = Hs.max()
            ###################################
            if max_H_i > max_H:
                max_H = max_H_i
                max_H_opt_path = os.path.dirname(csv_path)
                max_H_opt = os.path.basename(max_H_opt_path)

        ## Now we recopy the best data to a separate directory called hp_optimum:
        search_outputdir = os.path.join(jobpath_corrected,"hp_optimum")
        print(max_H_opt_path,'max h opt path')
        print(search_outputdir,'max h opt path')
        print(os.path.join(bucket_name,max_H_opt_path,"opt_data.csv"))
        s3_resource.Object(bucket_name,os.path.join(search_outputdir,"opt_data.csv")).copy_from(CopySource={"Bucket":bucket_name,"Key":os.path.join(max_H_opt_path,"opt_data.csv")})
        s3_resource.Object(bucket_name,os.path.join(search_outputdir,"epi_opt.mp4")).copy_from(CopySource=os.path.join(bucket_name,max_H_opt_path,"epi_opt.mp4"))
        
        results_msg ="Best opt was {}s with entropy {}.2E.".format(max_H_opt, max_H) 
            
    else: 
        message = "not analyzing, statuses are success: {}, csv exists for {} of {}".format(passed,len(results_existing),num_analyzed)
    
        results_msg = "not yet detected. "
    print(results_msg)
    print(message)
    
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('message: {}, data: {}'.format(message,results_msg))

    }
