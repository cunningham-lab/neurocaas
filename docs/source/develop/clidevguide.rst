Developing On the Command Line (Recommended) 
============================================

The recommended method of developing a blueprint is now through the neurocaas-contrib CLI (here). However, 
we include legacy documentation for developing using the IPython Console (next section).

.. note::
   As of July 2023, we have updated the neurocaas contrib interface to no longer require "sessions" from developers.  
   If you would like to continue developing with "sessions", you can check out the `sessions` branch of `neurocaas-contrib`.

Working with remote machines
----------------------------

Most of the work that you do to get an analysis on NeuroCAAS will happen on a remote machine. 
You can either request a new remote machine from NeuroCAAS, or "assign" a pre-existing one.  
The first time that you request a remote machine, you will probably call it as follows: 

.. code-block::

   neurocaas-contrib remote launch-devinstance --name <instance name> --description <description> --timeout 60 --volumesize <size GB> --amiid <ami-id>

This command will launch a remote instance of the type specified in your blueprint's parameter, :code:`Lambda.LambdaConfig.INSTANCE_TYPE`.    
We encourage you to provide a name and description for this instance, to make it easier to identify later on. 
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

.. note:: 
    If you choose to start with the Deep Learning AMIs, you do not need to do any configuration to start using GPUs (installing nvidia toolkits, etc.). If you run the command :code:`watch nvidia-smi`, you should be able to see GPUs available for use, and you can check on their usage throughout processing.  
    If you require a specific CUDA version, please follow these instructions to detect and change the active CUDA version `here <https://docs.aws.amazon.com/dlami/latest/devguide/tutorial-base.html>`_. CUDA versions are pre-installed, and this process should take only a few minutes.  

.. warning::
    These codes have been tested with a variety of x86 (intel based)
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

Alternatively, if you have an AWS instance already that you would like to work with, you can run the command 

.. code-block::
   
   neurocaas-contrib remote assign-instance -i <instance-id> -n <name> -d <description>

Here, the instance-id identifies the AWS instance you would like to work with, while name and description are once again identifies that will make your
instance easier to work with. All of the commands above can be used on an instance that has been assigned to the CLI, instead of created from it.    

Working with multiple instances/analyses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Although the NeuroCAAS CLI only allows you to interact with one development instance at a time, 
there can be several different instances associated with the CLI, which you can switch between. 
This can be helpful (for example) if you want to develop new features on one instance,
and testing them on another.
 
For each of your analyses, you can have up to 4 instances associated with the CLI at a given time.  
At any time you can run the command: 

.. code-block:: 

   neurocaas-contrib remote list-instances 

to see the list of instances that are currently available for a given analysis. 

.. image:: ../images/list_instances.png
   :width: 600

You will see an asterisk next to the currently selected instance. You can select a different 
instance from this list at any time with the command 

.. code-block::
   
   neurocaas-contrib remote select-instance -n <instance name>/-i <instance id>

Where you can provide either the name or ID of the instance when selecting it. 

We track development instances separately for each NeuroCAAS analysis you work with. 


Developing a machine image into an immutable analysis environment
-----------------------------------------------------------------

After connecting to your remote instance via ssh, you can download your
code repositories and dependencies to it, and test basic functionality.
You should also install the CLI tool on the remote instance as well. 
If you remember the Quickstart example, our goal here is to develop any source code 
into that kind of example, where all functionality is handled from a call to a single workflow script. 

.. note:: 
   Although our platform largely hosts analysis code written in python, we are not tied to a particular programming language, and you are free to run programs written in the language of your choice, as long as it can be incorporated into a bash script call. One important qualification is the use of licensed languages, like MATLAB. For Matlab, we recommend the following workflow: 

   1. Use the [MATLAB Compiler](https://www.mathworks.com/help/compiler/getting-started-with-matlab-compiler.html) to compile your code into a program that can be run from your command line. You should run the MATLAB compiler from a Linux Operating System so that compiled code will run on our pre-configured IAE templates. 
   2. Install the compiled code onto the IAE, and proceed as described below.       
   
   Feel free to contact a NeuroCAAS Admin for more help with specific instances of this workflow. 

In what follows we will first cover the structure of inputs to IAEs, followed by the recommended structure of processing scripts.


Input: Data and Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All NeuroCAAS analyses take as input a single data file, and a single configuration file. The data file can be in any format (numpy array, hdf5 file, tiff image stack, zip archive, etc.), but it must be a single file. If you have additional data files that are important for analysis, the recommended workflow is to indicate them as additional parameters in your configuration file.  

The configuration file is a :code:`.yaml` (or optionally :code:`.json`) file. We prefer :code:`.yaml` because it allows developers to easily write comments around their parameters, which is easier for users to understand. For python analyses, YAML files can be parsed like dictionaries- we provide command line tools to parse YAML files through the :code:`neurocaas-contrib` cli as well. 

One important point is that all NeuroCAAS config files take two general purpose NeuroCAAS parameters:    
    - __duration__: This parameter specifies the **maximum** expected duration for a given NeuroCAAS job, in minutes. **Once this duration is reached, the job can be stopped at any time**. If not given, this duration is set at 60 minutes for all analyses- you may want to set a much higher default value depending on your analysis. At the same time, note that this parameter allows us to predict and monitor costs, and users will not be able to run jobs whose expected costs exceed their budgets, so don't set it to something ludicrously large.  
    - __dataset_size__: This parameter specifies storage space in GB that you would like to add to your immutable analysis environment. This is most important if you are running very large datasets.  

In your config file, these parameters might look like this:     

.. code-block:: yaml

    # Analysis Parameters:
    # ++++++++++++++++++++
    ## a boolean parameter
    parameter_1: True 
    ## a list parameter
    parameter_list: [1,2,3,4]
    ## a float parameter
    float_parameter: 0.5
    ## a path parameter: points to another resource the user has access to 
    additional_data: /path/to/file/in/s3.data


    # NeuroCAAS Parameters:
    # ++++++++++++++++++++

    # DURATION: You can specify the duration parameter if you know how long the job will last to trigger a NeuroCAAS Save job.
    # This will cost around half of a standard job, and the instance will terminate once the given time limit is reached, whether or not analysis is complete.
    # Units: Minutes
    # Type: INTEGER.
    __duration__: 200

    # DATASET SIZE: You can specify the dataset_size parameter if your dataset is large, and you know you will need extra storage space in the immutable analysis environment.
    # This space will be added onto the existing size of the instance.
    # Units: GB
    # Type: INTEGER
    __dataset_size__: 300



Main script
~~~~~~~~~~~

All NeuroCAAS analyses should be triggered by running a central bash script called :code:`run_main_cli.sh` (it can be found in the top level directory of :code:`neurocaas-contrib`).

This script ensures that all jobs run on NeuroCAAS are managed and logged correctly. 
This script takes 5 arguments, as follows:   

.. code-block::

  `% bash run_main_cli.sh $bucketname $path_to_input $path_to_result_dir $path_to_config_file $path_to_analysis_script`

The first four parameters refer to locations in Amazon S3 where the inputs and results of this analysis will be stored. 
These parameters correspond to the directory structure given in the "End Goals" section as follows: 

- :code:`$bucketname: {analysis_name}`
- :code:`$path_to_input`: {group_name}/inputs/name_of_dataset`
- :code:`$path_to_result_dir`: results/job_{timestamp}`
- :code:`$path_to_config_file`: {group_name}/configs/name_of_config_file`

These will be automatically filled in by NeuroCAAS when users request jobs, 
but can be manually filled in for certain test cases. For more info see the sections "Testing your script (locally)" and "Testing a machine image".

The fifth parameter, :code:`$path_to_analysis_script`, is a analysis-specific bash script, that will be run inside the :code:`run_main.sh` script. It will call all of the analysis source code,
transfer data in to the instance, and perform all of the functions we think of as analysis workflow.
This script is analogous to the script :code:`run_pca.sh` in the Quickstart example. 
Importantly, we assume that there will be a single analysis script that will be shared by all users of an analysis. 

If we look at the contents of :code:`run_main_cli.sh`, they are as follows: 

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

If we substitute in :code:`run_pca.sh` for all instances of :code:`$5`, these are basically the same commands that you ran manually in the Quickstart example. In this case we are just running those same steps, based off of parameters that are specified by the user requesting the analysis. 

This script-in-a-script organization ensures two things:

- Reliability of logging. Logging progress mid-analysis can be a delicate process, and standardizing it 
in a single main script helps to ensure that developers will not have to worry about this step.

- Correct error handling. In the event that analysis scripting runs into an error, we want to be able to detect and catch these errors. We can do so much more easily if all relevant code is executed in a separate script, ensuring that the relevant steps necessary to report the error to the user, and run appropriate cleanup on the instance are carried out.

See the CLI --help command for in depth info on each of these CLI commands, or the API docs `here <https://neurocaas-contrib.readthedocs.io/en/latest/>`_

.. note:: 
    Before we move on, let's discuss how the main script interacts with the analysis blueprint. This is one of the more complex parts of NeuroCAAS's function, which is worth discussing in detail. 
   
    Let's assume that we are developing the PCA based analysis from the Quickstart example into a full NeuroCAAS blueprint. We already have an analysis specific bash script, located at :code:`./run_pca.sh`. In this case, we should format the main script as follows:
   
    :code:`% bash run_main_cli.sh $bucketname $path_to_input $path_to_result_dir $path_to_config_file ./run_pca.sh`
   
    The remaining variables in this command specify where to pull input data and configuration parameters from, and where to deposit the results. Therefore, they must be specified each time an analysis is called.   

    The blueprint for this hypothetical analysis would have a COMMAND field as follows:

    :code:`ls; cd /home/ubuntu; neurocaas_contrib/run_main_cli.sh \"{}\" \"{}\" \"{}\" \"{}\" \"./run_pca.sh\"; . neurocaas_contrib/ncap_utils/workflow.sh; cleanup`.
   
    Beyond navigating to the correct directory (:code:`ls; cd /home/ubuntu`) and shutting down the instance (:code:`./ neurocaas_contrib/ncap_utils/workflow.sh; cleanup`), the COMMAND field is nearly identical to the bash command specified above. The brackets given are filled in by the job manager with the appropriate information before being run.   

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
See the CLI --help command for in depth info on each of these CLI commands, or the API docs `here <https://neurocaas-contrib.readthedocs.io/en/latest/>`_.
 
As a general guideline for writing analysis scripts, you can treat immutable analysis environments like a persistent server when installing your analysis software- the state of your file system will be preserved when you save your IAE. A good rule of thumb is as follows: Imagine you log in to a remote server, install your code, and then log out and back in again. What steps would you have to take to make your analysis run? A typical (python) example might include:   
   
1. Activating a conda virtual environment
2. Navigating to the directory where your scripts are stored      
3. Locating your data and configuration files, and passing them to your analysis script      
4. Locating analysis results, and passing them back to the user.       

We have introduced tools to make scripting many of these steps easier, as documented above. 


.. note::

    Please consider the follow best practice guidelines to maximize the benefits of NeuroCAAS for your analysis. These criteria will be evaluated when your stack is reviewed by NeuroCAAS admins: 

    1. Secrets: Don't hardcode private secrets into the immutable analysis environment. AWS credentials will automatically be passed to the instance when you log in, so you will not have to configure it as you did your local machine. Although users won't be able to interactively access the IAE, removing private secrets can also make your analysis more portable and usable in non-NeuroCAAS settings should you wish to do so in the future.    
    2. Updating your codebase: Avoid steps that could mutate the state of your IAE within your workflow script (e.g. git pulling from your repository to get the latest version). Although convenient, this step can interfere with the reproducibility that NeuroCAAS provides. The recommended workflow is to update your IAE through pull requests when you want to update your analysis itself, ensuring that changes to expected behavior are documented. In the future we plan to create workflows through Github to automate this process.       
    3. Randomization: If your analysis relies upon randomized computations (random initial state, sampling), whenever possible we recommend including random seeds as a configuration parameter. This step can extend the reproducibility benefits provided by NeuroCAAS.   
    4. Logs: Be as clear as possible about reporting compute back to the user. If you follow the steps outlined here, all outputs printed to stdout and stderr by your workflow script will be reported back to the user (including outputs from child processes of the script, like calls to python scripts). See the :code:`Analysis script` section below for an example. Configuration files will also be returned to the user by default.    
    5. Input parsing: A useful feature for IAE based analyses is the ability to parse inputs at the beginning of analyses to ensure that they are formatted as expected- in fact, in the absence of common infrastructure issues this is the most common issue on NeuroCAAS. Including input parsing can save compute time and provide clearer error messages to users. Input parsing can be implemented in several ways: 1) As the first step of your Analysis script. This option is most appropriate if input parsing requires the compute resources provided by your blueprint, but it means that analyses will have to be started before users are informed of a potential formatting error. 2) As an independent script distributed to users. When you make your analysis available on NeuroCAAS, you can provide additional resources for users, including scripts that they can run themselves. 3) As a customized job manager. When analysis jobs are first requested, we can program custom behavior from the NeuroCAAS job manager. See the section :code:`Customizing the job manager` later in this section for details.  
           
If you have questions about these criteria and their implementation for your particular use case, please pose a question via an issue or pull request on our Github repo.     


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

Finally, update the permissions on your analysis script to ensure they can be run by NeuroCAAS automatically:     

.. code-block::

   % chmod 777 /path/to/analysis/script

Testing your script (locally)
-----------------------------

At this point, it's a good idea to run a few more tests to ensure that your script is behaving as intended. A nice feature of the analysis script is that it is input independent- it looks at the dataset, configuration file, and result paths that you've registered, and doesn't care if they are in an S3 bucket or local. Therefore, you can run the following commmands on the compute instance to test your analysis script with data that exists on that instance:   

.. code-block::

    % neurocaas-contrib workflow initialize-job -p "/some/local/path" 

    % neurocaas-contrib workflow register-dataset -l "/path/to/your/local/data"
    % neurocaas-contrib workflow register-config -l "/path/to/your/local/config"
    % neurocaas-contrib workflow register-resultpath -l "/path/to/your/results/folder" 

    % neurocaas-contrib workflow log-command-local -c "bash $path/to/your/analysis_script" 

Running these commands from the command line is exactly analogous to what the main script does when triggered remotely. The only difference is that what happens here is totally local: these commands will register certain files within your compute instances as the dataset and configuration file to use for testing, instead of files in an S3 bucket. Results will be written to a local folder, instead of S3 as well. Finally, it will run any command, and write the output to the console in the same fashion that a user would see them. 

If your analysis results look good, we can check one final thing. When run remotely, NeuroCAAS runs analyses as a separate user, :code:`ssm_user`, instead of :code:`ubuntu`, or :code:`ec2-user`, as you normally use. This is normally not an issue, but we can mimic the performance of :code:`ssm_user` by running the following commands: 

.. code-block::

   % sudo -i 
   % cd /home/{your original username}
   % source activate {your environment name}
   % neurocaas-contrib workflow log-command-local -c "bash $path/to/your/analysis_script"

We are re-running the final command above, but now as a different user. If you find that this causes issues, we will deal with this in the blueprint, in the section :code:`Deploying your blueprint and Testing` below. 
   
Saving your progress 
--------------------

After you have written a script and tested it locally (as in the Quickstart example), you should save
your progress in a machine image. Even if you are not confident that your image is ready, saving a machine image will freeze the state of the file system 
and installed software, so that a new hardware instance can start from that state upon launch, allowing you to develop 
the contents incrementally. We will cover the process of testing instances more rigorously in a later section.   
In order to save your machine image, return to a terminal window in your local machine and run the following:  

.. code-block:: bash

   neurocaas-contrib remote create-devami -n "<name>"

where the name is an identifier you will provide to your newly created
image. 

Additionally, if you have newly created/renamed your analysis script, make sure to update the :code:`COMMAND` field of your blueprint appropriately. 

Then, you can update your blueprint with this new image by running:

.. code-block:: bash

   neurocaas-contrib remote update-blueprint -m "<message>"

This command automatically updates the blueprint of your analysis with the new AMI you have created, 
and creates a pair of git commits saving the state of your repo before and after this update. 
The message command, if provided, will be a message associated
with this pair of git commits for readability.

Cleaning up
-----------

After you have saved your machine image and updated your blueprint, you
can terminate it by running:

.. code-block:: bash

   neurocaas-contrib remote terminate-devinstance

If you have not created an image before doing so, you will be prompted
for confirmation. If you would like to step away from developing for a
while, you can run:

.. code-block:: bash

   neurocaas-contrib remote stop-devinstance

And conversely, to start again,

.. code-block:: bash

   neurocaas-contrib remote start-devinstance

You can also use this command to start instances that have exceeded the provided timeout and been stopped externally
.    
Note that stopped instances will be deleted after two weeks of idleness.    

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

We can now run tests that interact with your analysis exactly as a user would. 

.. note::
    This step can only be done AFTER initially deploying a
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
upload to an S3 bucket, and {group_name} corresponds to the group name 
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

.. note:: 

   You may run into permissions related issues at this stage- if certain software was installed with permissions that only allows it to be run by a specific user, automatically running your IAE may fail. A common example of this is in activating conda environments. To resolve these issues, we can amend the blueprint as follows. For the field :code:`Lambda.LambdaConfig.COMMAND`, please prepend `sudo -u {your username}` to your call to :code:`run_main.sh`. For example, if the current value is :code:`neurocaas_contrib/run_main.sh`, and you log in to your compute instance as :code:`ubuntu`, the command should become :code:`sudo -u ubuntu neurocaas_contrib/run_main.sh`. This will ensure behavior that is identical to running your main script from inside the instance. 

Adding users and managing access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once your blueprint has successfully been deployed, you can authorize
some users to access it. Additionally, if it is ready you can publish your analysis to the neurocaas website, and have it accessible by default to interested users. 

As a developer, you can manage access to your analysis through the :code:`STAGE` parameter of your blueprint. Access works as follows: 

- If :code:`STAGE=webdev`, you authorize users to access your analysis on a case-by-case basis through blueprint updates. Nobody who you do not explicitly name in your blueprint can run analysis jobs. 
- If :code:`STAGE=websubstack`, you are opening your analysis for general use. Anyone with a NeuroCAAS account can opt in to use your analysis. 

Generally, we recommend you keep analyses in the :code:`webdev` mode until you have run a few end-to-end tests yourself (i.e. uploading data to an S3 bucket, and ensuring that results are written back to the bucket), and upgrade to :code:`websubstack` once you would like to recruit test users. In order to add users to your analysis, ask them for their AWS username, and contact NeuroCAAS admins for their group name (we're working on making this easier.) 

With this information, add the following bracketed block to the "Affiliates" section of your blueprint: 

.. code-block:: json 

   "UXData": {
    "Affiliates": [
        ...
        {
            "AffiliateName": {name of group},
            "UserNames": [
               {AWS username WITHOUT REGION} 
            ],
            "UserInput": true,
            "ContactEmail": "NOTE: KEEP THIS AFFILIATE TO ENABLE EASY TESTING"
        }
        ... 
    ]

Importantly, you should add the AWS username without the region suffix (e.g. "us-east-1"). 


This process is managed through pull requests as well. Let your NeuroCAAS admin know that you are ready to add users in a pull request thread, and they will authorize you for further steps. 

Customizing Job Managers
------------------------

For most analyses, it is sufficient to develop your analysis entirely within a single IAE as described above.This is the case for all computing steps that can be done assuming that your dataset and configuration files already exist in some file system. If this is the case for you, you can ignore this section.  
However, some parts of analysis may be useful to implement as soon as NeuroCAAS jobs are triggered- i.e. before transferring data and configuration files into an IAE. Examples of such steps include parsing inputs, coordination of multiple IAEs on multiple hardware instances, or multi-step analyses that work across different IAEs sequentially. Examples of these latter two workflows are presented in the NeuroCAAS paper. This level of customization can be implemented on an analysis-by-analysis basis by customizing NeuroCAAS job manager behavior through protocols.

Default Protocol 
~~~~~~~~~~~~~~~~
Note the following fields of the blueprints: :code:`Lambda.CodeUri` and :code:`Lambda.Handler`. By default, you should expect to see the following fields and values in the blueprint:

.. code-block::
    "Lambda": {
        "CodeUri": "../../protocols",
        "Handler": "submit_start.handler_develop",

These fields point to code located in the directory :code:`ncap_iac/protocols`.
In particular, the module :code:`submit_start.py` contains a function :code:`handler_develop` that is triggered every time a NeuroCAAS submission file is uploaded. This code is run in a *serverless* environment using AWS Lambda.  

Building Custom Protocols
~~~~~~~~~~~~~~~~~~~~~~~~~

The logic for parsing submissions is contained in the class :code:`Submission_dev`, contained in the same file. The recommended workflow for customizing job managers is to *inherit* from :code:`Submission_dev`, as is done in :code:`Submission_ensemble`, and overwrite or extend existing methods. For example, one could implement input parsing by extending the method :code:`check_existence`, which performs a basic check to ensure that the data and configuration file referenced in job submission really exists. 

Some notes regarding customizing job managers: 

- Customizing job managers is more advanced than the standard NeuroCAAS workflow, as it requires developers to be more aware of the way in which user input triggers computation on the cloud. We therefore recommend that first time developers leave Job Managers in their default configuration if possible, and that they consult with NeuroCAAS admins before making changes if required.  
- It is critical to correctly handle errors and exceptions in the Job Manager- because Job Managers have the important role of determining when to start and stop compute instances, mismanagement can have implications on the cost of your analysis. These features will be tested extensively by NeuroCAAS admins if you choose to customize your Job Manager.   

