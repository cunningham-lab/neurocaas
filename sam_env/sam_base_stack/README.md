# SAM Base Stack
This is an AWS Serverless Application Model (SAM) application that is used as a preparation/debugging platform for all of the pipelines that we will be publishing as part of our NCAP paper. Given a group name as a parameter, it creates an S3 bucket for them to write into, an IAM user with read/write permissions to that bucket, and a nested set of lambda functions that depend on the pipeline in use.  

## Project Structure: 
This project is organized as follows: 
README.md: This file. 
src: Source code for lambda functions. Functions for individual pipelines, and bucket configuration as is required. 
    __init__.py
    utils.py
    config_tools.py
    lambda_funcs.py
template.yaml: SAM template defining all the relevant resources we will use. Note that the default behavior (without explicit parameter passage w.r.t. lambda functions) will generate a stack that just writes the name of the uploaded object like the hello world function.SampleEvent\_\default.json: Sample event for debugging. 

TODO: implement template.yaml
