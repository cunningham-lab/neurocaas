# README for tests. 
This folder contains tests run against various modules of the neurocaas source code. The paradigm for testing here is with localstack to mock out AWS resources whenever possible (exceptions include actually needing a remote AWS instance to be running so you can run SSM commands, certain quirks with permissions, etc). There are several indepenent pushes to write tests here, so we document the most relevant ones: 

## protocol_tests
These are unit tests for the AWS lambda functions that act as NeuroCAAS Job Managers (see the paper). The main job manager tests are in `test_submit_start.py` (including tests for the legacy widefield lambda function). The tests for postprocessing functions used for ensembling are in `test_postprocess.py`. We still need to (as of 8/1/21) write tests for the logging lambdas that monitor the state of ec2 instances and write budgeting logs from them (`test_log.py`). We also need to write test for the helper lambdas (`test_helper.py`) that back AWS Custom Resources that create and delete S3 folders.  

## prototype_tests
These are only test sketches- ignore. 

## devutils_tests
*Note: These tests depend upon you having a profile called testdev configured with the credentials given in ncap_iac/permissions/dev_policy.json*
These are tests for the developer tools that we developed and have since ported over into an independent `neurocaas_contrib` repo. Unlike the unit tests found there, these tests will check if the developer credentials stored in a local profile `testdev` will be able to conduct the required actions. We may want to port this over to that repo eventually.  

## fixture_generators
These are scripts to generate test resources from a past testing attempt- very thorough, but ignore for now. 

## permissions_tests
*Note: These tests depend upon you having a profile called testdev configured with the credentials given in ncap_iac/permissions/dev_policy.json*
These are general tests that check that certain permissions we have defined are well scoped for the roles we want the relevant people to play. There may be some redundancy here between this repo and devutils_tests- worth looking into. The file `test_devcreds.py` tests that developers can only launch instances if they have a certain combination of tags attached. The file `test_managementlambdas.py` tests the management lambda functions that we have built to monitor the activity of rogue instances. Unclear if this is updated to latest version of lambdas, but we should make it so. Finally the file `test_ssm_list_commands` makes sure that ssm is a valid way to check if the activity of an instance is as expected or not, and tests the actual AWS. .   

## utils_tests 
These tests perform basic checks of the template generation mechanisms that convert NeuroCAAS Blueprints to AWS Cloudformation Templates. In the future we could include more checks that can be deployed on the fly for static checking of a stack, as well as mocking deployment of stacks. 

## unit_tests
These tests are from a previous attempt to write tests for the repo, and include a mixture of different testing paradigms. The most useful is test_s3_jobmanager_utils.py, which tests the s3 functions in `protocols/utilsparam/s3.py`. The tests for other `utilsparam` modules would be great to get in place as well. There are actually tests for ec2 in protcol_tests/utilsparam_tests- look for others like this. 


The major remaining todo items regarding testing are the other `utilsparam` modules, a cleanup to figure out which tests are redundant, and mark integration tests that actually hit the AWS endpoint for critical functionality. These will in general be slower, and potentially cost money. These Continuous Integration tests can be prioritized or thrown away depending on the testing context.  Higher coverage in Continuous Integration  would also be good (right now it's only protocol_tests). The tests are also not entirely independent: some will complain about instances that are left around by other tests.  
