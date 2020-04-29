# Things That NEED to be set for each pipeline
AMI = 'ami-0f000d7cdf823e092' # which image to boot from
INSTANCE_TYPE = 'c5.18xlarge'  # instance type to launch.  # TODO make this adaptive

# Things That MAY change across different pipelines
REGION = 'us-east-1'          # which region to create instances in
SECURITY_GROUPS = ['launch-wizard-6']
IAM_ROLE = 'ec2-ssm'  # name of IAM role with SSM & S3 access
KEY_NAME = 'ta_testkey'          # ssh key to use for access

# Things That SHOULD NOT change across different pipelines
WORKING_DIRECTORY = '~/bin'                 # location of scripts on instance
COMMAND = 'cd ../../../../home/ubuntu; bin/run.sh {} "{}"'  # command to run after booting
SHUTDOWN_BEHAVIOR = 'stop'               # 'terminate' or 'stop' when done
CONFIG = 'config.yaml'

# Things We Should Eliminate As Config Params
MISSING_CONFIG_ERROR = 'We need a config file to analyze data.'
EXECUTION_TIMEOUT = '172800'
LOGDIR = 'logs'
OUTDIR = 'results'
INDIR = 'inputs'
LOGFILE = 'lambda_log.txt'
