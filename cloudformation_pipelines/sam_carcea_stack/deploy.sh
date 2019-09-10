#!/bin/bash

sam build -t compiled_template.json -m ../lambda_repo/requirements.txt

sam package --s3-bucket ctnsampackages --output-template-file compiled_packaged.yaml

sam deploy --template-file compiled_packaged.yaml --stack-name carceamonitored --capabilities CAPABILITY_NAMED_IAM
