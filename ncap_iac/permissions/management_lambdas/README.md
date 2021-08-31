# This folder contains tests for the monitoring lambda functions that we have deployed. 
## The important folders are those that contain the code for each lambda function: 

- ec2_rogue_killer
- test_ec2_killer.py
- neurocaas_guardduty_develop.py
- neurocaas_guardduty_deploy.py

The file `lambda_function_imported.py` is a minimally modified version of ec2_rogue killer. 

The file `lambda_launch.py` launches lambda functions, both to localstack and to the real aws. It works for ec2-rogue-killer by hardcoded names, and should be made more general

Below we explain the logic of each lambda function. 

### ec2_rogue_killer.py (global, tag-sensitive)
- This function collects all active instances, and then filters out those that are exempt from processing, those that are within their timeout, and those that have an ssm command. It aims to stop all others. This should catch most activity off the bat. 

### test_ec2_killer.py (global, tag-agnostic)
- This function collects all active instnaces, and then filters out those that are exempt. If any others are active past a global graceperiod, they get turned off. 

### neurocaas_guardduty_develop.py (group based, tag-agnostic)
- The develop function doesn't care about timeouts, just a global graceperiod of however many hour (maybe 2 days). 

### neurocaas_guardduty_deploy.py (group based, tag-sensitive)
- The deploy function waits until each instance in the deploy group's timeout expires, and then evaluates if it's active (greater than 5% cpu utilization) and if it has an ssm command. If not either of those things, it gets deleted. 


The tag-agnostic functions are part of an older system that is basically built in for redundancy. We can use super long timeouts here, and maybe build in a notification system around them. 
The tag-sensitive functions are important. If we have confidence in the future, we should move our whole system to them- remove test_ec2_killer and convert the develop one to be tag sensitive.  

Todos: 
1. Convert develop to tag-sensitive frakework. Basically the same as deploy, just with tags.  
2. Give an additional grace period with rogue_killer so the security group functions can get to security group functions and turn them off first.
3. delete test_ec2_killer or convert to something with notifications. 
