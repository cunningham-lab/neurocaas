# This folder contains tests for the monitoring lambda functions that we have deployed. 
## The important folders are those that contain the code for each lambda function: 

- ec2_rogue_killer
- test_ec2_killer.py
- neurocaas_guardduty_develop.py
- neurocaas_guardduty_deploy.py

The file `lambda_function_imported.py` is a minimally modified version of ec2_rogue killer. 

The file `lambda_launch.py` launches lambda functions, both to localstack and to the real aws. It works for ec2-rogue-killer by hardcoded names, and should be makde more general
