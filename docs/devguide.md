Introduction
============

Neuroscience Cloud Analysis As a Service welcomes external developers to
deploy their existing analyses onto our platform. Once analyses are
built, they can be loaded onto the website interface for NeuroCAAS
seamlessly where they can be accessed by users in the neuroscience community. 

In this guide, we will describe a process to _incrementally 
automate_ all of the steps you would need to take to set up and use your analysis. 
This process includes automated installation and build (which you may recognize from 
Docker-like services), but also includes setup of hardware, scripting 
of your analysis workflow, and data transfer between 
the machine where the compute is happening and a requesting user.  

At the core of the process is a *blueprint* that records the steps you would like to 
automate, as you determine them in the course of the development process. 

## End Goal
The goal is to offer data analysis to users in such a way that they can analyze
their data without ever having to purchase, configure, or host analyses on their
own machines. This goal follows the "software as a service" model that has become popular in industry.

In this figure, you can see the resources and workflow that you will be able to 
support with your analysis at the end of the development process: 
<img src="./images/Fig2_backend_12_14.png" />

Key Points:
- For users, data analysis can be done entirely by interacting with data storage in AWS [S3 buckets](https://aws.amazon.com/s3/) (more on setting this up later). Data storage is already structured for them, according to individual analyses and user groups.  
```bash
    s3://{analysis_name}   ## This is the name of the S3 bucket
    |- {group_name}        ## Each NeuroCAAS user is a member of a group (i.e. lab, research group, etc.) 
       |- configs
       |- inputs
       |- submissions
       |  |- {id}_submit.json 
       |- results
          |- job_{timestamp}
             |- logs
             |- process_results
```

 When users want to trigger a particular analysis run, they upload a file indicating the data and parameters they want to analyze to a special directory called `submissions` (see the figure for content of this file). This upload triggers the automatic VM setup process described above, and users simply wait for the results to appear in a separate, designated subdirectory (`results`). Although shown as file storage here, most users will use NeuroCAAS through a web client that automates the process of uploading submission files.
This S3 bucket and the relevant directory structure will be generated once you deploy your analysis scripts (see section: Deploying your blueprint). 
If you want to see how the user interacts with this file structure, sign up for an account on [neurocaas.org](neurocaas.org). 
- Your analysis will be hosted on cloud based virtual machines (VMs). These machines are automatically set up with your analysis software pre-loaded on them, and run automatically when given a dataset to analyze. The main point of this guide is to figure out the set of steps that will make this happen for your particular analysis, and record them in a document called a _blueprint_. 
- A single virtual machine is  *entirely dedicated* to running your analysis on a given dataset. Once it is done analyzing a dataset, it will terminate itself. This means there are no history effects between successive analysis runs: each analysis is governed only by the automatic setup procedure described in your blueprint.  
 
   


We’ll describe the process of developing analyses for
NeuroCAAS in three steps: 

1. Choosing hardware and computing environment 

2. Setting up your automatic analysis runs 

3. Testing and deployment. 

All steps are available via a python and shell
script based API. Development will follow a principle of Infrastructure
as Code (IaC), meaning that all of your development steps will be
documented in code as you build.

Prerequisites
=============

In order to follow the steps listed here, you will need the following
installed on your local machine:

-   An AWS account (n.b. specific instructions below if developing on
    the Center for Theoretical Neuroscience account).

-   An IAM user with programmatic access on that account (i.e. access
    key and secret access keys)
    (<https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html>)

-   A local clone of the [NeuroCAAS Repository](https://github.com/cunningham-lab/ctn_lambda/tree/reorganize).

-   Custom resources for ssh-key management available at this repo:
    <https://github.com/binxio/cfn-secret-provider>

-   jq 1.6 (a json parser)- *install via brew/apt-get*

-   AWS CLI. -
    (<https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html>)

-   AWS Sam CLI. Additional command line tools for serverless
    applications.
    <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>

-   Docker (for the AWS Sam CLI)- *install via Docker homepage-referenced in SAM CLI installation*.

-   Anaconda (<https://www.anaconda.com>).

First verify your aws cli installation by running:

`% aws configure`

When prompted, enter the access key and secret access key associated
with your IAM user account, as well as the AWS region you are closest
to. IMPORTANT: If using the CTN AWS account to develop, please set your
AWS region to be **us-east-1**. Next verify your conda installation by
running:

`% conda list`

Then create a new environment as follows:

`% conda create -n neurocaas python=3.6`

Note: the argument following the -n flag is the name of the virtual
python environment you are creating. We strongly recommend that you name
your environment neurocaas, as it is referenced by bash scripts
referenced later (in particular, configure.sh and fulldeploy.sh). If you
do not name your environment neurocaas, please change the “source
activate” commands correspondingly. Now move into the root directory of
the cloned neurocaas repo:

`% cd /path/to/local/neurocaas/`

Activate your new environment, and install necessary packages by
running:

`% conda activate neurocaas`

`% conda install pip`

`% pip install -r requirements.txt`

`% pip install .`

Initializing NeuroCAAS
======================

*If you are developing within the CTN account, skip this first step, and
start with the `bash print\_privatekey.sh` command*

To initialize NeuroCAAS, first follow the installation instructions for
the binxio secret provider stack:
<https://github.com/binxio/cfn-secret-provider>. Navigate within the
repository to:

`neurocaas/ncap_iac/ncap_blueprints/utils_stack`

Now run the following command:

`% bash initialize_neurocaas.sh`

This will create the cloud resources necessary to deploy your resources
regularly and handle the permissions necessary to manage and deploy
cloud jobs, and ssh keys to access resources on the cloud. The results
of initialization can be seen in the file
`global_params_initialized.json`, with the names of resources listed. If
you encounter an error, consult the contents of the file
`neurocaas/ncap_iac/ncap_blueprints/utils_stack/init_log.txt`, and post
it to the neurocaas issues page.

This process will also generate an ssh key, that is not printed to the
repo for security reasons. In order to retrieve your ssh key, navigate
within the repository to:

`neurocaas/ncap_iac/ncap_blueprints/utils_stack`. Type the following
command:

`% bash print_privatekey.sh > securefilelocation/securefilename.pem`

Where “securefilelocation/securefilename.pem” is a file NOT under
version control. **IMPORTANT: We strongly recommend you keep this file
in separate, secure directory not under version control. If this key is
exposed, it will expose the development instances of everyone on your
account**. You will reference this key when developing a machine image
later. Finally, change the permissions on this file with:

`% chmod 400 securefilelocation/securefilename.pem`

Initializing a blueprint
========================

To start, we will need to build a computing environment where your
analysis lives along with all of its required dependencies. To do this,
we first need to initialize a blueprint for your stack. Navigate to the
`ncap_blueprints` directory, and run the command:

`% bash iac_utils/configure.sh "name of your analysis algorithm"`

Where the argument passed must be restricted to lowercase letters,
numbers, and dash marks (-). This will create a folder with the
specified name. If you navigate into this folder, you can see the
blueprint that specifies an analysis pipeline. 

This blueprint contains all of the details that specify the different resources 
and services that will support your analysis. When initializing an analysis, 
we can leave most of these fixed, but there are a few that we should go over: 
The parameters that you will probably change are:

- STAGE: This parameter describes different stages of pipeline development. It should be set to "webdev" while initializing a blueprint.

- Lambda.LambdaConfig.INSTANCE\_TYPE: INSTANCE\_TYPE specifies the hardware configuration that is run by
default (can be changed on demand) and is selected from a list of instance types available on AWS.

Important parameters to keep in mind for later: 
- Lambda.LambdaConfig.AMI: AMI specifies the Amazon Machine Image where your software and dependencies are installed, and contains most of the analysis-specific configuration details that you must specify. As you develop, you will save your progress into different AMIs so they can be linked to the blueprint through this parameter.

- Lambda.LambdaConfig.COMMAND: COMMAND specifies a bash command that will be run on your remote instance [with parameters specified in the main script section] to generate data analysis. You will most likely not have to change this command, but it is the principal way in which we will be starting analyses on a remote instance. 

For now, remove all Affiliates from the UXData area except for
“debuggers” we will return to these later.

Once you have configured a blueprint, navigate to the “dev\_utils”
folder in the “ncap\_blueprints” directory, and start up IPython. The
bulk of building a machine image will be done through an interactive,
Python based API, described next.

Building a machine image
========================

To handle image build and development, we have built a custom class to
interface with the python AWS SDK, boto3. Make sure that your
environment has the required dependencies listed in the Prerequisites
section. Then import the “NeuroCaaSAMI” class from the
develop\_blueprint module, and give it the path to the folder you just
configured:

`>>> from develop_blueprint import NeuroCaaSAMI`

`>>> devami = NeuroCaaSAMI("../path_to_configured_folder")`

By calling methods on declared objects, you can create, destroy, develop
and test machine images easily, without directly interfacing with the
cloud. The declared object reads the blueprint that you have built, and
intelligently uses the information there to streamline development.

Launching a machine image
-------------------------

If you are working with a blueprint where you have already specified an
AMI, you can simply call :

`>>> devami.launch_devinstance(timeout =60)`

Which will launch the AMI listed in your blueprint. CAUTION: The timeout parameter is the amount of time you are requesting that a development instance be active for, in minutes. By default, it is set at 1 hour. After this timeout passes, your instance can be stopped at any time, so be careful! 

If you need to check the time remaining on your instance, run the command `devami.get_lifetime()`. You can also extend the lifetime of your instance by running `devami.extend_lifetime(additional_time)`, where additional time is the additional number of minutes you are requesting.

If starting with a newly configured blueprint, first select an EC2
instance type from the available list:
<https://aws.amazon.com/ec2/instance-types/>

Then call:

`>>> devami.launch_devinstance(ami = string, timeout = 60)`

Where string is the id of an AMI you like, formatted as (“ami-xxxxxxxx”)
(you can find many on the AWS marketplace). If you do not have a
particular AMI id in mind, you can also pass one of the following
special codes:

-   “ubuntu18”: ubuntu version 18, x86.

-   “ubuntu16”: ubuntu version 16 x86.

-   “dlami18”: AWS conda deep learning ami
    <https://aws.amazon.com/blogs/machine-learning/new-aws-deep-learning-amis-for-machine-learning-practitioners/>,
    with pre-installed deep learning libraries on ubuntu 18, x86.

-   “dlami16”: like dlami18, but on ubuntu16, x86.

NOTE: These codes have been tested with a variety of x86 (intel based)
instances (m5 series, m5a series, p2 and p3 series). If you plan to use
non-x86 based instances, (such as the ARM based a1 series) please look
up the AMI id for the relevant OS distribution, and pass this id as an
argument. 

Calling this method will initialize an instance for you, and
then provide you with the ip address of that initialized instance. You
can then ssh into the instance with the key that you retrieved when
initializing NeuroCAAS, like so:

`>>> ssh -i /path/to/your/local/sshkey ubuntu@{ip address}`

Please note that if you use a custom ami, you may be prompted to log in
as root, or ec2-user instead of ubuntu.

If you ever need to close the ipython console, you can always
re-associate a new instance of the NeuroCaaSAMI object to your development 
instance with the following code: 

```
>>> devami = NeuroCaaSAMI("../path_to_configured_folder")
>>> devami.assign_instance(instance_id)
>>> devami.start_devinstance(timeout =60)
>>> ip = devami.ip
```

Note that if you restart your development instance, the requested timeout will be reset (default is 1 hour again).

Developing a machine image into an immutable analysis environment
-----------------------------------------------------------------

After connecting to your remote instance via ssh, you can download your
code repositories and dependencies to it, and test basic functionality.
Once this is done, you will have to clone the repository
[neurocaas\_contrib](https://github.com/cunningham-lab/neurocaas_contrib)
into the user’s remote directory. This repo contains utility functions 
to connect software that lives on the instance with data on the user side,
and send logs to the users as analysis proceeds. 
It also contains examples of projects that show how to use these utility functions.
We will now explain the workflow for developing a script with the neurocaas_contrib repository. 


#### Main script
All NeuroCAAS analyses should be triggered by running a central bash script called run\_main.sh.
This script ensures that all jobs run on NeuroCAAS are managed and logged correctly. 
This script takes 5 arguments, as follows:   

`% bash run_main_cli.sh $bucketname $path_to_input $path_to_result_dir $path_to_config_file $path_to_analysis_script`

The first four parameters refer to locations in Amazon S3 where the inputs and results of this analysis will be stored. 
These parameters correspond to the directory structure given in the "end goals" section as follows: 
- $bucketname: {analysis\_name}
- $path\_to\_input: {group\_name}/inputs/name\_of\_dataset
- $path\_to\_result\_dir: results/job\_{timestamp}
- $path\_to\_config\_file: {group\_name}/configs/name\_of\_config\_file
These will be automatically filled in by NeuroCAAS when users request jobs, 
but can be manually filled in for certain test cases. For more info see the section, "Testing a machine image."

The fifth parameter, $path\_to\_analysis\_script, is a analysis-specific bash script, that will be run inside the run\_main.sh script. It will call all of the analysis source code
, transfer data in to the instance, etc. This will be the subject of the next subsection, Analysis script. 

This script-in-a-script organization ensures two things:

- Reliability of logging. Logging progress mid-analysis can be a delicate process, and standardizing it 
in a single main script helps to ensure that developers will not have to worry about this step.

- Correct error handling. In the event that analysis scripting runs into an error, we want to be able to detect and 
catch these errors. We can do so much more easily if all relevant code is executed in a separate script, ensuring that
the relevant steps necessary to report the error to the user, and run appropriate cleanup on the instance are carried out. 

In the rest of this subsection, we will walk through the content of run\_main.sh. This will be more of a reference for interested parties.
If you would like to get started developing your own analysis, you can jump ahead to the next subsection, Analysis script. 

##### Content of run\_main.sh
```
4 execpath="$0"
5 scriptpath="$(dirname "$execpath")/ncap_utils"
6 ## Get in absolute path loader: 
7 source "$scriptpath/paths.sh"
```

First, we get the absolute path to the subdirectory containing our utility functions, and load in path management functions from paths.sh

```
10 set -a
11 neurocaasrootdir=$(dirname $(get_abs_filename "$execpath"))
12 set +a
```

Throughout this script, we will declare a set of environment variables that can be accessed by the child analysis script. 
The first of these is $neurocaasrootdir- the absolute path to the neurocaas_contrib repo. 

```
14 source "$scriptpath/workflow.sh"
15 ## Import functions for data transfer 
16 source "$scriptpath/transfer.sh"
```

We have previously mentioned that this repo contains a variety of helper functions to connect the remote instance with a user. 
These shell functions are stored separately in the file workflow.sh (for setting up logging files), and transfer.sh 
(for transferring data between your instance and the user.) By sourcing them, we make them available to use in this script.

```
27 set -a
28 parseargsstd "$1" "$2" "$3" "$4"
29 set +a
30
31 echo $bucketname >> "/home/ubuntu/check_vars.txt" 
32 echo $groupdir >> "/home/ubuntu/check_vars.txt" 
33 echo $resultdir >> "/home/ubuntu/check_vars.txt" 
34 echo $processdir >> "/home/ubuntu/check_vars.txt" 
35 echo $dataname >> "/home/ubuntu/check_vars.txt" 
36 echo $inputpath >> "/home/ubuntu/check_vars.txt" 
37 echo $configname >> "/home/ubuntu/check_vars.txt" 
38 echo $configpath >> "/home/ubuntu/check_vars.txt" 
```

In this step, we will declare more environment variables that will be passed to our analysis script. This is perhaps the most significant step 
carried out by the run\_main.sh script, as these environment variables make it much easier to move and manipulate data. The function 
parseargsstd is imported from the workflow.sh script.
As follows, these variables specify certain paths inside the directory structure described in the background.
- $bucketname <-> analysis\_name 
- $groupdir <-> group\_name 
- $resultdir <-> results/job\_{timestamp} 
- $processdir <-> results/job\_{timestamp}/process_results
- $dataname <-> the basename of a datafile in the inputs directory.
- $inputpath <-> {group\_name}/inputs/datafile
- $configname <-> the basename of a config file in the configs directory.
- $configpath <-> {group\_name}/configs/configfile

These variables are then printed to the file /home/ubuntu/check\_vars.txt where they can be examined for debugging purposes.

```
40 ## Set up Error Status Reporting:
41 errorlog_init 
42 
43 ## Set up STDOUT and STDERR Monitoring:
44 errorlog_background & 
45 background_pid=$!
46 echo $background_pid, "is the pid of the background process"
```

Both errorlog\_init and errorlog\_background are functions imported from the workflow.sh file. The file errorlog\_init initially fetches a 
status file from the specific job directory in the s3 bucket and prepares it to be written to. This status file contains info on the commands run on the instance, 
the cpu utilization, and the high-level status of the job (INITIALAIZING, IN PROGRESS, SUCCESS or FAILED). The function errorlog\_background is then run as a background process,  
continually updating a local copy of the status file as well as other logging data. Finally we save the process id of this background process to terminate it later. 

```
48 ## MAIN SCRIPT GOES HERE #####################
49
50 bash "$5" > "$neurocaasrootdir"/joboutput.txt 2>"$neurocaasrootdir"/joberror.txt
51 ##############################################
52 ## Cleanup: figure out how the actual processing went. 
53 ## MUST BE RUN IMMEDIATELY AFTER PROCESSING SCRIPTS TO GET ERROR CODE CORRECTLY.
54 errorlog_final
```

Now, we can finally run the bash script given to us as the fifth argument of run\_main.sh. We assume that it does not take any arguments, but it will have access to all 
of the environment variables declared above, which should be sufficient to perform all necessary tasks. Note that stdout and stderr are written to the neurocaas_contrib base directory, 
allowing us to evaluate job status by eye as well. The function errorlog_final (from workflow.sh) performs a final update to the logging files and changes their status to "SUCCESS" or "FAILURE" depending on the 
result of running line 50.  

```
55 ## Once this is all over, send the config and end.txt file
56 aws s3 cp s3://"$bucketname"/"$configpath" s3://"$bucketname"/"$groupdir"/"$processdir"/$configname
57 aws s3 cp "$neurocaasrootdir"/update.txt s3://"$bucketname"/"$groupdir"/"$processdir"/
58 kill "$background_pid"
```

Finally, we run some cleanup: we will transfer the configuration file used to run this job to the output directory for reproducibility (line 56),
send an empty file to indicate that this stage of the job is complete (line 57), and finally kill the background logging process (line 58). The actual machine shutdown is handled by 
a higher level system to improve reliability and stability. Note that here in lines 56-57 we use the declared data path variables extensively. This will be the case in the actual analysis script as well.  

#### Analysis script
TL;DR from the previous section: 
- We will assume the analysis script takes no parameters. Instead, you have access to certain environment variables declared in run_main.sh that should make it easier to transfer data to and from the user. These variables correspond to the 
directory structure explained in the background, as follows: 
    - $bucketname <-> analysis\_name 
    - $groupdir <-> group\_name 
    - $resultdir <-> results/job\_{timestamp} 
    - $processdir <-> results/job\_{timestamp}/process_results
    - $dataname <-> the basename of a datafile in the inputs directory.
    - $inputpath <-> {group\_name}/inputs/datafile
    - $configname <-> the basename of a config file in the configs directory.
    - $configpath <-> {group\_name}/configs/configfile
We will assume that the analysis script is located in a subdirectory of neurocaas\_contrib, as neurocaas\_contrib/analysis\_name/run\_analysis\_name.sh


As a first example, let's take a look at the directory neurocaas\_contrib/mock. 
This directory contains a simple example analysis script [(run_mock_internal.sh)](https://github.com/cunningham-lab/neurocaas_contrib/blob/reorganize/mock/run_mock_internal.sh). 
This script pulls an integer parameter `$waittime` from a configuration file and waits that amount of time before exiting. 
We can walk through this script line by line: 

```
1 #!/bin/bash
2
3 ## Import functions for workflow management. 
4 ## Get the path to this function: 
5 execpath="$0"
6 echo execpath
7 scriptpath="$(dirname "$execpath")/ncap\_utils"
8
9 source "$scriptpath/workflow.sh"
10 ## Import functions for data transfer 
11 source "$scriptpath/transfer.sh"

```

This initial block of code sources utility functions from the directory neurocaas_contrib/ncap_utils.
These shell functions are stored separately in the file workflow.sh (for setting up logging files), and transfer.sh 
(for transferring data between your instance and the user.)

```
13 ## Set up error logging. 
14 errorlog
```

The function `errorlog` is imported from the file workflow.sh. It records every line of this bash script after it is executed, 
and writes it to the json file neurocaaas_contrib/ncap_utils/statusdict.json. This file will be delivered back to the user, so that
the user has a running log of what command is running on the instance, as well as other information. Importantly this function also sets the -e flag on the script, 
indicating that it will exit if any errors are encountered.  

```
21 #source .dlamirc
22
23 export PATH="/home/ubuntu/anaconda3/bin:$PATH"
24
25 source activate epi
```

Keep in mind that when these scripts are run, they will not be run as a user, but rather as root. 
This can introduce some gotchas- if you are working with the AWS deep learning AMI, you will need to run 
`source .dlamirc` to establish the correct links between the instance and its GPU device(s). Likewise, 
you will have to manually append the user's anaconda bin to the path before running `source activate {}` to start a conda environment. 
In general, it's a good idea to test the analysis script as root by running `sudo -i` and navigating to the user's directory to see 
if there are any other issues.  
 
```
27 ## Declare local storage locations: 
28 userhome="/home/ubuntu"
29 datastore="epi/scripts/localdata/"
30 configstore="/home/ubuntu/" 
31 outstore="mock_results/"
32 ## Make local storage locations
33 accessdir "$userhome/$datastore" "$userhome/$outstore"
```

In general, it's useful to organize local analogues for the input, config, and results directories, so that you can just copy directories wholesale from s3 to the instance or vice versa. 
Here we've designated $datastore as the input location, the root user's home directory as the config storage directory, and $outstore as the output location (though this analysis won't have any output). 
The function accessdir (line 33) will then create these folders (and designate them as read/writable to all users) to prepare for data transfer. 

```
35 ## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
36 download "$inputpath" "$bucketname" "$datastore"
37
38 ## Stereotyped download script for config: 
39 download "$configpath" "$bucketname" "$configstore"
```

Here we're referencing the environment variables inherited from run_main.sh, and using them to download data and configuration files from the relevant locations in Amazon S3 to the locations that we designated. 
Note that you are also free to use the aws cli (`aws s3 cp` or `aws s3 sync`) to fetch data and configs from S3 as well. The function `download` can be found in the transfer.sh file.  

```
43 waittime=$(jq .wait "$configstore/$configname")
44 sleep $waittime
```

This is the meat of the script. Now the input data and configuration files are in known locations ($datastore and $configstore), and can be referenced by known names (the variables $configname and $dataname) 
inherited from run_main.sh. These parameters can then be passed to any local analysis routine. In this case, as a minimal example, we are simply getting an integer parameter from the configuration file, 
and waiting that amount of time. One notable difference is that this example has no output that we would generally want to route to the $outstore directory. Figuring out what goes here is the majority of the conceptual work necessary
to load an analysis on NeuroCAAS.  

```
50 cd "mock_results"
51 aws s3 sync ./ "s3://$bucketname/$groupdir/$processdir"
```

The last thing we do in this script is to move to our output directory (which is empty), and upload the results to the relevant directory in S3, as given by our inherited environment variables. Note that here we 
use the variable $processdir, instead of $resultdir, so that we can avoid dumping results directly into the job subdirectory. If you would like to write your own logs as jobs proceed, you can do so by writing them to 
the folder s3://$bucketname/$groupdir/$resultdir/logs/, where automatic logs will also be written. 

If any of the steps above fail, the flag -e set in the function errorlog will ensure that the whole script exits. This will be used to catch and report failure cases back to the main script. If you want to be fancy, 
you can set up input parsing before starting analyses. Error messages can be sent to STDOUT, and will be reported back to the user via auto-generated logs.    


For more involved examples, see neurocaas\_contrib/{caiman,dlc,epi,locanmf,pmd}). The corresponding run\_{analysis} files should provide an idea of how this basic framework can be used to serve a variety of different 
analysis needs, including analyses that require several different input modalities (locanmf), have train and test modes with different inputs (dlc), or accept parameters in different formats (caiman). 

When it comes to testing an analysis script, we recommend doing so AFTER initially deploying your blueprint. This means that once you have tested your main analysis call (the analogue of lines 43 and 44 in the analysis script)
and have a preliminary script, you can save your machine image, clean up, and deploy your updated blueprint before starting up another instance from the python console. 
 This will create the folder structure discussed in the background section, letting you can upload test data and configs to the relevant locations in S3.  

If you want to test your script locally, you can do so by:
- 1) creating an s3 bucket with the structure shown in the background section
- 2) uploading test data and config files to the relevant locations  
- 3) calling run_main.sh with the relevant variables.  

Note that you may get many loud errors from the background process, as it will not be able to find the appropriate logging files in the s3 bucket, but this should not interrupt your main analysis script.  

Saving your machine image
-------------------------

After you have written a script and tested it locally, you should save
your machine image. In order to do so, return to your IPython console,
and run the command:

`>>> devami.create_devami(name)`

where the name is an identifier you will provide to your newly created
image. You can update your blueprint with this new image by running:

`>>> devami.update_blueprint(ami_id,message=None)`

Where ami\_id is the id of the ami provided as output to the create
command. Not providing an ami\_id will update with the last image that
you have created. Updating the blueprint will also automatically
generate a two git commits for the repo, documenting the state of the
blueprint before and after you performed this update for reproducibility
purposes. The message command, if provided, will be a message associated
with this pair of git commits for readability.

Cleaning up
-----------

After you have saved your machine image and updated your blueprint, you
can terminate it by running:

`>>> devami.terminate_devinstance()`

If you have not created an image before doing so, you will be prompted
for confirmation. If you would like to step away from developing for a
while, you can run:

`>>> devami.stop_devinstance()`

And conversely,

`devami.start_devinstance()`

Note that you can launch new development images, but you can only do so
after terminating your current one to prevent losing track of
development.

Deploying your blueprint
------------------------

Once you have a working image, it is useful to deploy it as a NeuroCAAS
analysis, to perform further testing using the access configuration a
user would have (see “Testing a machine image”). To do so, navigate to
the “neurocaas\_blueprints” directory, and run the following command:

`% bash iac_utils/fulldeploy.sh "name of your pipeline here"`

This will run all the steps necessary to build the cloud resources
corresponding to your blueprint, and you can test it further from the
python API after adding some test users.

#### Testing a machine image

IMPORTANT NOTE: this step can only be done AFTER initially deploying a
blueprint (Step 6). Our Python development API has the capacity to
*mock* the job managers that parse user input. In order to test your
machine image including the inputs and outputs that a user would see,
follow these steps: 1) you upload data and configuration files to the deployed s3
bucket, just as a user would. 2) you manually write a submit.json file,
like below:

    {
        "dataname":"{group_name}/inputs/data.zip",
        "configname":"{group_name}/configs/config.json",
        "timestamp": "debugging_identifier"
    }

Where the dataname and configname values point to the data that you
uploaded in step 1, and {group\_name} corresponds to the group name 
depicted in the user-side data organization diagram. If you followed 
the instructions regarding blueprint configuration, this will most likely 
be "debuggers".

Then, run

`>>> devami.submit_job(submitpath)`

Where submitpath is the path to the submit file you wrote. This will
trigger processing in your development instance as a background process
(you can observe it with top). If you don't remove the instance shutdown 
command when you are running this test, your instance will stop after the processing finishes. You can monitor the
status and output of this job as it proceeds locally from python with:

`>>> devami.job_status(index)`

`>>> devami.job_output(index)`

Where index gives the number of job you would like to analyze (default
is -1, the most recent). The results themselves will be returned to AWS
S3 upon job completion.


#### Adding users

Once your blueprint has successfully been deployed, you can authorize
some users to access it. Additionally, if it is ready you can publish your analysis to the neurocaas website, and have it accessible by default to interested users. 
Contact your neurocaas admin at neurocaas@gmail.com for instructions on how to proceed from here.
