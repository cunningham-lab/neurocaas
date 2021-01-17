## Main file to build lambda functions in localstack, subverting the need for cfn.  
import pytest
import localstack.session


@pytest.fixture
def create_lambda(monkeypatch):
    """Sets up the module to use localstack, and creates a lambda function in localstack called test-lambda. Source code taken from ./test_mats/testmainlambda.zip. 

    """
    session = localstack.session.Session()
    lambda_client = session.client("lambda")
    lambda_resource = session.resource("lambda")
    lambda_client.create_function(
            FunctionName = "test-lambda",
            Runtime = 'python3.6',
            Role = 'todo',
            Handler = 'submit_start.handler',
            Description = "test Lambda Function for Serverless",
            MemorySize = 128,

            ) 


