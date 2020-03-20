#!/bin/bash
## This is just a tester to try out debugging of deployments. 
sam build -t test_template.json -m ../../lambda_repo/requirements.txt

sam package --s3-bucket ctnsampackages --output-template-file test_template_packaged.yaml

sam deploy --template-file test_template_packaged.yaml --stack-name repoteststack --capabilities CAPABILITY_NAMED_IAM
