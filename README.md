Main repository for the [NeuroCAAS project](www.neurocaas.com "NeuroCAAS Homepage"), providing a neuroscience analysis platform using Infrastructure-as-Code (IaC).

This repository hosts all of the Code that makes up our IaC approach, with structure as described in the paper [Link to pdf here]
Structure: 
- paper (material specifically related to the NeuroCaaS paper)
- media (demo movies, slides, etc.)
- experiments (benchmarking code for NeuroCaaS on existing algorithms)
- ncap\_iac (the core code of the project)
    - ncap blueprints (code representing analysis pipelines.)
    - user profiles (code representing users.)
    - protocols (code representing job management coordination analysis pipelines and users.)
    - utils (utilities to compile the above code into the corresponding infrastructure. Interfaces with troposphere and the AWS CLI)


*Requires:*

- AWS CLI (configured with AWS Account)
- AWS SAM CLI
- Troposphere (python package)
- Boto3 (python package)
- jq (json parser)

Coming soon:
-SSM [link]
-voltage imaging pipeline [link]
-deep graph pose [link]
-gene spot finder

Future directions:
- website-based dev portal
- "super user" API (in code)
- GUI support 
