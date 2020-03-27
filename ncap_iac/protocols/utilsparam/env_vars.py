import os 

os.environ["IAM_ROLE"] = "pmd-s3-ssm"
os.environ["KEY_NAME"] = "ta_testkey"
os.environ["SECURITY_GROUPS"] = "launch-wizard-34"
os.environ["SHUTDOWN_BEHAVIOR"] = "terminate"
