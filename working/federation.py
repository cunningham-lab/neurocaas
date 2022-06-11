# Some code contained here is sourced from https://github.com/awsdocs/aws-doc-sdk-examples/tree/main/python/example_code/sts/sts_temporary_credentials#code-examples,
# which is copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import sys
import time
import urllib.parse
import boto3
import requests
import pytz
from datetime import timedelta 

"""
    The purpose of the file is to serve sts federated users (these are users with temporary IAM credentials, which expire after a short, defined time (<= 12 hrs)), which are granted automatic S3 resource access based on an ABAC-like policy.
    This program creates a user role defined by the accompanying 'federation_policy.json' document, which should be created on your AWS instance
    
"""

def time_millis():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
def progress_bar(seconds):
    """Shows a simple progress bar in the command window."""
    for _ in range(seconds):
        time.sleep(1)
        print('.', end='')
        sys.stdout.flush()
    print()


def unique_name(base_name):
    return f'sts-{base_name}-{time_millis()}'
def unique_testing_name(base_name):
    return f'sts-testing-{base_name}-{time_millis()}'

def setup(iam_resource,name_function):
    """
    Creates a role that can be assumed by the current user.
    Attaches a policy that allows only Amazon S3 read-only access.

    :param iam_resource: A Boto3 AWS Identity and Access Management (IAM) instance
                         that has the permission to create a role.
    :return: The newly created role.
    """
    role = iam_resource.create_role(
        RoleName=name_function('role'), MaxSessionDuration=43200,
        AssumeRolePolicyDocument=json.dumps({
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': iam_resource.CurrentUser().arn},
                    'Action': ['sts:AssumeRole', 'sts:TagSession']
                }
            ]
        })
    )
    #role.attach_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess')
    role.attach_policy(PolicyArn='arn:aws:iam::739988523141:policy/access-same-project-team')
    print(f"Created role {role.name}.")

    print("Give AWS time to propagate these new resources and connections.", end='')
    progress_bar(10)

    return role


def generate_credentials(assume_role_arn, session_name, sts_client, group_name, bucket_name):
    """
    Constructs a URL that gives federated users direct access to the AWS Management
    Console.

    1. Acquires temporary credentials from AWS Security Token Service (AWS STS) that
       can be used to assume a role with limited permissions.
    2. Uses the temporary credentials to request a sign-in token from the
       AWS federation endpoint.
    3. Builds a URL that can be used in a browser to navigate to the AWS federation
       endpoint, includes the sign-in token for authentication, and redirects to
       the AWS Management Console with permissions defined by the role that was
       specified in step 1.

    :param assume_role_arn: The role that specifies the permissions that are granted.
                            The current user must have permission to assume the role.
    :param session_name: The name for the STS session.
    :param issuer: The organization that issues the URL.
    :param sts_client: A Boto3 STS instance that can assume the role.
    :param group_name: group name
    :param bucket_name: bucket name
    :return: The federated URL. 
    """
    response = sts_client.assume_role(
        RoleArn=assume_role_arn, RoleSessionName=session_name, DurationSeconds=43200, Tags=[{"Key": "access-bucket","Value": bucket_name},{"Key": "access-group","Value": group_name}])
    return response['Credentials']


def teardown(role):
    """
    Removes all resources created during setup.

    :param role: The demo role.
    """
    for attached in role.attached_policies.all():
        role.detach_policy(PolicyArn=attached.arn)
        print(f"Detached {attached.policy_name}.")
    role.delete()
    print(f"Deleted {role.name}.")

#utils

def build_credentials(group, analysis,testing=False):
    #: Returns object with temporary credentials

    iam_resource = boto3.resource('iam')
    name_function = unique_testing_name if testing else unique_name
    role = setup(iam_resource,name_function)
    sts_client = boto3.client('sts')
    return generate_credentials(role.arn, 'AssumeRoleDemoSession', sts_client, group.name, analysis.bucket_name) 

def reassign_iam(iam, temp_credentials):
    iam.aws_access_key = temp_credentials['AccessKeyId']
    iam.aws_secret_access_key = temp_credentials['SecretAccessKey']
    iam.aws_session_token = temp_credentials['SessionToken']
    iam.save()

def construct_federated_url(iam, issuer, bucket):
    """
    Constructs a URL that gives federated users direct access to the AWS Management
    Console.
       Builds a URL that can be used in a browser to navigate to the AWS federation
       endpoint, includes the sign-in token for authentication, and redirects to
       the AWS Management Console with permissions defined by the role that was
       specified in step 1.

    :param issuer: The organization that issues the URL.
    :return: The federated URL.
    """

    session_data = {
        'sessionId': iam.aws_access_key,
        'sessionKey': iam.aws_secret_access_key,
        'sessionToken': iam.aws_session_token
    }
    aws_federated_signin_endpoint = 'https://signin.aws.amazon.com/federation'

    # Make a request to the AWS federation endpoint to get a sign-in token.
    # The requests.get function URL-encodes the parameters and builds the query string
    # before making the request.
    response = requests.get(
        aws_federated_signin_endpoint,
        params={
            'Action': 'getSigninToken',
            'SessionDuration': str(datetime.timedelta(hours=12).seconds),
            'Session': json.dumps(session_data)
        })
    signin_token = json.loads(response.text)
    print(f"Got a sign-in token from the AWS sign-in federation endpoint.")

    # Make a federated URL that can be used to sign into the AWS Management Console.
    query_string = urllib.parse.urlencode({
        'Action': 'login',
        'Issuer': issuer,
        'Destination': 'https://s3.console.aws.amazon.com/s3/buckets/'+bucket+'?region=us-east-1&prefix='+iam.group.name+'/inputs/&showversions=false',
        'SigninToken': signin_token['SigninToken']
    })
    federated_url = f'{aws_federated_signin_endpoint}?{query_string}'
    return federated_url
def _deletion_filter(role):
    return role.role_name.startswith("sts-role-") and pytz.utc.localize(datetime.datetime.now()) > (role.create_date+timedelta(seconds=role.max_session_duration)).astimezone(pytz.utc)
def _deletion_filter_testing(role):
    return role.role_name.startswith("sts-testing-role-")
def sts_teardown_all(testing=False):
    for role in filter(_deletion_filter_testing if testing else _deletion_filter,boto3.resource('iam').roles.all()):
        teardown(role)