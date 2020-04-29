# Things That NEED to be set for each pipeline
AMI = 'ami-04ebe747c2e33038c' # which image to boot from
INSTANCE_TYPE = 'p2.xlarge'  # instance type to launch.  # TODO make this adaptive

# Things That MAY change across different pipelines
REGION = 'us-east-1'          # which region to create instances in
SECURITY_GROUPS = ['launch-wizard-6']
IAM_ROLE = 'locanmf-s3-access'  # name of IAM role with SSM & S3 access
KEY_NAME = 'ss5513'          # ssh key to use for access

# Things That SHOULD NOT change across different pipelines
WORKING_DIRECTORY = '~/bin'                 # location of scripts on instance
COMMAND = '/home/ubuntu/bin/run.sh {} {} {} {} {} {} {} {}'  # command to run after booting
SHUTDOWN_BEHAVIOR = 'terminate'               # 'terminate' or 'stop' when done
CONFIG = 'params.yaml'
SUBMIT_FILE = 'submit.json'

# Things We Should Eliminate As Config Params
MISSING_CONFIG_ERROR = 'We need a config file to analyze data.'
EXECUTION_TIMEOUT = '172800'
LOGDIR = 'logs'
OUTDIR = 'outputs'
INDIR = 'inputs'
LOGFILE = 'lambda_log.txt'