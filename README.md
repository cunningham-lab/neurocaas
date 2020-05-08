[![Build Status](https://travis-ci.com/cunningham-lab/neurocaas.svg?branch=master)](https://travis-ci.com/cunningham-lab/neurocaas)

Main repository for the [NeuroCAAS project](http://www.neurocaas.org), providing a neuroscience analysis platform using Infrastructure-as-Code (IaC).

This repository hosts all of the Code that makes up our IaC approach, with structure as described in the paper [Link to pdf here]
Structure: 
- paper (material specifically related to the NeuroCAAS paper)
- docs (documentation and developer guides)
- media (demo movies, slides, etc.)
- experiments (benchmarking code for NeuroCAAS on existing algorithms)
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
- SSM [link]
- voltage imaging pipeline [link]
- deep graph pose [link]
- gene spot finder

Future directions:
- website-based dev portal
- "super user" API (in code)
- GUI support 

To run our comparison analysis on your own infrastructure, navigate to the "experiments" directory and follow the directions found in the guide there. 
