"""
Test class for Job Manager utils. Test case for botocore stubbing. 
"""
from ncap_iac.protocols.utilsparam.env_vars import *
import ncap_iac.protocols.utilsparam.s3 as s3
import pytest 
from botocore.stub import Stubber
import json
import yaml
from unittest.mock import patch,MagicMock,call
from .test_fixtures import return_json_read, return_json_malformed,return_yaml_read,return_yaml_malformed
from .test_s3_mock_resources import make_mock_bucket,make_mock_object,make_mock_file_object


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

class Test_s3_base():
    """ Tests the basic functions used to interact directly with the boto3 api. 

    """
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
        mbucket = make_mock_bucket([{"key":"some/given/path"},{"key":"some/other/path"}],filter_path = "some")
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object_method:
                s3.deldir("mock_bucket_name","path/to/thing")
                mock_object_method.assert_called()
            mock_bucket_method.assert_called_once()

    def test_deldir_path_empty(self):
        mbucket = make_mock_bucket([{"key":"an/given/path"},{"key":"an/other/path"}],filter_path = "some")
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object_method:
                s3.deldir("mock_bucket_name","path/to/thing")
                mock_object_method.assert_not_called()
            mock_bucket_method.assert_called_once()

    def test_deldir_bucket_empty(self):
        mbucket = make_mock_bucket([],filter_path = "some")
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object_method:
                s3.deldir("mock_bucket_name","path/to/thing")
                mock_object_method.assert_not_called()
            mock_bucket_method.assert_called_once()

    def test_delbucket(self):
        mbucket = make_mock_bucket([{"key":"some/given/path"},{"key":"some/other/path"}],filter_path = "some")
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object_method:
                s3.delbucket("mock_bucket_name")
                mock_object_method.assert_called()
            mock_bucket_method.assert_called_once()

    def test_delbucket_bucket_empty(self):
        mbucket = make_mock_bucket([],filter_path = "some")
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object_method:
                s3.delbucket("mock_bucket_name")
                mock_object_method.assert_not_called()
            mock_bucket_method.assert_called_once()

    def test_ls(self):
        tuple_arguments = ("path/to/1","path/to/2")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            bucket = s3.s3_resource.Bucket("name")
            assert list(tuple_arguments) == s3.ls(bucket,path)
            mock_bucket_method.assert_called_once()
            
    def test_ls_prefix(self):
        tuple_arguments = ("path/to/1","path/to/2","other/path")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            bucket = s3.s3_resource.Bucket("name")
            assert list(tuple_arguments)[:2] == s3.ls(bucket,path)
            mock_bucket_method.assert_called_once()

    def test_ls_empty_prefix(self):
        tuple_arguments = ("path/to/1","path/to/2","other/path")
        path = "otherkey"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            bucket = s3.s3_resource.Bucket("name")
            assert [] == s3.ls(bucket,path)
            mock_bucket_method.assert_called_once()

    def test_ls_name(self):
        tuple_arguments = ("path/to/1","path/to/2")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert list(tuple_arguments) == s3.ls_name("bucketname",path)
            mock_bucket_method.assert_called_once()
            
    def test_ls_name_prefix(self):
        tuple_arguments = ("path/to/1","path/to/2","other/path")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert list(tuple_arguments)[:2] == s3.ls_name("bucketname",path)
            mock_bucket_method.assert_called_once()

    def test_ls_name_empty_prefix(self):
        tuple_arguments = ("path/to/1","path/to/2","other/path")
        path = "otherkey"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert [] == s3.ls_name("bucketname",path)
            mock_bucket_method.assert_called_once()

    def test_exists_obj_exists(self):
        key = "path/to/thing"
        mbucket = make_mock_bucket([{"key":key}],filter_path = "path")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            condition = s3.exists("mock_bucket_name","path")
            assert condition

    def test_exists_obj_not_exists(self):
        key = "path/to/thing"
        mbucket = make_mock_bucket([{"key":key}],filter_path = "otherkey")
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_method:
            condition = s3.exists("mock_bucket_name",key)
            assert not condition

    def test_cp(self):
        path1 = "path1"
        path2 = "path2"
        example_bucketname = "example_bucketname"
        with patch.object(s3.s3_resource,"meta",return_value = MagicMock) as mock_client:
            s3.cp(example_bucketname,path1,path2)
            mock_client.mock_calls[0] 
            assert mock_client.mock_calls == [call.client.copy({'Bucket':example_bucketname, 'Key': path1},example_bucketname, path2)]
        
    def test_mv(self):
        path1 = "path1"
        path2 = "path2"
        example_bucketname = "example_bucketname"
        mobject = make_mock_object({"key":"some/other/path"}) 
        with patch.object(s3.s3_resource,"meta",return_value = MagicMock) as mock_client:
            with patch.object(s3.s3_resource,"Object",return_value = mobject) as mock_object:
                s3.mv(example_bucketname,path1,path2)
                assert mock_client.mock_calls == [call.client.copy({'Bucket':example_bucketname, 'Key': path1},example_bucketname, path2)]
                ## Shouldn't the following also record Object().delete?
                assert mock_object.mock_calls == [call('example_bucketname',path1)]

    def test_load_json(self):
        a = return_json_read()
        file_object_mock = make_mock_file_object(a)
        with patch.object(s3.s3_resource,"Object",return_value = file_object_mock) as mock_fileobj:
            assert s3.load_json("a","b") == json.loads(a.decode("utf-8"))

    def test_load_malformed_json(self):
        a = return_json_malformed()
        file_object_mock = make_mock_file_object(a)
        with patch.object(s3.s3_resource,"Object",return_value = file_object_mock) as mock_fileobj:
            with pytest.raises(ValueError):
                 assert s3.load_json("a","b")

    def test_load_yaml(self):
        a = return_yaml_read()
        file_object_mock = make_mock_file_object(a)
        with patch.object(s3.s3_resource,"Object",return_value = file_object_mock) as mock_fileobj:
            assert s3.load_yaml("a","b") == yaml.safe_load(a.decode("utf-8"))

    def test_load_malformed_yaml(self):
        a = return_yaml_malformed()
        file_object_mock = make_mock_file_object(a)
        with patch.object(s3.s3_resource,"Object",return_value = file_object_mock) as mock_fileobj:
            with pytest.raises(ValueError):
                 assert s3.load_yaml("a","b")

    def test_extract_files(self):
        tuple_arguments = ("path/to/1","path/to/2")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert list(tuple_arguments) == s3.extract_files("bucketname",path)
            mock_bucket_method.assert_called_once()

    def test_extract_files_with_directories(self):
        tuple_arguments = ("path/to/1","path/to","path/to/2","path/to/")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert list(tuple_arguments)[:-1] == s3.extract_files("bucketname",path)
            mock_bucket_method.assert_called_once()

    def test_extract_files_with_extensions(self):
        tuple_arguments = ("path/to/1.jpg","path/to/2","path/to/")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            assert list(tuple_arguments)[:1] == s3.extract_files("bucketname",path,ext = "jpg")
            mock_bucket_method.assert_called_once()

    def test_extract_files_with_malformed_extensions(self):
        tuple_arguments = ("path/to/1.jpg","path/to/2","path/to/")
        path = "path"
        mbucket = make_mock_bucket([{"key":path} for path in tuple_arguments],filter_path = path)
        with patch.object(s3.s3_resource,"Bucket",return_value = mbucket) as mock_bucket_method:
            with pytest.raises(ValueError):
                assert s3.extract_files("bucketname",path,ext = ".jpg")
            mock_bucket_method.assert_called_once()

    def test_write_endfile(self):
        mbucket = make_mock_bucket([]) 
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_bucket_method:
            s3.write_endfile("bucketname","resultpath")
            assert (mock_bucket_method.mock_calls) == [call('bucketname')]
            assert (mock_bucket_method.return_value.mock_calls) == [call.put_object(Body=b'end of analysis marker', Key='resultpath/process_results/end.txt')] 

    def test_write_active_monitorlog(self):
        mbucket = make_mock_bucket([]) 
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_bucket_method:
            s3.write_active_monitorlog("bucketname","resultpath",{"key":"value"})
            assert (mock_bucket_method.mock_calls) == [call('bucketname')]
            print((mock_bucket_method.return_value.mock_calls))
            assert (mock_bucket_method.return_value.mock_calls) == [call.put_object(Body=b'{\n  "key": "value"\n}', Key='logs/active/resultpath')] 

    def test_delete_active_monitorlog(self,s3_stub):
        bucketname = "bucketname"
        key = "key"
        s3_stub.add_response("delete_object",expected_params={"Bucket":bucketname,"Key":os.path.join("logs","active",key)},service_response = {})
        s3.delete_active_monitorlog(bucketname,key)

    def test_update_monitorlog_start(self):
        time = "t0"
        log_init = {"start":"init_val","end":"init_val"}
        instance_id = "i-12345" 
        a = return_yaml_read()
        mbucket = make_mock_bucket([]) 
        file_object_mock = make_mock_file_object(a)
        mbucket.put_object.return_value = file_object_mock
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_bucket_method:
            with patch('ncap_iac.protocols.utilsparam.s3.load_json',return_value=log_init) as mock_fileobj_method:
                log_test = {"start":time,"end":"init_val"}
                s3.update_monitorlog("bucketname",instance_id,"running",time)
                print((mock_bucket_method.return_value.put_object.mock_calls))
                assert (mock_bucket_method.mock_calls) == [call('bucketname')]
                assert (mock_bucket_method.return_value.mock_calls) == [call.put_object(Body=bytes(json.dumps(log_test,indent = 2).encode('UTF-8')), Key=os.path.join("logs","active",instance_id))] 
        
    def test_update_monitorlog_start(self):
        time = "t0"
        log_init = {"start":"init_val","end":"init_val"}
        instance_id = "i-12345" 
        a = return_yaml_read()
        mbucket = make_mock_bucket([]) 
        file_object_mock = make_mock_file_object(a)
        mbucket.put_object.return_value = file_object_mock
        with patch.object(s3.s3_resource,"Bucket",return_value=mbucket) as mock_bucket_method:
            with patch('ncap_iac.protocols.utilsparam.s3.load_json',return_value=log_init) as mock_fileobj_method:
                log_test = {"start":"init_val","end":time}
                s3.update_monitorlog("bucketname",instance_id,"shutting-down",time)
                print((mock_bucket_method.return_value.put_object.mock_calls))
                assert (mock_bucket_method.mock_calls) == [call('bucketname')]
                assert (mock_bucket_method.return_value.mock_calls) == [call.put_object(Body=bytes(json.dumps(log_test,indent = 2).encode('UTF-8')), Key=os.path.join("logs","active",instance_id))] 


## Todo: cover exception. 




















        
