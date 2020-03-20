# debug_ami

## launch_default_ami
```python
launch_default_ami(path)
```

This function reads the configuration file of a given pipeline, extracts the default ami, and launches it on the default instance type.

Inputs:
path (string): the path to the folder representing the pipeline that you would like to edit.

## test_instance
```python
test_instance(instance_id, pipelinepath, submitpath)
```

Uses SSM manager to send a RunCommand document to a given instance, mimicking the way jobs would be sent to the instance by the user. Assumes that there is data at the S3 path referenced by the submit file that you give.


Inputs:
instance_id (str): the id of the instance (starts with i-) that you would like to send a command to. The instance must have ssm manager installed in order to run commands.
pipelinepath (str): the path to the folder representing the pipeline that you would like to edit.
submitpath (str): the path to the submit file that references data to be analyzed, and configurations to be used

## DevAMI
```python
DevAMI(self, path)
```

This class streamlines the experience of developing an ami within an existing pipeline. It has three main functions: 1) to launch a development instance from amis associated with a particular algorithm or pipeline, 2) to test said amis with simulated job submission events, and 3) to create new images once development instances are stable and ready for deployment.

The current instantiation of this class only allows for one development instance to be launched at a time to encourage responsible usage.

Inputs:
path (str): the path to the directory for a given pipeline.


Example Usage:
```python
devenv = DevAMI("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
devenv.launch_ami() ## function 1 referenced above
### Do some development on the remote instance
devenv.submit_job("/path/to/submit/file") ## function 2 referenced above
### Monitor the remote instance to make sure that everything is running as expected, outputs are returned
devenv.create_devami("new_ami") ## function 3 referenced above
devenv.terminate_devinstance() ## clean up after done developing
```

### get_instance_state
```python
DevAMI.get_instance_state(self)
```

Checks the instance associated with the DevAMI object, and determines its state. Used to maintain a limit of one live instance at a time during development.

Outputs:
(dict): a dictionary returning the status of the instance asso




### check_running
```python
DevAMI.check_running(self)
```

A function to check if the instance associated with this object is live.

Outputs:
(bool): a boolean representing if the current instance is in the state "running" or not.

### check_clear
```python
DevAMI.check_clear(self)
```

A function to check if the current instance is live and can be actively developed. Prevents rampant instance propagation. Related to check_running, but not direct negations of each other.

Outputs:
(bool): a boolean representing if the current instance is inactive, and can be replaced by an active one.

### launch_ami
```python
DevAMI.launch_ami(self, ami=None)
```

Launches an instance from an ami. If ami is not given, launches the default ami of the pipeline as indicated in the stack configuration file. Launches on the instance type given in this same stack configuration file.

Inputs:
ami (str): (Optional) if not given, will be the default ami of the path.

### submit_job
```python
DevAMI.submit_job(self, submitpath)
```

Submit a submit file json to a currently active development instance. Will not work if the current instance is not live.
Inputs:
submitpath:(str) path to a submit.json formatted file.

### job_status
```python
DevAMI.job_status(self, jobind=-1)
```

method to get out stdout and stderr from the jobs that were run on the instance.
Inputs:
jobind (int): index giving which job we should be paying attention to. Defaults to -1

### job_output
```python
DevAMI.job_output(self, jobind=-1)
```

method to get out stdout and stderr from the jobs that were run on the instance.
Inputs:
jobind (int): index giving which job we should be paying attention to. Defaults to -1

### start_devinstance
```python
DevAMI.start_devinstance(self)
```

method to stop the current development instance.

### stop_devinstance
```python
DevAMI.stop_devinstance(self)
```

method to stop the current development instance.

### terminate_devinstance
```python
DevAMI.terminate_devinstance(self, force=False)
```

Method to terminate the current development instance.
Inputs:
force (bool): if set to true, will terminate even if results have not been saved into an ami.

### create_devami
```python
DevAMI.create_devami(self, name)
```

Method to create a new ami from the current development instance.

Inputs:
name (str): the name to give to the new ami.

## DevAMI_full
```python
DevAMI_full(self, path)
```

### submit_job
```python
DevAMI_full.submit_job(self, submitpath)
```

Submit a submit file json to a currently active development instance. Will not work if the current instance is not live. Modified to the take config.
Inputs:
submitpath:(str) path to a submit.json formatted file.

