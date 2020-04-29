# develop_blueprint

## NeuroCaaSAMI
```python
NeuroCaaSAMI(self, path)
```

This class streamlines the experience of building an ami for a new pipeline, or impriving one within an existing pipeline. It has three main functions:
1) to launch a development instance from amis associated with a particular algorithm or pipeline,
2) to test said amis with simulated job submission events, and
3) to create new images once development instances are stable and ready for deployment.

This class only allows for one development instance to be launched at a time to encourage responsible usage.

This class assumes that you have already configured a pipeline, having created a folder for it, and filled out the template with relevant details [not the ami, as this is what we will build here.]

Inputs:
path (str): the path to the directory for a given pipeline.


Example Usage:
```python
devenv = NeuroCaaSAMI("../../sam_example_stack/") ## Declare in reference to a particular NCAP pipeline
devenv.launch_ami() ## function 1 referenced above
### Do some development on the remote instance
devenv.submit_job("/path/to/submit/file") ## function 2 referenced above
### Monitor the remote instance to make sure that everything is running as expected, outputs are returned
devenv.create_devami("new_ami") ## function 3 referenced above
devenv.terminate_devinstance() ## clean up after done developing
```

### launch_ami
```python
NeuroCaaSAMI.launch_ami(self, ami=None)
```

Launches an instance from an ami. If ami is not given, launches the default ami of the pipeline as indicated in the stack configuration file. Launches on the instance type given in this same stack configuration file.

Inputs:
ami (str): (Optional) if not given, will be the default ami of the path. This has several text options to be maximally useful.
[amis recent as of 3/16]
ubuntu18: ubuntu linux 18.06, 64 bit x86 (ami-07ebfd5b3428b6f4d)
ubuntu16: ubuntu linux 16.04, 64 bit x86 (ami-08bc77a2c7eb2b1da)
dlami18: ubuntu 18.06 version 27 (ami-0dbb717f493016a1a)
dlami16: ubuntu 16.04 version 27 (ami-0a79b70001264b442)

### submit_job
```python
NeuroCaaSAMI.submit_job(self, submitpath)
```

Submit a submit file json to a currently active development instance. Will not work if the current instance is not live. Modified to the take config file, and create logging.
Inputs:
submitpath:(str) path to a submit.json formatted file.
Output:
(str): path to the output directory created by this function.
(str): path to the data file analyzed by this function.
(str): id of the command issued to the instance.


### submit_job_log
```python
NeuroCaaSAMI.submit_job_log(self, submitpath)
```

Inputs:
submitpath:(str) path to a submit.json formatted file.

### job_status
```python
NeuroCaaSAMI.job_status(self, jobind=-1)
```

method to get out stdout and stderr from the jobs that were run on the instance.
Inputs:
jobind (int): index giving which job we should be paying attention to. Defaults to -1

### job_output
```python
NeuroCaaSAMI.job_output(self, jobind=-1)
```

method to get out stdout and stderr from the jobs that were run on the instance.
Inputs:
jobind (int): index giving which job we should be paying attention to. Defaults to -1

### start_devinstance
```python
NeuroCaaSAMI.start_devinstance(self)
```

method to stop the current development instance.

### stop_devinstance
```python
NeuroCaaSAMI.stop_devinstance(self)
```

method to stop the current development instance.

### terminate_devinstance
```python
NeuroCaaSAMI.terminate_devinstance(self, force=False)
```

Method to terminate the current development instance.
Inputs:
force (bool): if set to true, will terminate even if results have not been saved into an ami.

### create_devami
```python
NeuroCaaSAMI.create_devami(self, name)
```

Method to create a new ami from the current development instance.

Inputs:
name (str): the name to give to the new ami.

### update_blueprint
```python
NeuroCaaSAMI.update_blueprint(self, ami_id=None, message=None)
```

Method to take more recently developed amis, and assign them to the stack_config_template of the relevant instance, and create a git commit to document this change.

Inputs:
ami_id:(str) the ami id with which to update the blueprint for the pipeline in question. If none is given, defaults to the most recent ami in the ami_hist list.
message:(str) (Optional) the message we associate with this particular commit.

### get_instance_state
```python
NeuroCaaSAMI.get_instance_state(self)
```

Checks the instance associated with the DevAMI object, and determines its state. Used to maintain a limit of one live instance at a time during development.

Outputs:
(dict): a dictionary returning the status of the instance asso




### check_running
```python
NeuroCaaSAMI.check_running(self)
```

A function to check if the instance associated with this object is live.

Outputs:
(bool): a boolean representing if the current instance is in the state "running" or not.

### check_clear
```python
NeuroCaaSAMI.check_clear(self)
```

A function to check if the current instance is live and can be actively developed. Prevents rampant instance propagation. Related to check_running, but not direct negations of each other.

Outputs:
(bool): a boolean representing if the current instance is inactive, and can be replaced by an active one.

