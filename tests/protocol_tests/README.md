In this folder, test_submit_start tests all of the big lambda functions we use to submit jobs, including those found in submit_start_legacy_wfield_preprocess.py. The folder test_create.py creates a local lambda function, which is useful to test the monitoring functions we have. 

The file test_postprocess.py tests the ensemble postprocessing that we built to launch another instance. 

The parts of the protocols module that are currently still untested are log.py and helper.py- log.py monitors instance state changes, and helper.py backs AWS custom resources for folder cretion and deletion. 

Regarding the utilsparam functions, the ec2 module is tested here, as is s3. 

The way in which we handle environment variables for lambda functions needs to change. We have them set in simevents/main_func_env_vars, we sometimes import them from the files env_vars.py in utilsparam. These should be standardized. env_vars is far more common right now. 
