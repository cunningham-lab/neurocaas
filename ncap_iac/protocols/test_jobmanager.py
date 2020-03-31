"""
Test class for Job Manager object. Currently broken. 
"""
import pytest 
import json
from submit_start import Submission_dev 
from unittest.mock import patch

@pytest.fixture
def create_good_submission_args():
    with open("../utils/simevents/s3_putevent.json") as f:
        event = json.load(f)
        record = event["Records"][0]
        bucket_name = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"] 
        time = record["eventTime"]
    return bucket_name,key,time 

class TestSubmission(): 

    def test_init_parse_submit(self,monkeypatch,create_good_submission_args):
        Submission_dev(*create_good_submission_args)
        
