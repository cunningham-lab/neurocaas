Initializing a blueprint
========================

We first need to initialize a blueprint for your analysis that will record you development process.
This portion of the process should take about 10-15 minutes. 
All NeuroCAAS blueprints are stored in a single directory in the source repo, in 
:code:`neurocaas/ncap_iac/ncap_blueprints`. This is where you will create your new analysis as well.  

We will use the CLI tool to create a new analysis here. 

Navigate to the
`ncap_blueprints` directory, and run the command:

.. code-block:: bash

   neurocaas-contrib init --location /path/to/neurocaas/ncap_iac/ncap_blueprints

This will let your CLI tool know that this location is the place it should store analysis blueprints that you develop. 
Upon running this comand, you will be prompted for the name of the analysis you want to develop, and asked to create one if it does not exist already:

.. image:: ../images/init_write.png
   :width: 600

Note that the analysis name must be restricted to lowercase letters, numbers, and hyphens (-). 
If you find yourself working on multiple analyses at once, you can switch between them by running this command as well. 
You can always remind yourself what analysis you are configured to work with by calling the command :code:`neurocaas-contrib describe-analyses`:

.. image:: ../images/describe-analyses.png
   :width: 600

Doing so will list the analyses you have available in your chosen blueprint storage location, as well as the one that is currently initialized (indicated by an asterisk).

Once you have initialized a blueprint, you can examine it in any text editor at the path: 

.. code-block:: bash

   /path/to/neurocaas/ncap_iac/ncap_blueprints/<analysis_name>/stack_config_template.json

This blueprint contains all of the details that specify the different resources 
and services that will support your analysis. When initializing an analysis, 
we can leave most of these fixed, but there are a few that we should go over: 
The parameters that you will probably change are:

- PipelineName: This should be the name of your analysis, or something similar. 

- REGION: The global region (An AWS parameter) where you want to develop. By default "us-east-1" is a good choice.   

- STAGE: This parameter describes different stages of pipeline development. It should be set to "webdev" while initializing a blueprint.

- Lambda.LambdaConfig.INSTANCE\_TYPE: INSTANCE\_TYPE specifies the hardware configuration that is run by
default (can be changed on demand) and is selected from a list of instance types available on AWS. A good default choice is :code:`m5.xlarge`, and a good choice with access to a GPU is :code:`p2.xlarge`. 

Important parameters to keep in mind for later: 
- Lambda.LambdaConfig.AMI: AMI specifies the Amazon Machine Image where your software and dependencies are installed, and contains most of the analysis-specific configuration details that you must specify. As you develop, you will save your progress into different AMIs so they can be linked to the blueprint through this parameter. 

- Lambda.LambdaConfig.COMMAND: COMMAND specifies a bash command that will be run on your remote instance [with parameters specified in the main script section] to generate data analysis. You will most likely not have to change this command, but it is the principal way in which we will be starting analyses on a remote instance. 

For now, remove all Affiliates from the UXData area except for
“debuggers” we will return to these later.


Linking your blueprint to cloud resources
----------------------------------------- 

We have now reached the point where you will have to start interacting with cloud resources, which means that you will need AWS account credentials. 
This portion of the process should take about 10 minutes, and response time from the NeuroCAAS Team (within 24h), or setup time of an AWS account (about 1-2h). 
You can get AWS account credentials by letting the NeuroCAAS team know that you have an initialized blueprint in place. 
We accomplish this using pull requests through Github `(in depth explanation here) <https://blog.axosoft.com/learning-git-pull-request/>`_ . 

First, go ahead and push your new blueprint to your version of the neurocaas repo if you haven't already: 
.. code-block:: bash
    git add /path/to/neurocaas/ncap_iac/ncap_blueprints/<analysis_name>/
    git commit -m "intialized blueprint for <analysis_name>" # or something like that
    git push 

Then, you can go ahead and open a pull request on the original neurocaas Github page (see step 7 `here <https://jarv.is/notes/how-to-pull-request-fork-github/>`_).  
Add a comment to your pull request that specifies what your analysis does, and we will get back to you with AWS account credentials. 

Note that if you develop more blueprints later, you will still submit pull requests, but you can use the same credentials. 

Alternative Account
~~~~~~~~~~~~~~~~~~~
**Skip to Configuring Credentials if you submitted a pull request**
Alternatively, you can also set up development on a separately managed AWS account. NOTE: AWS charges in real time for resource use. Make sure that you know what you are doing (cost monitoring, instance management, privacy settings) before going this route!
To proceed with your own AWS account, you will need admin permissions.
To initialize NeuroCAAS on a separate AWS account, first follow the installation instructions for
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

To continue, you will need to create an IAM user with programmatic access, and at minimum the IAM policies listed in :code:`neurocaas/ncap_iac/permissions/dev_policy.json`. Save the AWS key pair that is generated when you create an IAM user in a safe place outside of version control. 

Configuring Credentials
~~~~~~~~~~~~~~~~~~~~~~~
**Important: this section deals with security credentials. Please proceed carefully.**

From the previous step, you should now have an AWS Key Pair (Key and Secret Key),
either from a pull request, or from an independent account. 
These credentials will allow your to launch cloud compute instances, 
and as such are extremely valuable. 
**IMPORTANT: You MUST keep this file
in separate, secure directory not under version control. If this key is
exposed, it poses financial risks and privacy risks to the entire account.** 

First verify your aws cli installation by running:

.. code-block:: bash

    % aws configure

When prompted, enter the access key and secret access key associated
with your IAM user account, as well as the AWS region you are closest
to. Set the default output type to be :code:`json`.
IMPORTANT: If using the NeuroCAAS account to develop, please set your
AWS region to be **us-east-1**.  

Once you have the aws cli configured with your credentials, you  
have full developer priviledges. You can now additionally retrieve 
an ssh key to let you log in to remote instances and develop on them interactively.

In order to retrieve your ssh key, navigate
within the source repository to:

:code:`/path/to/neurocaas/ncap_iac/ncap_blueprints/utils_stack`. Type the following
command:

.. code-block:: bash

    % bash print_privatekey.sh > securefilelocation/securefilename.pem

Where :code:`securefilelocation/securefilename.pem` is a file NOT under
version control. **IMPORTANT: We strongly recommend you keep this file
in separate, secure directory not under version control. If this key is
exposed, it will expose the development instances of everyone on your
account**. You will reference this key when developing a machine image
later. Finally, change the permissions on this file with:

.. code-block:: bash

    % chmod 400 securefilelocation/securefilename.pem


With these credentials in place, you are now ready to choose the hardware and computing environment for your analysis.     
