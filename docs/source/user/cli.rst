Using NeuroCAAS from the Command Line
=====================================

The simplest way to use NeuroCAAS is through the website interface, located `here <www.neurocaas.org>`_. However, this is not the only way to use NeuroCAAS. In particular, NeuroCAAS also supports a *command line interface* (CLI), which lets you upload data, submit jobs, and retrieve results from the platform directly from your computer's terminal window, as opposed to a web browser. In this document, we'll discuss the pros and cons of this method, how it interfaces with other ways of using NeuroCAAS, and the steps you'll need to follow.   

Pros and Cons
-------------
The biggest pros of using a CLI interface to interact with NeuroCAAS is efficiency and scale. You can easily upload large datasets to NeuroCAAS (~100s of GB), which can be quite inconvenient using the web browser, and you can easily submit multiple jobs in parallel, or build software around calls to NeuroCAAS (although this may be easier with the SDK for your programming language-- although NeuroCAAS also supports this use case, we do not cover it in detail here). It can also be useful to download data to a machine where you do not have access to a web browser.  

The downsides of using a CLI interface is that it can be less user friendly- in particular, monitoring jobs can be more difficult: the website interface lets you monitor logs for jobs in real time, but you will have to download and inspect them using the CLI. If you are getting started, we recommend that you work with the web interface first, in order to get familiar with how NeuroCAAS works. 

Interoperability
----------------

The website interface to NeuroCAAS and the CLI (as well as any other cloud storage browser) are interoperable- you can start a job with the web inteface, and download result via the CLI, or upload data via the CLI and run jobs with the browser. 

Installation
------------

We use the `AWS CLI <https://aws.amazon.com/cli/>`_ to support a CLI interface to NeuroCAAS, as it is platform independent and optimized for performance. You will not need to create an AWS account in order to use the AWS CLI, but you will need to do the following: 

1. Create an account for NeuroCAAS `here <www.neurocaas.org>`_ if you have not already. 
2. Log in on the NeuroCAAS web interface, and click on your name in the top right hand corner of the website to reach your profile. 
3. On your profile, record the following information:   

   - AWS Access Key 
   - AWS Secret Access Key  
   - S3 Bucket For Datasets and config files  

We will use this information to set up the CLI and submit work to NeuroCAAS. 
Once you have this information, please follow the instructions here `AWS CLI <https://aws.amazon.com/cli/>`_ to install the CLI for your platform. Use the AWS Access Key and Secret Access Key you retrieved earlier to configure your CLI when prompted.  

To confirm that installation was successful, run the command :code:`aws s3 ls` and confirm that you see a list of cloud storage buckets. If you do not, contact an AWS administrator with your issues, or submit an issue on GitHub.  

Basic Usage
-----------

Once you have the AWS CLI set up correctly, you can start working with NeuroCAAS analyses. All user interaction on NeuroCAAS happens by uploading and downloading files from cloud storage, which in this case corresponds to **AWS S3 Buckets**. Each bucket that you see when you run the command `aws s3 ls` corresponds to a different analysis. Within each bucket, you will see that each user group has a directory, that lets them manage their analysis related data and results. 

Navigating your files
~~~~~~~~~~~~~~~~~~~~~

In order to use a particular analysis, you will first need to identify what S3 bucket it corresponds to. For example, all users have access by default to the analysis CaImAn, which corresponds to the bucket :code:`caiman-ncap-web`. For a full list of analyses and corresponding buckets, see the NeuroCAAS repository  `here <https://github.com/cunningham-lab/neurocaas>`_. Within each bucket you have access to, you will have a directory where you can manage your use of that particular analysis. This directory name is given by the :code:`S3 Bucket For Datasets and config files` parameter you recovered from the NeuroCAAS website. For example, if this directory name is :code:`user1`, and you want to use CaImAn, all of your work with CaImAn can be done with files at :code:`s3://caiman-ncap-web/user1/`. Within this directory, you will see the following structure: 

.. code-block:: 

  s3://caiman-ncap-web/user1/   
  |- inputs/ 
  |- configs/ 
  |- submissions/ 
  |- results 
   
You can explore each of these directories by running the command :code:`aws s3 ls s3://caiman-ncap-web/user1/{inputs,configs,submissions,results}`. Note that you will not be able to list the contents of other user directories. 

Uploading Data
~~~~~~~~~~~~~~

You can upload data and configuration files to the :code:`{inputs,configs}` subdirectories indicated above. Note that you cannot download data from the inputs directory, so you cannot use NeuroCAAS as free file storage (you can delete files, however). 

Assuming you have some data on your local machine at `/path/to/data`, to upload data from your local machine to NeuroCAAS you can run :code:`aws s3 cp /path/to/data s3://caiman-ncap-web/user1/{inputs,configs}/data`. This will create a file named :code:`data` in storage. To delete the file, you should run `aws s3 rm s3://caiman-ncap-web/user1/{inputs,configs}/data`. You can also upload directories using the :code:`aws s3 sync` command, instead of `aws s3 cp`. 

Submitting Jobs
~~~~~~~~~~~~~~~

To submit jobs to NeuroCAAS, you will upload a special file to NeuroCAAS, which we call a submit file.A submit file is a :code:`JSON` file that has the fields :code:`dataname,configname,timestamp`, as follows: 

.. code-block:: json

    {
       "dataname": ["user1/inputs/data"],
       "configname": "user1/configs/config.yaml",
       "timestamp": "unique_timestamp"
    }

You can write this file on your local machine. Note that the :code:`dataname` and :code:`configname` parameters are paths to the input data and configuration file you want to use for analysis, without the s3 bucket prefix. Additionally, you can pass a string or list to the :code:`dataname` parameter. If you pass a list, the analysis will be parallelized across each data file in the list, using the same configuration file. Finally, the :code:`timestamp` parameter is a unique timestamp that will be used to write an output directory where the outputs of your job will be stored.     

You can start a job by saving your submit file as any file suffixed as :code:`submit.json`. You should upload this file to the :code:`submissions`, using the command :code:`aws s3 cp submit.json s3://caiman-ncap-web/user1/submissions/`.  

Note that this file is generated automatically when you click the "submit" button on the NeuroCAAS website.



Monitoring Jobs
~~~~~~~~~~~~~~~

Once you upload a submit file, a result directory for the corresponding job will be generated at :code:`s3://caiman-ncap-web/user1/results/job__caiman-ncap-web_{unique_timestamp}`, where the timestamp is what you provided in the :code:`timestamp` field of your submit file. You can monitor jobs by looking in the directory :code:`s3://caiman-ncap-web/user1/results/job__caiman-ncap-web_{unique_timestamp}/logs`. You can find two types of files here:  

- certificate.txt: There will always be one certificate file that uniquely identifies a job. It will contain any logging and error information related to the startup of the job you requested, and will print high-level information about all the IAEs are running in real time. 
- DATASET_NAME_{}.txt: If you request processing for multiple IAEs in parallel, each will generate a detailed log that contains the standard error and standard output from the IAEs console, as well as live information on the IAEs memory and CPU usage, and the amount of time it has been running. 

You can monitor job process by downloading these files to your local computer, and opening them. Run the command :code:`aws s3 cp s3://caiman-ncap-web/user1/results/job__caiman-ncap-web_{unique_timestamp}/logs/{certificate.txt,DATASET_NAME_{}.txt} /path/to/local/location/` to download them.  
 
Downloading Results
~~~~~~~~~~~~~~~~~~~

Finally, all results that your analysis generates will be sent to the folder :code:`s3://caiman-ncap-web/user1/results/job__caiman-ncap-web_{unique_timestamp}/process_results`. You can download them all at once with the command :code:`aws s3 sync s3://caiman-ncap-web/user1/results/job__caiman-ncap-web_{unique_timestamp}/process_results/ /path/to/local/location/`. Note that when processing finishes, it will upload a file called :code:`end.txt` to the :code:`process_results` folder, which you can monitor for to detect if the analysis is done.   


Advanced Usage
--------------

Storage Bypass (June 9th, 2022)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have especially large datasets or analysis outputs, it may be prohibitively slow to first transfer them to NeuroCAAS, analyze them, and remove the analysis outputs, especially as we do not allow users to use NeuroCAAS itself to analyze data. For these cases, we can offer a "Storage Bypass" option: if you have access to your data in a publically accessible S3 bucket, you can read and write directly to that bucket. Timestamped outputs and logs will be delivered back to the storage location of your choice. In order to make use of this feature, modify your submit files as follows: 

.. code-block:: json

    {
        dataname: [s3://inputbucket/sep_inputs/file.ext],
        configname: [s3://inputbucket/sep_configs/configsep.json],
        timestamp: timestamp
        [resultpath: s3://outputbucket/sep_results], 
    }

Modifications to the original submit file format are presented in brackets. Note that here we assume the following: 

- data and configuration files come from a public bucket, and can be accessed by anyone.
- data and config must come from the same input bucket, but no longer require an explicit group
- results will be written to a subfolder of the optionally different output bucket.

Finally, older analyses last deployed before this feature will need to be updated in order to work correctly with it. We are actively updating analyses at this time to standardize interfaces across analyses, but if you encounter any issues please contact neurocaas@gmail.com and we can expedite updates. 
