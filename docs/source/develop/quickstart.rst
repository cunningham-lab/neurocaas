.. Comment. 

Quickstart
==========

We'll start with a quick demo to show how one can migrate an existing analysis onto NeuroCAAS. This demo should take about 15 minutes, and at the end you will have a NeuroCAAS-style implementation of PCA that runs entirely on your local machine, as well as a working understanding of the pros and cons involved in putting an analysis on NeuroCAAS. Make sure you have downloaded and installed the :code:`neurocaas_contrib` repo before starting this demo, and that you have activated the neurocaas conda environment with :code:`source/conda activate neurocaas`.  

Inputs and Scripts
------------------

The meat of a developer's work migrating an existing analysis to NeuroCAAS is figuring out the right way to structure inputs, and writing scripts to process those inputs. We have gone ahead and done that here with Principal Components Analysis to provide an illustrative guide. 

All analyses available on NeuroCAAS expect two inputs: a dataset, and a configuration file. Choosing how to divide your dataset in this way will be an important design choice when migrating your analysis to NeuroCAAS. In the case of the PCA demo, the dataset consists of a numpy binary file containing an array to perform PCA on, structured as (n_samples,n_features), and the configuration file has a single field, :code:`n_components`, that determines how many components we want to extract when performing PCA. You can look at examples in the :code:`neurocaas_contrib` repo, under :code:`pca/s3/inputs/data_100_15.npy` and :code:`pca/s3/configs/config.yaml`, respectively.  

After choosing a format for datasets and config files, the most important part of a developer's job when migrating analyses to NeuroCAAS is writing a script that will parse these inputs, and output the results. For the PCA example, you can find this script in the :code:`neurocaas_contrib` directory, under :code:`run_pca.sh`, also shown here:

.. code-block:: bash

    #!/bin/bash 
    set -e 
    ### Bash script to wrap python script pca.py. Passes pca.py the appropriate paths to the dataset, configuration file, and path where results should be written. See pca.py for details 

    ## Move dataset and config file to the appropriate location
    echo "--Moving data and config files into temporary directory--"
    neurocaas-contrib workflow get-data
    neurocaas-contrib workflow get-config

    ## Get the names of the datasets once they have been moved 
    echo "--Parsing paths--"
    datapath=$(neurocaas-contrib workflow get-datapath)
    configpath=$(neurocaas-contrib workflow get-configpath)
    resultpath=$(neurocaas-contrib workflow get-resultpath-tmp)

    echo "--Running PCA--"
    python pca.py $datapath $configpath $resultpath

    echo "--Writing results--"
    neurocaas-contrib workflow put-result -r $resultpath/pcaresults


After a lot of path parsing (we'll get into that later), the meat of this script is the line :code:`python pca.py $datapath $configpath $resultpath`, which takes the data located at :code:`$datapath`, the config file located at :code:`$configpath`, runs Principal Components Analysis using scikit-learn, and saves the resulting model to a pickled file :code:`$resultpath/pcaresults`. 


.. * Starting off: having a working analysis is a necessary step. Take a look at neurocaas_contrib/pca. Has a python script, a folder called "s3", and a bash script. Walk through python script, and data/configs in folder.  
..     * Important points: 
..       * MUST include two inputs: called a dataset, and parameters. Notice these are handled by NeuroCAAS, not passed directly as parameters. 
..       * Assuming you have an analysis in place, these scripts are the most important parts of your job as an analysis developer. Deciding what parameters to take, how input should be structured, and writing log messages throughout. 
..       * it doesn't have to be located anywhere specific 

Running Scripts 
---------------

Given the script above, how to we run it on some dataset that we care about? You may have noticed that the commands to get the path to the dataset and configuration file (:code:`$(neurocaas-contrib workflow get-datapath)`) don't include any reference to information about where this data is located. This is because the script :code:`run_pca.sh` assumes that we have already registered the dataset, configuration file, and the location where we expect results to be delivered before it is run. We can do this registration as follows:  

First, we need to create a working directory for NeuroCAAS to temporarily store data. Assuming you choose this directory to be at /path/to/tmp/dir/, run the following command: 

.. code-block:: bash

    neurocaas-contrib workflow initialize-job -p /path/to/tmp/dir/ 

Now we will register the example dataset and config file:     

.. code-block:: bash

    neurocaas-contrib workflow register-dataset -l /path/to/neurocaas_contrib/pca/s3/inputs/data_100_15.npy 
    neurocaas-contrib workflow register-config -l /path/to/neurocaas_contrib/pca/s3/configs/config.yaml 

We will also register a directory where we want the outputs of the analysis to be dumped:     

.. code-block:: bash

    neurocaas-contrib workflow register-resultpath -l /path/to/neurocaas_contrib/pca/s3/results/ 
    
Registering your dataset, configuration file, and result path with the neurocaas-contrib CLI tool allows it to support manipulation and references to the data later, as seen in the run_pca.sh script. We're now ready to run that script. Assuming you're in the :code:`neurocaas_contrib/pca` directory, this is: 

.. code-block:: bash

   neurocaas-contrib workflow log-command-local -c ./run_pca.sh

Note: if you have :code:`not found` issues, try changing permissions: :code:`chmod 700 ./run_pca.sh`  

You should see a lot of logging information, indicating the output of the analysis run. 
    
Once analysis completes, two things will have happened. First, the fitted model will be output at the results folder, :code:`neurocaas_contrib/pca/s3/results/process_results/pcaresults`. You can work with this model by loading it back into python via pickle.

Second, a lot of logging information will have been printed to :code:`neurocaas_contrib/pca/s3/results/logs`: a file :code:`DATASTATUS.json` will carry info about when your analysis started and finished, whether it succeeded or not, the amount of memory and cpu used at last count, and the output written out to the user. A second file :code:`log.txt` will carry just the output to stdout/stderr. Another file :code:`certificate.txt` will carry a more concisely summarized version of this information. We'll discuss the role of each of these files later.  

We call the full loop of pulling from a registered location, analyzing it, and pushing the results and logs back a NeuroCAAS "job".

Putting it all together
-----------------------

At this point, this may all seem a bit contrived. Why do we have to go through the process of registering datasets, configuration files, and result paths, and why do we need a special CLI command to log outputs to file? The answer is that the process above, processing inputs and passing results to the local folder :code:`neurocaas_contrib/pca/s3` generalizes `directly` to inputs and results that are located in the cloud, in AWS S3 cloud storage. Just by registering files and data paths located on the cloud, we can run the exact same script to transfer data to and from remotely located user storage.   

As you develop your own analysis, this means that you can easily switch back and forth between pulling in remote inputs, and testing your scripts locally. Feel free to change the logging or output of this PCA analysis, or use it as the basis for your own. 

The rest of this guide will cover the process of taking this script, along with whatever source code and dependencies you might need, matching it with the appropriate hardware, testing the system end to end, and deploying it for others to use.  

Closing Notes
~~~~~~~~~~~~~

- Note that although the script for the PCA analysis and many others are located in the :code:`neurocaas-contrib` repo, they can be located anywhere, as you will be using your command line tool. A good choice would be a Github repository where you keep your analysis source code. 

- The script that you develop for your own analysis might be dependent on available hardware (GPU, multi-core, etc.). You may want to hold off on building certain parts of your analysis script until you have this hardware available (see the Full Guide, below), but it's a good idea to plan out what you want your dataset and config files to look like before you do so.    

- You'll notice ethat we didn't touch the :code:`neurocaas` source repo at all during this process. This is because the source repo is a place where we store the details of a stable analysis that is ready to use- once you go through the above process with your own analysis, and choose appropriate hardware, the results will get saved to the `neurocaas` source repo.   
    
.. * Try changing the logging, changing the output, and examining the results to see what happens.   




