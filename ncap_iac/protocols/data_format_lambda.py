import json
import sys
import boto3
import pandas as pd
import yaml
import collections
import os

#call this once per job created

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    #copies frame jpegs from labeling job input folder
    data_bucket = event["Records"][0]["s3"]["bucket"]["name"]
    seqlabel_path = event["Records"][0]["s3"]["object"]['key']
    print(seqlabel_path)
    path_split_indices = []
    start = 0
    while seqlabel_path.find('/', start) != -1:
        idx = seqlabel_path.find('/', start)
        path_split_indices.append(idx)
        start = idx + 1
    neurocaas_job_output_directory = seqlabel_path[:path_split_indices[3] + 1]
    label_job_output_directory = seqlabel_path[:path_split_indices[4] + 1]
    path_from_label_job_direct_to_seqlabel = seqlabel_path[path_split_indices[4] + 1:]
    group_name = seqlabel_path.split('/')[0]
    neurocaas_job_name = seqlabel_path.split('/')[2]
    label_job_name = seqlabel_path.split('/')[4]
    neurocaas_job_config_file = yaml.load(s3.get_object(Bucket = data_bucket, Key = group_name + '/configs/' + label_job_name + '/config.yaml')["Body"].read()) #assumes config.yaml, talk to taiga about this, maybe just assume finaldatabucket stays constant and read config.yaml file there
    print(neurocaas_job_config_file)
    parts = neurocaas_job_config_file["bodyparts"]
    if "prevneurocaasjobID" in neurocaas_job_config_file.keys():
      prevneurocaasjobnum = neurocaas_job_config_file["prevneurocaasjobID"]
    else:
      prevneurocaasjobnum = None
    labeling_job_info = neurocaas_job_config_file["jobs_info"][label_job_name]
    dataset_name = labeling_job_info["datasetname"]
    labeled_datasetname = labeling_job_info["labeled_datasetname"]
    bucket_contents = s3.list_objects(Bucket = data_bucket, Prefix = group_name + '/inputs/' + label_job_name + '/' + dataset_name + '/')
    objects = bucket_contents['Contents']
    print(len(objects))
    for bucket_object in objects:
        s3.copy_object(Bucket = data_bucket, CopySource = {"Bucket" : data_bucket, "Key": bucket_object['Key']}, Key = neurocaas_job_output_directory + "labeled_data/" + dataset_name + "/" + bucket_object['Key'].split('/')[-1])
    
    final_dataset_dict = collections.defaultdict(list)
    for job_name, job_info in neurocaas_job_config_file["jobs_info"].items():
        final_dataset_dict[job_info["labeled_datasetname"]].append(job_name)
    
    seqlabel_dict = {}
    all_frames = []
    print(final_dataset_dict[labeling_job_info["labeled_datasetname"]])
    for job_name in final_dataset_dict[labeling_job_info["labeled_datasetname"]]:
        try:
            seqlabel = json.loads(s3.get_object(Bucket = data_bucket, Key = neurocaas_job_output_directory + job_name + "/" + path_from_label_job_direct_to_seqlabel)["Body"].read())
            seqlabel_dict[neurocaas_job_config_file["jobs_info"][job_name]["datasetname"]] = seqlabel
        except:
            print("Not all labeling jobs completed for this labeled dataset yet", flush = True)
            #s3 resource not found
            return #returning because not all labeling jobs are completed for this dataset yet
    print("Finished copying data to labeled data folder", flush = True)
    print(seqlabel_dict.keys())
    
    coords = ['x', 'y']
    if "bad_frame" in parts:
        parts.remove("bad_frame")
    header = pd.MultiIndex.from_product([parts, coords])
    df = pd.DataFrame()

    if prevneurocaasjobnum != None:
      try:
        print(group_name + '/results/job__label-job-create-web_' + str(prevneurocaasjobnum) + "/process_results/labeled_data/" + labeled_datasetname + ".csv")
        s3.download_file(data_bucket, group_name + '/results/job__label-job-create-web_' + str(prevneurocaasjobnum) + "/process_results/labeled_data/" + labeled_datasetname + ".csv", '/tmp/' + labeled_datasetname + ".csv")
        existing_df = pd.read_csv(filepath_or_buffer = '/tmp/' + labeled_datasetname + ".csv", header = [0, 1, 2], index_col = 0)
        os.remove('/tmp/' + labeled_datasetname + ".csv")
      except:
        print("labeled dataset with this name does not already exist, creating from scratch")
        existing_df = df
    print(len(seqlabel_dict))
    for dataset_name, seqlabel in seqlabel_dict.items():
        frames = seqlabel["tracking-annotations"]
        for frame in frames:
            df_row = pd.DataFrame(columns = header, index = [dataset_name + "/" + frame["frame"]])
            cols = [("Default_Name", ) + col for col in df_row.columns]
            df_row.columns = pd.MultiIndex.from_tuples(cols, names =['scorer','bodyparts','coords'])
            for annotation in frame["keypoints"]: #assuming no duplicate annotations
                label = annotation["object-name"].split(':')[0]
                df_row["Default_Name", label, 'x'] = annotation["x"]
                df_row["Default_Name", label, 'y'] = annotation["y"]
            df = df.append(df_row, ignore_index = False)
    if prevneurocaasjobnum != None:
      df = pd.concat([existing_df, df])
    s3.put_object(Body = df.to_csv(), Bucket = data_bucket, Key = neurocaas_job_output_directory + "labeled_data/" + labeled_datasetname + ".csv")
    print("uploaded csv!", flush=True)
    df.to_hdf(path_or_buf='/tmp/' + labeled_datasetname + ".h5", key='df', mode='w')
    s3.upload_file('/tmp/' + labeled_datasetname + ".h5", data_bucket, neurocaas_job_output_directory + "labeled_data/" + labeled_datasetname + ".h5")
    print("uploaded h5!", flush=True)
    os.remove('/tmp/' + labeled_datasetname + ".h5")
    return

# test_event = {
#   "Records": [
#     {
#       "eventVersion": "2.0",
#       "eventSource": "aws:s3",
#       "awsRegion": "us-east-1",
#       "eventTime": "1970-01-01T00:00:00.000Z",
#       "eventName": "ObjectCreated:Put",
#       "userIdentity": {
#         "principalId": "EXAMPLE"
#       },
#       "requestParameters": {
#         "sourceIPAddress": "127.0.0.1"
#       },
#       "responseElements": {
#         "x-amz-request-id": "EXAMPLE123456789",
#         "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
#       },
#       "s3": {
#         "s3SchemaVersion": "1.0",
#         "configurationId": "testConfigRule",
#         "bucket": {
#           "name": "label-job-create-web", #changed from label-job-create-web
#           "ownerIdentity": {
#             "principalId": "EXAMPLE"
#           },
#           "arn": "arn:aws:s3:::label-job-create-web"
#         },
#         "object": {
#           "key":"nrg2148columbiaedu1620315589/results/job_2003/process_results/costajob1b/annotations/consolidated-annotation/output/0/SeqLabel.json",  #"testgroup/results/job__1202/process_results/videojobnew20211017054406945421/annotations/consolidated-annotation/output/0/SeqLabel.json",
#           "size": 1024,
#           "eTag": "0123456789abcdef0123456789abcdef",
#           "sequencer": "0A1B2C3D4E5F678901"
#         }
#       }
#     }
#   ]
# }
# #event = {"label_job_input": "reachingvideo1/", "video_bucket": "sagemakerneurocaastest", "video_path": "username/inputs/reachingvideo1.avi",  "data_bucket" : "nickneurocaastest2", "label_bucket" : "nickneurocaastest2", "label_output_key": "output/GeneralTestAWS14/annotations/consolidated-annotation/output/0/SeqLabelMod.json", "dgp_input": "dgp-input-test"}
# context = {}
#lambda_handler(test_event, context)


