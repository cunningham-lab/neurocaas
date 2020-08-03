[![Build Status](https://travis-ci.com/cunningham-lab/neurocaas.svg?branch=master)](https://travis-ci.com/cunningham-lab/neurocaas)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg)](code_of_conduct.md)

Main repository for the [NeuroCAAS project](http://www.neurocaas.org), providing a neuroscience analysis platform using Infrastructure-as-Code (IaC).

This repository hosts all of the Code that makes up our IaC approach, with structure as described in the [paper](https://www.biorxiv.org/content/10.1101/2020.06.11.146746v1).

Please note that this project is released with a Contributor Code of Conduct, [here](ContributorCovenant.md).

Structure: 
- paper (material specifically related to the NeuroCAAS paper)
- docs (documentation and developer guides)
- media (demo movies, slides, etc.)
- experiments (benchmarking code for NeuroCAAS on existing algorithms)
- ncap\_iac (the core code of the project)
    - ncap blueprints (code representing analysis pipelines.)
    - user profiles (code representing users.)
    - protocols (code representing job management coordination analysis pipelines and users.)
    - utils (utilities to compile the above code into the corresponding infrastructure. Interfaces with troposphere and the AWS CLI)

### To Reproduce Experiments: 
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

### Customized Infrastructure Comparisons
To run our comparison analysis on your own infrastructure, navigate to the "experiments" directory and follow the directions found in the guide there. 

### To Contribute Analyses: 
See the [developer guide](docs/NeuroCAAS_Developer_Guide.pdf)

### Project Roadmap.
See the [roadmap](Project_Roadmap.md) for expected timeline of new analyses, new features, and supplementary packages for this project. 

