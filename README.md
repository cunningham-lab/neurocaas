[![Build Status](https://travis-ci.com/cunningham-lab/neurocaas.svg?branch=master)](https://travis-ci.com/cunningham-lab/neurocaas)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg)](code_of_conduct.md)
![https://readthedocs.org/projects/pip/badge/?version=latest&style=plastic]

Main repository for the [NeuroCAAS project](http://www.neurocaas.org), providing a neuroscience analysis platform using Infrastructure-as-Code (IaC).

This repository hosts all of the Code that makes up our IaC approach, with structure as described in the [paper](https://www.biorxiv.org/content/10.1101/2020.06.11.146746v1).

Please note that this project is released with a Contributor Code of Conduct, [here](ContributorCovenant.md).

Structure: 
- paper (material specifically related to the NeuroCAAS paper)
- docs (documentation and developer guides)
- media (demo movies, slides, etc.)
- experiments (benchmarking code for NeuroCAAS on existing algorithms)
- ncap_iac (the core code of the project)
    - ncap blueprints (code representing analysis pipelines.)
    - user profiles (code representing users.)
    - protocols (code representing job management coordination analysis pipelines and users.)
    - utils (utilities to compile the above code into the corresponding infrastructure. Interfaces with troposphere and the AWS CLI)

### To Contribute Analyses: 
See the [developer guide](https://neurocaas.readthedocs.io/en/latest/index.html).

### To Reproduce Experiments (Figure 10): 
You will need to install the dependencies found in the requirements_experiments.txt file in order to run experiments and compare NeuroCAAS to your own infrastructure. We recommend doing so in a [conda](https://www.anaconda.com) virtual environment. Once you have installed conda, check your installation by running:

```
conda list
```

Then create a new environment as follows: 

```
conda create -n neurocaas_experiments python=3.6
```

Now clone and move into the root directory of this repo. 

```
git clone https://github.com/cunningham-lab/neurocaas.git
cd /path/to/this/repo
```

Activate your new environment, and install necessary packages by running: 

```
conda activate neurocaas_experiments
conda install pip
pip install -r requirements_experiments.txt
```

Navigate to the experiments directory, and run the following to generate png files shown in Figure 4: 

```
python recreate_figure4.py
```

Pngs showing cost and time analyses will be stored in the "panels" subdirectory within each analysis. The files suffixed "Cost", "Time", "LCC_powermatch", and "LUC_powermatch" are those shown in the submitted figure. 
The source code to generate these analyses and figures can be found in the "calculate_cost" module, called by the "getdata_fig4" function.

You can generate the data for custom versions of Figure 4 by filling out a custom cost file. See experiments/Custom_CostFiles/hardwarecost.yaml and experiments/Custom_CostFiles/hardwarecost2.yaml for annotated examples. 
Once you have filled out a cost file, you can run it by executing the following commands: 

```
cd /path/to/local/repo/neurocaas/experiments
python generate_customcomparison.py /path/to/your/costfile.yaml
```

### To Calculate Analysis Usage (Figure 6): 
Developers can calculate analysis usage and parallelism for their own analyses once deployed on NeuroCAAS, as shown in Figure 6. 
First install the neurocaas contrib package. Instructions found at https://github.com/cunningham-lab/neurocaas_contrib. 
Then generate log files for your analysis, to be written to some folder: 

```
neurocaas-contrib init ## enter the name of your analysis
neurocaas-contrib monitor visualize-parallism -p /path/to/logfolder
```

Running this command will generate JSON files that describe individual jobs run by individual users in analysis buckets as: 
`{analysis_name}_{user_name}_{job_timestamp}_parallel_logs.json`, where each log contains individual jobs. 

Then, use the script `neurocaas_contrib/figures/parallelized.py` to create an analogue to Figure 6: 

```
python /path/to/neurocaas_contrib/figures/parallelized.py /path/to/logfolder
```
To generate a figure in that same folder, `parallelism_figure_{date time}.png`. If you have multiple analyses, you can generate the logs for all of them into the same log folder, and the script `parallelized.py` will create a graph that includes all of them. 

Note that the script parallelized.py includes conditional statements to exclude debugging jobs run in the course of creating NeuroCAAS infrastructure as well. 

### Customized Infrastructure Comparisons
To run our comparison analysis on your own infrastructure, navigate to the "experiments" directory and follow the directions found in the guide there. 

### Project Roadmap.
See the [roadmap](Project_Roadmap.md) for expected timeline of new analyses, new features, and supplementary packages for this project. 

