Main repository for the NeuroCaaS project, providing a neuroscience analysis platform using Infrastructure-as-Code (IaC).

This repository hosts all of the Code that makes up our IaC approach, with structure as described in the paper [Link]
Structure: 
- paper (material specifically related to the NeuroCaaS paper)
- media (demo movies, slides, etc.)
- experiments (benchmarking code for NeuroCaaS on existing algorithms)
- ncap\_iac (the core code of the project)
    - ncap blueprints (code representing analysis pipelines.)
    - user profiles (code representing users.)
    - protocols (code representing job management coordination analysis pipelines and users.)

 



*Requires:*

AWS CLI (configured with AWS Account)

AWS SAM CLI

Troposphere (python package)

Boto3 (python package)

jq (json parser)
