Developing On the Command Line (Recommended) 
============================================

The recommended method of developing a blueprint is now through the neurocaas-contrib CLI (here). However, 
we include legacy documentation for developing using the IPython Console (next section).

Starting a development session
------------------------------

Every time you want to start a remote development session, you should run the following command: 

.. code-block:: 

   neurocaas-contrib remote start-session

This lets the CLI tool know that you would like to start working on a blueprint remotely, and initializes the relevant parameters.    

Note- this is a change as of 8/19/21. If your neurocaas-contrib version was built from source before this, you should update it. The `start-session` command deprecates `develop-remote`. 


Launching a machine 
-------------------

Once you have started a development session, you can request a remote machine. 
The first time that you request a remote machine, you will probably waht to call it as follows: 

.. code-block::

   neurocaas-contrib remote launch-devinstance  --timeout 60 --volumesize <size GB> --amiid <ami-id>

This command will launch a remote instance of the type specified in your blueprint's parameter, :code:`Lambda.LambdaConfig.INSTANCE\_TYPE`.    
Furthermore, it will be kept on for :code:`--timeout` minutes (default 60), be equipped with a storage volume of size :code:`--volumesize` gigabytes, and 
start with a virtual machine of type :code:`--amiid`, where the ID is specified by AWS AMI IDs. If you do not specify an id, it will be read in from the blueprint's :code:`Lambda.LambdaConfig.AMI` parameter.  

To be concrete, AMI IDs are formatted as (“ami-xxxxxxxx”)
(you can find many on the AWS marketplace). If you do not have a
particular AMI id in mind, you can also pass one of the following
special codes as an argument:

-   “ubuntu18”: ubuntu version 18, x86.

-   “ubuntu16”: ubuntu version 16 x86.

-   “dlami18”: AWS conda deep learning ami
    `details here <https://aws.amazon.com/blogs/machine-learning/new-aws-deep-learning-amis-for-machine-learning-practitioners/>`_,
    with pre-installed deep learning libraries on ubuntu 18, x86.

-   “dlami16”: like dlami18, but on ubuntu16, x86.

These latter two AMIs are pre-configured with CUDA drivers, which can 
save lots of time for GPU based analyses. 
NOTE: These codes have been tested with a variety of x86 (intel based)
instances (m5 series, m5a series, p2 and p3 series). If you plan to use
non-x86 based instances, (such as the ARM based a1 series) please look
up the AMI id for the relevant OS distribution, and pass this id as an
argument. 

Calling this method will initialize an instance for you, and
then provide you with the ip address of that initialized instance. You
can then ssh into the instance with the key that you retrieved when
initializing NeuroCAAS, like so:

.. code-block:: 

    ssh -i /path/to/your/local/sshkey ubuntu@{ip address}

Please note that if you use a custom ami, you may be prompted to log in
as root, or ec2-user instead of ubuntu.

If you ever restart the instance, or forget, you can get the ip address of a running instance by calling:

.. code-block:: 

   neurocaas-contrib remote get-ip

Note that if you restart your development instance, the requested timeout will be reset (default is 1 hour again).
If you ever need to check how much time you have left, you can call: 

.. code-block:: 

   neurocaas-contrib remote get-timeout

To extend the lifetime of your instance, you can also call 
   
.. code-block:: 

   neurocaas-contrib remote extend-timeout -m <minutes>

To extend the lifetime of your instance. Note that each developer does have a budget of instance lifetime, up to the NeuroCAAS Account's discretion.   

Developing a machine image into an immutable analysis environment
-----------------------------------------------------------------

After connecting to your remote instance via ssh, you can download your
code repositories and dependencies to it, and test basic functionality.
You should also install the CLI tool on the remote instance as well. 
If you remember the Quickstart example, our goal here is to develop any source code 
into that example. 

Main script
~~~~~~~~~~~

All NeuroCAAS analyses should be triggered by running a central bash script called :code:`run\_main_cli.sh` (it can be found in the top level directory of :code:`neurocaas-contrib`).

This script ensures that all jobs run on NeuroCAAS are managed and logged correctly. 
This script takes 5 arguments, as follows:   

.. code-block::

  `% bash run_main_cli.sh $bucketname $path_to_input $path_to_result_dir $path_to_config_file $path_to_analysis_script`

The first four parameters refer to locations in Amazon S3 where the inputs and results of this analysis will be stored. 
These parameters correspond to the directory structure given in the "End Goals" section as follows: 

- :code:`$bucketname: {analysis\_name}`
- :code:`$path\_to\_input`: {group\_name}/inputs/name\_of\_dataset`
- :code:`$path\_to\_result\_dir`: results/job\_{timestamp}`
- :code:`$path\_to\_config\_file`: {group\_name}/configs/name\_of\_config\_file`

These will be automatically filled in by NeuroCAAS when users request jobs, 
but can be manually filled in for certain test cases. For more info see the section, "Testing a machine image."

The fifth parameter, :code:`$path\_to\_analysis\_script`, is a analysis-specific bash script, that will be run inside the :code:`run\_main.sh` script. It will call all of the analysis source code
, transfer data in to the instance, etc. This will be the subject of the next subsection, Analysis script. 

If we look at the contents of :code:`run\_main\_cli.sh`, they are as follows: 

.. code-block:: bash

    #!/bin/bash

    source "/home/ubuntu/.dlamirc"
    export PATH="/home/ubuntu/anaconda3/bin:$PATH"
    source activate neurocaas

    neurocaas-contrib workflow initialize-job -p /home/ubuntu/contribdata

    neurocaas-contrib workflow register-dataset -b "$1" -k "$2"
    neurocaas-contrib workflow register-config -b "$1" -k "$4"
    neurocaas-contrib workflow register-resultpath -b "$1" -k "$3"

    neurocaas-contrib workflow log-command -b "$1" -c "$5" -r "$3"

    neurocaas-contrib workflow cleanup

These are basically the same commands that you ran manually in the Quickstart example- in this case we are just running those same steps, based off of automatically given parameters. 

This script-in-a-script organization ensures two things:

- Reliability of logging. Logging progress mid-analysis can be a delicate process, and standardizing it 
in a single main script helps to ensure that developers will not have to worry about this step.

- Correct error handling. In the event that analysis scripting runs into an error, we want to be able to detect and catch these errors. We can do so much more easily if all relevant code is executed in a separate script, ensuring that the relevant steps necessary to report the error to the user, and run appropriate cleanup on the instance are carried out.

 

See the CLI --help command for in depth info on each of these CLI commands, or the API docs `here <https://neurocaas-contrib.readthedocs.io/en/latest/>`_

Analysis script
~~~~~~~~~~~~~~~

TL;DR from the previous section: 
- We will assume the analysis script takes no parameters. The main script above registers the dataset, configuration file, and result location that we should interact with, and we can use the cli to interact with registered files and paths as follows: 

- Getting Files:   
  - In an analysis script, users can retrieve files from a registered remote location by calling the following commands: 
    - :code:`neurocaas-contrib workflow get-data` to retrieve registered data. 
    - :code:`neurocaas-contrib workflow get-config` to retrieve registered configuration files. 
  - By passing the :code:`-f` flag, you can force redownload files that already exist. 
  - By passing the :code:`-o` flag, you can force download to a specific directory.  
- Uploading Files:
  - In an analysis script, users can push files to a registered remote location by calling the following commands: 
    - :code:`neurocaas-contrib workflow put-result -r <path>`
    - The parameter :code:`-r` specifies the local file that you want to upload to the registered remote location.   
- Listing File Paths:       
  - Once you have gotten files from a remote location, you need to know where they are. Get the name/path to registered files and directories as follows: 
    - :code:`neurocaas-contrib workflow get-datapath` retrieves the path to downloaded data. 
    - :code:`neurocaas-contrib workflow get-configpath` retrieves the path to downloaded config files. 
    - :code:`neurocaas-contrib workflow get-dataname` retrieves the basename of downloaded data. 
    - :code:`neurocaas-contrib workflow get-configname` retrieves the basename to downloaded config files. 
  - You might also want the path of the remote location to which you are writing results:  
    - :code:`neurocaas-contrib workflow get-resultpath` retrieves this remote path, so you can write other items to it. 
- Utilities:       
  - There are several tasks you might run into during scripting that can be a real pain: unzipping files, reading fields from yaml configuration files, etc. We include some utilities to help with these tasks: 
    - :code:`neurocaas-contrib scripting parse-zip -z <pathtozip>` unzips a zipped directory, assuming there is just a single top level directory within. It will also return the name of that top level directory.  
    - :code:`neurocaas-contrib scripting read-yaml -p <pathtoyaml> -f <field> -d <default>` retrieves the contents of a yaml file, at a specified field. If not found it will return a developer-specified default value.  


There are more features that you can dig into to parse multiple input files, or multiple result files. 
See the CLI --help command for in depth info on each of these CLI commands, or the API docs `here <https://neurocaas-contrib.readthedocs.io/en/latest/>`_
 
As a worked example, we can look at the processing script for the analysis DeepGraphPose. This analysis uses all of the commands above, and conditionally performs training or prediction based on the value of a configuration file parameter: 

.. code-block:: bash 
   
    #!/bin/bash
    set -e
    userhome="/home/ubuntu"
    datastore="deepgraphpose/data"
    outstore="ncapdata/localout"

    echo "----DOWNLOADING DATA----"
    source activate dgp
    neurocaas-contrib workflow get-data -f -o $userhome/$datastore/
    neurocaas-contrib workflow get-config -f -o $userhome/$datastore/

    datapath=$(neurocaas-contrib workflow get-datapath)
    configpath=$(neurocaas-contrib workflow get-configpath)
    taskname=$(neurocaas-contrib scripting parse-zip -z "$datapath")
    echo "----DATA DOWNLOADED: $datapath. PARSING PARAMETERS.----"

    mode=$(neurocaas-contrib scripting read-yaml -p $configpath -f mode -d predict)
    debug=$(neurocaas-contrib scripting read-yaml -p $configpath -f testing -d False)

    echo "----RUNNING ANALYSIS IN MODE: $mode----"
    cd "$userhome/deepgraphpose"

    if [ $mode == "train" ]
    then
        if [ $debug == "True" ]
        then
            echo "----STARTING TRAINING; SETTING UP DEBUG NETWORK----"
            python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
        elif [ $debug == "False" ]
        then
            echo "----STARTING TRAINING; SETTING UP NETWORK----"
            python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
        else
            echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."
            exit
        fi
        echo "----PREPARING RESULTS----"
        zip -r "/home/ubuntu/results_$taskname.zip" "$userhome/$datastore/$taskname/"
    elif [ $mode == "predict" ]
    then
        if [ $debug == "True" ]
        then
            echo "----STARTING PREDICTION; SETTING UP DEBUG NETWORK----"
            python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/" --test
        elif [ $debug == "False" ]
        then
            echo "----STARTING PREDICTION; SETTING UP NETWORK ----"
            python "demo/predict_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
        else
            echo "Debug setting $debug not recognized. Valid options are "True" or "False". Exiting."
            exit
        fi
        echo "----PREPARING RESULTS----"
        zip -r "/home/ubuntu/results_$taskname.zip" "$userhome/$datastore/$taskname/videos_pred/"
    else
        echo "Mode setting $mode not recognized. Valid options are "predict" or "train". Exiting."
    fi

    echo "----UPLOADING RESULTS----"
    neurocaas-contrib workflow put-result -r "/home/ubuntu/results_$taskname.zip"



Saving your machine image
-------------------------

After you have written a script and tested it locally (as in the Quickstart example), you should save
your progress in a machine image. Even if you are not confident that your image is ready, saving a machine image will freeze the state of the file system 
and installed software, so that a new hardware instance can start from that state upon launch, allowing you to develop 
the contents incrementally. We will cover the process of testing instances more rigorously in a later section.   
In order to save your machine image, return to a terminal window in your local machine and run the following:  

.. code-block:: bash

   neurocaas-contrib remote create-devami -n "<name>"

where the name is an identifier you will provide to your newly created
image. 

Then, you can update your blueprint with this new image by running:

.. code-block:: bash

   neurocaas-contrib remote update-blueprint -m "<message>"

This command automatically updates the blueprint of your analysis with the new AMI you have created, 
and creates a pair of git commits saving the state of your repo before and after this update. 
The message command, if provided, will be a message associated
with this pair of git commits for readability.

Cleaning up
-----------

To clean up after finishing a session, you can delete your instance and reset your cli state by running: 

.. code-block:: bash

   neurocaas-contrib remote end-session 

Note- this is a change as of 8/19/21. If your neurocaas-contrib version was built from source before this, you should update it. 

Alternatively, after you have saved your machine image and updated your blueprint, you
can terminate it by running:

.. code-block:: bash

   neurocaas-contrib remote terminate-devinstance

If you have not created an image before doing so, you will be prompted
for confirmation. If you would like to step away from developing for a
while, you can run:

.. code-block:: bash

   neurocaas-contrib remote stop-devinstance

And conversely,

.. code-block:: bash

   neurocaas-contrib remote start-devinstance

You can also use this command to start instances that have exceeded the provided timeout and been stopped externally
.    
Note that stopped instances will be deleted after two weeks of idleness.    
Furthermore, you can only launch one instance at a time. 

Deploying your blueprint and Testing 
------------------------------------

Once you have a working image, it is useful to deploy it as a NeuroCAAS
analysis to perform further testing using the access configuration a
user would have (see “Testing a machine image”).
Deployment is managed centrally by the NeuroCAAS Team. 
Once you are ready to deploy your blueprint, and see how your analysis performs, 
push your blueprint to an active pull request in the NeuroCAAS repo, or create a new one and notify your NeuroCAAS admin. 
A NeuroCAAS admin will then review your blueprint and associated code changes, and deploy it so that you can monitor the results. 

Testing a machine image
~~~~~~~~~~~~~~~~~~~~~~~

IMPORTANT NOTE: this step can only be done AFTER initially deploying a
blueprint (Step 6). Our Python development API has the capacity to
*mock* the job managers that parse user input. In order to test your
machine image including the inputs and outputs that a user would see,
follow these steps: 

1. Upload data and configuration files to the deployed s3 bucket, just as a user would.

The easiest way to do this is to use the AWS CLI that you already have installed as part of your setup. In particular, the following commands are useful: 

- :code:`aws s3 ls s3://{bucket}/{path}`. This command will list the contents of a certain bucket under a specific paths prefix.   
- :code:`aws s3 ls {local/file/path} s3://{bucket}/{path}/{filename}`. This command will upload a local file to the given s3 location.   
- :code:`aws s3 ls s3://{bucket}/{path}/{filename} {local/file/path}`. This command will download a file from the given s3 location to your local computer.   

See `this page <https://docs.aws.amazon.com/cli/latest/reference/s3/>`_ for more detailed info on interacting with AWS S3. 

For your analyses, the parameter :code:`{bucket}` corresponds to the :code:`PipelineName` you passed in the blueprint. If you list the contents of your bucket, you will see the group name that you passed to your blueprint under :code:`AffiliateName`, and the following directory organization: 

.. code-block::

    s3://{analysis_name}   ## This is the name of the S3 bucket
    |- {group_name}        ## Each NeuroCAAS user is a member of a group (i.e. lab, research group, etc.)
       |- configs
       |- inputs
       |- submissions
       |- results

You should upload all configuration files to the :code:`configs` directory, and all data to the :code:`inputs` directory.        

2. Write a submit.json file, like below:

.. code-block:: json


    {
        "dataname":"{group_name}/inputs/data.zip",
        "configname":"{group_name}/configs/config.json",
        "timestamp": "debugging_identifier"
    }

Where the dataname and configname values point to the data that you
upload to an S3 bucket, and {group\_name} corresponds to the group name 
depicted in the user-side data organization diagram. If you followed 
the instructions regarding blueprint configuration, this will most likely 
be "debuggers".

Then, run

.. code-block:: bash

   neurocaas-contrib remote submit-job -s <submitpath>

Where submitpath is the path to the submit file you wrote. This will
trigger processing in your development instance as a background process
(you can observe it with top). If you don't remove the instance shutdown 
command when you are running this test, your instance will stop after the processing finishes. You can monitor the
status and output of this job as it proceeds locally from python with:

.. code-block:: bash

   neurocaas-contrib remote job-status 

.. code-block:: bash

   neurocaas-contrib remote job-output 

The results themselves will be returned to AWS
S3 upon job completion.


Adding users
~~~~~~~~~~~~

Once your blueprint has successfully been deployed, you can authorize
some users to access it. Additionally, if it is ready you can publish your analysis to the neurocaas website, and have it accessible by default to interested users. 
This process is managed through pull requests as well. Let your NeuroCAAS admin know that you are ready to add users in a pull request thread, and they will authorize you for further steps. 
