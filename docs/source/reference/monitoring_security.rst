Monitoring and Security on NeuroCAAS
==================================== 

- We implement monitoring of instance usage on NeuroCAAS via lambda functions. 

Here is the current layout:

"Soft cap" protections:
-----------------------

- test-ec2-killer
    - Kills all ec2 instances that are not exempt after 180 minutes of activity.
- ec2-rogue-killer
    - Kills all ec2 instances that are not on ssm, or explicitly provided with a timeout after 15 minutes of activity.

Exempt instances are given in an SSM parameter called exempt-instances 

“Hard cap functions” on total usage:
------------------------------------

- neurocaas-guardduty-develop
    - Stops all ec2 instances that have the developer security group after 2880 minutes of activity (2 days)
- neurocaas-guardduty-deploy
    - Stops all ec2 instances that have the deploy security group after 120 minutes of activity.

These functions provide a nice layer of security against unexpected usage in all cases except a ssm job that continues unnecessarily. Paired with user based budgets, this is a consistent system to monitor usage. 



