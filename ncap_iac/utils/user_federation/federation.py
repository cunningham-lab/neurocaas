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
    The purpose of the file is to serve STS federated users (these are users with temporary IAM credentials, 
    which expire after a short, defined time (<= 12 hrs)), which are granted automatic S3 resource access based on an ABAC-like policy.

    Use Case:
    If you are an IAM user with limited permissions using the neurocaas cloud, this is likely is not relevant (due to permission needs outlined below).
    
    However, this may be useful to users with elevated permissions looking to grant temporary access to other users, 
    or users with their own, seperately hosted neurocaas system.

    Explanation:
    This program creates a user role defined by the accompanying 'aws_federation_policy.json' document, 
    which should be created on your AWS instance. On the official neurocaas.org cloud, this policy is named 'access-same-project-team'.

    Furthermore a non-federated IAM must exist to federate new users, with access to all of the relevant buckets and files. 
    This user must have access to certain permission delegation functions which can be seen in this file, 
    including assume_role, attach_policy, detach_policy, etc. 
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html for relevant policy information.

    S3 resource access is established through a hybrid tag and prefix system. 
    Upon creation, the federated user is tagged with relevant group and bucket prefixes (one of each), 
    which is the only resource this user will have access too. However, this system can be modified as needed by adapting the policy (for example allowing access to all buckets).

    The aformentioned policy uses the prefixes contained in access tags to determine the allowed bucket and folder, so ensure these are correct.
    If proper access is established, the user should have read-write access to configs/submissions, 
    write access to inputs, and read access to results. Modify the policy document for different access functionality.
    
    See https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html for information on STS, 
    and https://github.com/awsdocs/aws-doc-sdk-examples/tree/main/python/example_code/sts/sts_temporary_credentials#code-examples for STS federation examples.
"""

def time_millis(): # More precise than something like time.time()*1000, which may or may not be needed
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
def progress_bar(seconds):
    """Shows a simple progress bar in the command window."""
    for _ in range(seconds):
        time.sleep(1)
        print('.', end='')
        sys.stdout.flush()
    print()

def unique_name():
    return f'sts-role-{time_millis()}'

def setup(iam_resource, duration=43200):
    """
    Creates a role that can be assumed by the current user.
    Attaches a policy that allows only Amazon S3 read-only access.

    :param iam_resource: A Boto3 AWS Identity and Access Management (IAM) instance
                         that has the permission to create a role.
    :param duration: Credential lifetime (s). Defaults to 43200 (12 hours)
    :return: The newly created role.
    """
    role = iam_resource.create_role(
        RoleName=unique_name(), MaxSessionDuration=duration,
        AssumeRolePolicyDocument=json.dumps({ #: Embedded policy to allow a new user to assume a role and tag
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
    role.attach_policy(PolicyArn='arn:aws:iam::739988523141:policy/access-same-project-team') #: This should be the policy ARN 
    print(f"Created role {role.name}.")

    print("Give AWS time to propagate these new resources and connections.", end='')
    progress_bar(10)

    return role


def generate_credentials(assume_role_arn, session_name, sts_client, group_name, bucket_name, duration=43200):
    """
    Acquires temporary credentials from AWS Security Token Service (AWS STS) that
       can be used to assume a role with limited permissions.

    :param assume_role_arn: The role that specifies the permissions that are granted.
                            The current user must have permission to assume the role.
    :param session_name: The name for the STS session.
    :param issuer: The organization that issues the URL.
    :param sts_client: A Boto3 STS instance that can assume the role.
    :param group_name: group name
    :param bucket_name: bucket name
    :return: Credentials. 
    """
    response = sts_client.assume_role(
        RoleArn=assume_role_arn, RoleSessionName=session_name, DurationSeconds=duration, 
        Tags=[{"Key": "access-bucket","Value": bucket_name},{"Key": "access-group","Value": group_name}]) #: Tags for bucket and group prefix
    return response['Credentials']


#utils

def construct_federated_url(credentials, issuer, bucket, group_prefix):
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
        'sessionId': credentials['AccessKeyId'].aws_access_key,
        'sessionKey': credentials['SecretAccessKey'].aws_secret_access_key,
        'sessionToken': credentials['SessionToken'].aws_session_token
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
        'Destination': 'https://s3.console.aws.amazon.com/s3/buckets/'+bucket+'?region=us-east-1&prefix='+group_prefix+'/inputs/&showversions=false',
        'SigninToken': signin_token['SigninToken']
    })
    federated_url = f'{aws_federated_signin_endpoint}?{query_string}'
    return federated_url

#: Teardown -----
def teardown(role):
    """
    Removes all resources for a certain role.

    :param role: The demo role.
    """
    for attached in role.attached_policies.all():
        role.detach_policy(PolicyArn=attached.arn)
        print(f"Detached {attached.policy_name}.")
    role.delete()
    print(f"Deleted {role.name}.")

def _deletion_filter(role):
    return role.role_name.startswith("sts-role-") and pytz.utc.localize(datetime.datetime.now()) > (role.create_date+timedelta(seconds=role.max_session_duration)).astimezone(pytz.utc)

#: Tears down all expired sts roles with the given prefix
def teardown_all():
    for role in filter(_deletion_filter,boto3.resource('iam').roles.all()):
        teardown(role)

def main():
    # Arguments:
    # python federation.py bucket_prefix group_prefix
    iam_resource = boto3.resource('iam')
    role = setup(iam_resource)
    sts_client = boto3.client('sts')
    return generate_credentials(role.arn, 'AssumeRoleDemoSession', sts_client, sys.argv[2], sys.argv[1]) 
if __name__=="__main__":
    main()