## README file for Nature Software Policy. 

The process of using NeuroCAAS is significantly different from standards in the field for the usage of data analysis algorithms. We have filled out this README to reflect the process of using analyses that we offer on the NeuroCAAS site (www.neurocaas.org) 

## System Requirements: 
+Using NeuroCAAS does not require any specific software dependencies or operating system. It only requires an internet connection and a web browser. We have tested our system with Safari v13.1 and Google Chrome v81.0.4044.138, running on Mac OSX v10.13.6. We encountered display issues for our website with Firefox v16.0.2 that are currently being addresssed. 

## Installation Guide: 
+ Instructions: 
  1. Navigate to the NeuroCAAS site (www.neurocaas.org)
  2. Select an analysis to use under "Available Analyses" 
  3. Click on "Start Analysis" at the bottom of the page
  4. Provide your credentials: 
      AWS ACCESS KEY: AKIA2YSWAZCC7QNRMKMZ
      AWS SECRET ACCESS KEY: 39juEWSC7AmlhFtztiStpDpDge/G55NQQFSW/+gX 
+ We have encountered no significant delay times in getting NeuroCAAS set up for use. 

## Demo: 
+ Usage instructions and expected outputs are provided at the landing page for each analysis. Demo data is provided for each algorithm in the "inputs" area. 
+ Expected run times are as follows:  
  EPI:   
  [Any Dataset]

  CaImAn:
  [images_YST] 
  [N.01.01]

  DLC:
  [data-reaching.zip (training)]
  [reachingvideo1.avi (tracking)]
 
  LocaNMF: 
  [Vc_Uc.mat]
  
  Penalized Matrix Decomposition:
  [demoMovie.npy]
  
## Instructions for use: 
+ NeuroCAAS can be run on the experimental data that we used to generate results shown in Figure 4 in exactly the same way that it is run on the demo data provided.   
+ The timing data used to generate Figure 4 can be found in the neurocaas repository, in experiments/{analysis_name}/batch_{}.json files. Analogous datasets for local processing can be found in experiments/{analysis_name}/Manual_Data.json. The plots shown in Figure 4 can be reproduced by installing the neurocaas repository (see README in the github repo [https://github.com/cunningham-lab/neurocaas/blob/master/README.md]) and performing the steps listed there under the "To Reproduce Experiments" header.     

