"""
Test class for Job Manager utils. Test case for botocore stubbing. 
"""
from ncap_iac.protocols.utilsparam.env_vars import *
import ncap_iac.protocols.utilsparam.s3 as s3
import pytest 
from botocore.stub import Stubber
import json
from unittest.mock import patch,MagicMock
from .test_s3_mock_resources import make_mock_bucket#,make_mock_bucket_single_output


@pytest.fixture(autouse=True)
def s3_stub():
    with Stubber(s3.s3_client) as stubber:
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

class Test_s3():
    def test_mkdir_obj_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_response("head_object",expected_params={"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_response = {})
        new_path = s3.mkdir(bucket=bucket_name,path=path,dirname=dirname) 
        assert new_path == os.path.join(path,dirname,"")

    def test_mkdir_obj_not_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_client_error("head_object",service_error_code = "NoSuchKey")
        s3_stub.add_response("put_object",expected_params={"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_response = {})
        new_path = s3.mkdir(bucket=bucket_name,path=path,dirname=dirname) 
        assert new_path == os.path.join(path,dirname,"")

    def test_mkdir_bucket_not_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_client_error("head_object",service_error_code = "NoSuchBucket",service_message ='The specified bucket does not exist.')
        s3_stub.add_client_error("put_object",expected_params = {"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_error_code = "NoSuchBucket",service_message ='The specified bucket does not exist.')
        with pytest.raises(Exception):
            assert s3.mkdir(bucket=bucket_name,path=path,dirname=dirname) 

    def test_mkdir_reset_obj_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_response("head_object",expected_params={"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_response = {})
        s3_stub.add_response("put_object",expected_params={"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_response = {})
        mbucket = make_mock_bucket([{"key":os.path.join(path,dirname,"")}],filter_path = "key")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            new_path = s3.mkdir_reset(bucketname=bucket_name,path = path,dirname=dirname)
            assert new_path == os.path.join(path,dirname,"")

    def test_mkdir_reset_obj_not_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_client_error("head_object",service_error_code = "NoSuchKey")
        s3_stub.add_response("put_object",expected_params={"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_response = {})
        mbucket = make_mock_bucket([{"key":"some/other/path"}],filter_path = "key")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            new_path = s3.mkdir_reset(bucketname=bucket_name,path = path,dirname=dirname)
            assert new_path == os.path.join(path,dirname,"")

    def test_mkdir_reset_bucket_not_exists(self,s3_stub):
        bucket_name = "example_bucket"
        path = "foo"
        dirname = "bar"
        s3_stub.add_client_error("head_object",service_error_code = "NoSuchBucket",service_message ='The specified bucket does not exist.')
        s3_stub.add_client_error("put_object",expected_params = {"Bucket":bucket_name,"Key":os.path.join(path,dirname,"")},service_error_code = "NoSuchBucket",service_message ='The specified bucket does not exist.')
        mbucket = make_mock_bucket([{"key":"some/other/path"}],filter_path = "key")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            with pytest.raises(Exception):
                 assert s3.mkdir_reset(bucketname=bucket_name,path = path,dirname=dirname)

    def test_deldir(self):
        bucket_name = "example_bucket"
        path = "foo/bar"
        mbucket = make_mock_bucket([{"key":"some/other/path"}],filter_path = "key")
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = MagicMock) as mock_bucket_method:

    def test_exists_obj_exists(self):
        mbucket = make_mock_bucket([{"key":"key/path/full"}],filter_path = "key")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            condition = s3.exists("mock_bucket_name","path/to/thing")
            assert condition




