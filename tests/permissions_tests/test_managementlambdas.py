# uncompyle6 version 3.7.4
# Python bytecode 3.6 (3379)
# Decompiled from: Python 3.6.9 |Anaconda, Inc.| (default, Jul 30 2019, 13:42:17) 
# [GCC 4.2.1 Compatible Clang 4.0.1 (tags/RELEASE_401/final)]
# Embedded file name: /Users/taigaabe/neurocaas/tests/permissions_tests/test_managementlambdas.py
# Compiled at: 2021-01-29 17:56:57
# Size of source mod 2**32: 12920 bytes
import os, pytest, localstack_client.session

env_vars = {'graceperiod':'10', 
 'exemptlist':'i-029339d0ff4fa4318,i-0c366d0e991bc6fde,i-04a5f4794bafda3b1,i-0a7b60fe2661444da', 
 'dryrun':'1', 
 'topicarn':'arn:aws:sns:us-east-1:739988523141:EC2_Instance_Sweeper', 
 'localstack':'1', 
 'AWS_ACCCESS_KEY_ID':'foo', 
 'AWS_SECRET_ACCESS_KEY':'bar', 
 'LOCALSTACK_HOSTNAME':'localhost'}
for var in env_vars.items():
    os.environ[var[0]] = var[1]

import ncap_iac.permissions.management_lambdas.lambda_function_imported as lambda_function_imported
session = localstack_client.session.Session()
ec2_resource_local = session.resource('ec2')
ec2_client_local = session.client('ec2')
ssm_client_local = session.client('ssm')

@pytest.fixture()
def set_ssm_exempt(monkeypatch):
    monkeypatch.setattr(lambda_function_imported, 'ssm_client', ssm_client_local)
    ssm_client_local.put_parameter(Name='exempt_instances', Type='String',
      Overwrite=True,
      Value=(env_vars['exemptlist']))
    yield 'values'
    ssm_client_local.delete_parameter(Name='exempt_instances')


@pytest.fixture()
def create_lambda_env(monkeypatch):
    """Takes the relevant environment variables and places them in the environment. 

    """
    for var in env_vars.items():
        (monkeypatch.setenv)(*var)


@pytest.fixture()
def create_instance_array(create_mockinstance, create_mockinstance_doomed, create_mockinstance_untagged):
    """Create an array of mock instances to test 

    """
    pass


@pytest.fixture()
def create_mockinstance_doomed(monkeypatch):
    """Creates a mock instance for the purpose of getting and modifying tags. Doomed because the relevant timeouts are set to 0 minutes. 
    """
    session = localstack_client.session.Session()
    ec2_resource = session.resource('ec2')
    ec2_client = session.client('ec2')
    monkeypatch.setattr(lambda_function_imported, 'ec2_client', session.client('ec2'))
    output = ec2_resource.create_instances(ImageId='garbage', InstanceType='t2.micro',
      MinCount=1,
      MaxCount=1,
      TagSpecifications=[
     {'ResourceType':'volume', 
      'Tags':[{'Key':'Timeout',  'Value':str(-1)}]}, {'ResourceType':'instance',  'Tags':[{'Key':'Timeout',  'Value':str(-1)}]}])
    yield output
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds=[instance_id])


@pytest.fixture()
def create_mockinstance_ssm(monkeypatch):
    """Creates a mock instance without tags and with an ssm command running, mimicking deployment instances.  

    """
    session = localstack_client.session.Session()
    ec2_resource = session.resource('ec2')
    ec2_client = session.client('ec2')
    monkeypatch.setattr(lambda_function_imported, 'ec2_client', session.client('ec2'))
    output = ec2_resource.create_instances(ImageId='garbage', InstanceType='t2.micro',
      MinCount=1,
      MaxCount=1)
    ssm_client_local.send_command(DocumentName='AWS-RunShellScript',
      InstanceIds=[
     output[0].instance_id],
      Parameters={'commands':[
      'sleep 100; sleep 10'], 
     'executionTimeout':[
      str(3600)]})

    def mockfunc(instance_info):
        return output[0].instance_id != instance_info['InstanceId']

    yield (output, mockfunc)
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds=[instance_id])


@pytest.fixture()
def create_mockinstance(monkeypatch):
    """Creates a mock instance for the purpose of getting and modifying tags. BEWARE: As this spins up a localstack instance, is a check of function only, not permissions. 

    """
    session = localstack_client.session.Session()
    ec2_resource = session.resource('ec2')
    ec2_client = session.client('ec2')
    monkeypatch.setattr(lambda_function_imported, 'ec2_client', session.client('ec2'))
    output = ec2_resource.create_instances(ImageId='garbage', InstanceType='t2.micro',
      MinCount=1,
      MaxCount=1,
      TagSpecifications=[
     {'ResourceType':'volume', 
      'Tags':[{'Key':'Timeout',  'Value':str(100)}]}, {'ResourceType':'instance',  'Tags':[{'Key':'Timeout',  'Value':str(100)}]}])
    yield output
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds=[instance_id])


@pytest.fixture()
def create_mockinstance_untagged(monkeypatch):
    """Creates a mock instance for the purpose of getting and modifying tags. BEWARE: As this spins up a localstack instance, is a check of function only, not permissions. 

    """
    session = localstack_client.session.Session()
    ec2_resource = session.resource('ec2')
    ec2_client = session.client('ec2')
    monkeypatch.setattr(lambda_function_imported, 'ec2_client', session.client('ec2'))
    output = ec2_resource.create_instances(ImageId='garbage', InstanceType='t2.micro',
      MinCount=1,
      MaxCount=1)
    yield output
    instance_id = output[0].instance_id
    ec2_client.terminate_instances(InstanceIds=[instance_id])


def test_not_exempt_ssm(create_lambda_env, create_mockinstance, set_ssm_exempt):
    """

    """
    inst_id = create_mockinstance[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    print(instance_info['InstanceId'], os.environ['exemptlist'])
    assert lambda_function_imported.not_exempt(instance_info)
    copy_dict = {}
    for key, val in instance_info.items():
        copy_dict[key] = val

    copy_dict['InstanceId'] = 'i-029339d0ff4fa4318'
    assert not lambda_function_imported.not_exempt(copy_dict)


def test_not_exempt(monkeypatch, create_lambda_env, create_mockinstance):
    """

    """
    inst_id = create_mockinstance[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    print(instance_info['InstanceId'], os.environ['exemptlist'])
    assert lambda_function_imported.not_exempt(instance_info)
    copy_dict = {}
    for key, val in instance_info.items():
        copy_dict[key] = val

    copy_dict['InstanceId'] = 'i-029339d0ff4fa4318'
    assert not lambda_function_imported.not_exempt(copy_dict)


def test_no_command(create_lambda_env, create_mockinstance):
    inst_id = create_mockinstance[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    assert lambda_function_imported.no_command(instance_info)
    ssm_client_local.send_command(InstanceIds=[inst_id], DocumentName='AWS-RunShellScript', Parameters={'commands': ['ls']})
    assert not lambda_function_imported.no_command(instance_info)
    ec2_client_local.terminate_instances(InstanceIds=[inst_id])


@pytest.mark.parametrize('graceperiod,condition', [(-1, True), (10, False)])
def test_active_past_graceperiod(monkeypatch, create_lambda_env, create_mockinstance, graceperiod, condition):
    inst_id = create_mockinstance[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    monkeypatch.setattr(lambda_function_imported, 'graceperiod', graceperiod)
    assert lambda_function_imported.active_past_graceperiod(instance_info) == condition


def test_active_past_timeout(monkeypatch, create_lambda_env, create_mockinstance, create_mockinstance_doomed, create_mockinstance_untagged):
    inst_id = create_mockinstance[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    assert not lambda_function_imported.active_past_timeout(instance_info)

    inst_id = create_mockinstance_doomed[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    assert lambda_function_imported.active_past_timeout(instance_info)

    inst_id = create_mockinstance_untagged[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    assert not lambda_function_imported.active_past_timeout(instance_info)

    inst_id = create_mockinstance_untagged[0].instance_id
    response = ec2_client_local.describe_instances(InstanceIds=[inst_id])
    instance_info = response['Reservations'][0]['Instances'][0]
    monkeypatch.setattr(lambda_function_imported, 'graceperiod', -1)
    assert lambda_function_imported.active_past_timeout(instance_info)


def test_get_rogue_instances(monkeypatch, create_mockinstance, create_mockinstance_doomed, create_mockinstance_untagged, create_mockinstance_ssm):
    normal_id = create_mockinstance[0].instance_id
    exempt_info = ec2_client_local.describe_instances(InstanceIds=[normal_id])['Reservations'][0]['Instances'][0]
    deploy_id = create_mockinstance_ssm[0][0].instance_id
    mockfunc = create_mockinstance_ssm[1]
    monkeypatch.setattr(lambda_function_imported, 'no_command', mockfunc)
    deploy_info = ec2_client_local.describe_instances(InstanceIds=[deploy_id])['Reservations'][0]['Instances'][0]
    doomed_id = create_mockinstance_doomed[0].instance_id
    doomed_info = ec2_client_local.describe_instances(InstanceIds=[doomed_id])['Reservations'][0]['Instances'][0]
    untagged_id = create_mockinstance_untagged[0].instance_id
    untagged_info = ec2_client_local.describe_instances(InstanceIds=[untagged_id])['Reservations'][0]['Instances'][0]
    monkeypatch.setattr(lambda_function_imported, 'ec2_client', ec2_client_local)
    instances = lambda_function_imported.get_rogue_instances()
    instanceids = [i['InstanceId'] for i in instances]
    print(normal_id, deploy_id, doomed_id, untagged_id, 'normal,deploy,doomed,untagged')
    assert instanceids == [doomed_id]

    with monkeypatch.context() as m:
        m.setattr(lambda_function_imported, 'exempt', [normal_id])
        instances = lambda_function_imported.get_rogue_instances()
        instanceids = [i['InstanceId'] for i in instances]
        assert instanceids == [doomed_id]

    with monkeypatch.context() as m:
        m.setattr(lambda_function_imported, 'exempt', [doomed_id])
        instances = lambda_function_imported.get_rogue_instances()
        instanceids = [i['InstanceId'] for i in instances]
        assert instanceids == []

    with monkeypatch.context() as m:
        m.setattr(lambda_function_imported, 'graceperiod', -1)
        instances = lambda_function_imported.get_rogue_instances()
        instanceids = [i['InstanceId'] for i in instances]
        assert set(instanceids) == set([doomed_id,untagged_id])

    with monkeypatch.context() as m:
        m.setattr(lambda_function_imported, 'exempt', [doomed_id, untagged_id])
        m.setattr(lambda_function_imported, 'graceperiod', -1)
        instances = lambda_function_imported.get_rogue_instances()
        instanceids = [i['InstanceId'] for i in instances]
        assert set(instanceids) == set([])

    with monkeypatch.context() as (m):
        m.setattr(lambda_function_imported, 'exempt', [normal_id])
        m.setattr(lambda_function_imported, 'graceperiod', -1)
        instances = lambda_function_imported.get_rogue_instances()
        instanceids = [i['InstanceId'] for i in instances]
        assert set(instanceids) == set([doomed_id,untagged_id])
