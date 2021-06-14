import json
import sys
import boto3
import pandas as pd
import yaml

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    #copies frame jpegs from labeling job input folder
    data_bucket = event["Records"][0]["s3"]["bucket"]["name"]
    group_name = event["Records"][0]["s3"]["object"]['key'].split('/')[0]
    label_job_config_file = yaml.load(s3.get_object(Bucket = data_bucket, Key = group_name + '/configs/config.yaml')["Body"].read())
    target_bucket = label_job_config_file["finaldatabucket"]
    model_config_file = yaml.load((s3.get_object(Bucket = target_bucket, Key = 'data/config.yaml')["Body"].read()))
    job_name = label_job_config_file["jobname"]
    output_path = model_config_file["process_dir"]
    video_name = model_config_file["video_name"]
    bucket_contents = s3.list_objects(Bucket = data_bucket, Prefix = group_name + '/inputs/' + video_name + '/')
    objects = bucket_contents['Contents']
    for bucket_object in objects:
        s3.copy_object(Bucket = target_bucket, CopySource = {"Bucket" : data_bucket, "Key": bucket_object['Key']}, Key = "data/labeled-data/" + video_name + "/" + bucket_object['Key'].split('/')[-1]) #copies with same name
    seqlabel = json.loads(s3.get_object(Bucket = data_bucket, Key = group_name + '/' + output_path + '/' + job_name + '/annotations/consolidated-annotation/output/0/SeqLabel.json')["Body"].read())
    parts = label_job_config_file['bodyparts'] #['Hand', 'Finger1', 'Tongue', 'Joystick1', 'Joystick2']
    coords = ['x', 'y']
    header = pd.MultiIndex.from_product([parts, coords])
    df = pd.DataFrame()
    frames = seqlabel["tracking-annotations"]
    num_frames = len(frames)
    for frame in frames:
        df_row = pd.DataFrame(columns = header, index = [frame["frame"]])
        cols = [("Mackenzie", ) + col for col in df_row.columns]
        df_row.columns = pd.MultiIndex.from_tuples(cols, names =['scorer','bodyparts','coords'])
        for annotation in frame["keypoints"]: #assuming no duplicate annotations
            label = annotation["object-name"].split(':')[0]
            df_row["Mackenzie", label, 'x'] = annotation["x"]
            df_row["Mackenzie", label, 'y'] = annotation["y"]
        df = df.append(df_row, ignore_index = False)
    #print(df)
    response = s3.put_object(Body = df.to_csv(), Bucket = target_bucket, Key = "data/labeled-data/" + video_name + "/CollectedData.csv")
    return

test_event = {
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "1970-01-01T00:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "127.0.0.1"
      },
      "responseElements": {
        "x-amz-request-id": "EXAMPLE123456789",
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "label-job-create", #changed from label-job-create-web
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::label-job-create-web"
        },
        "object": {
          "key": "testgroup/results/job__timestamp/process_results/end.txt", #changed to testgroup from examplegroup
          "size": 1024,
          "eTag": "0123456789abcdef0123456789abcdef",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}
#event = {"label_job_input": "reachingvideo1/", "video_bucket": "sagemakerneurocaastest", "video_path": "username/inputs/reachingvideo1.avi",  "data_bucket" : "nickneurocaastest2", "label_bucket" : "nickneurocaastest2", "label_output_key": "output/GeneralTestAWS14/annotations/consolidated-annotation/output/0/SeqLabelMod.json", "dgp_input": "dgp-input-test"}
context = {}
lambda_handler(test_event, context)

