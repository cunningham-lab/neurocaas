import pytest
import boto3
from botocore.exceptions import ClientError
import ncap_iac.ncap_blueprints.dev_utils.develop_blueprint as develop_blueprint
import os

@pytest.fixture()
def use_devcred(monkeypatch):
    monkeypatch.setattr(develop_blueprint,"ec2_resource",boto3.Session(profile_name = "testdev").resource("ec2"))

loc = os.path.dirname(os.path.abspath(__file__))
fixturetemplate = os.path.join(loc,"fixtures")

def test_NeuroCaaSAMI(use_devcred):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    
def test_NeuroCaaSAMI_launch(use_devcred):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    try:
        devami.launch_devinstance(DryRun = True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "DryRunOperation"

@pytest.mark.parametrize("ami",["ubuntu18","ubuntu16","dlami18","dlami16","ami-07ebfd5b3428b6f4d"])
def test_NeuroCaaSAMI_launch_defaultami(ami,use_devcred):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    try:
        devami.launch_devinstance(ami,DryRun = True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "DryRunOperation"

def test_NeuroCaaSAMI_launch_wrongami(use_devcred):
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    try:
        devami.launch_devinstance(ami="zz",DryRun = True)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "InvalidAMIID.Malformed"

@pytest.mark.parametrize("ami",[None,"ubuntu18","ubuntu16","dlami18","dlami16","ami-07ebfd5b3428b6f4d"])
def test_NeuroCaaSAMI_launch_wvolume(ami,use_devcred):
    """The error for volume requested too small is confusing.

    """
    devami = develop_blueprint.NeuroCaaSAMI(fixturetemplate)
    try:
        devami.launch_devinstance(ami,DryRun = True,volume_size = 200)
    except ClientError as e:    
        assert e.response["Error"]["Code"] == "DryRunOperation"

