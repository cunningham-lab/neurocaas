import boto3
from botocore.exceptions import ClientError

if __name__ == "__main__":
    s3_client = boto3.client("s3")


    response = s3_client.delete_object(Bucket = "cianalysispermastack",Key = "this/key/does/not/exist")
    print(response)

