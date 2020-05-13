"""
Test class for Job Manager utils. Test case for botocore stubbing. 
"""
from ..protocols.utilsparam.env_vars import *
from ..protocols.utilsparam.s3 import s3_resource,s3_client,mkdir,exists 
import pytest 
from botocore.stub import Stubber
import json
from unittest.mock import patch,MagicMock
from .test_s3_mock_resources import make_mock_bucket


@pytest.fixture(autouse=True)
def s3_stub():
    with Stubber(s3_client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def create_good_submission_args():
    with open("../utils/simevents/s3_putevent_pytest.json") as f:
        event = json.load(f)
        record = event["Records"][0]
        bucket_name = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"] 
        time = record["eventTime"]
    return bucket_name,key,time 

def test_mkdir_exists(s3_stub):
    s3_stub.add_response("head_object",expected_params={"Bucket":"example_bucket","Key":"foo/bar/"},service_response = {})
    new_path = mkdir(bucket="example_bucket",path="foo",dirname="bar") 
    assert new_path == "foo/bar/"

def test_mkdir_not_exists(s3_stub):
    s3_stub.add_client_error("head_object")
    s3_stub.add_response("put_object",expected_params={"Bucket":"example_bucket","Key":"foo/bar/"},service_response = {})
    new_path = mkdir(bucket="example_bucket",path="foo",dirname="bar") 
    assert new_path == "foo/bar/"

def test_exists():
    mbucket = make_mock_bucket()
    with patch.object(s3_resource,"Bucket",return_value=mbucket) as mock_method:
        condition = exists("mock_bucket_name","path/to/thing")
        assert condition




