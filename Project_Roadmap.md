# Project Roadmap
### Please refer to this roadmap for expected addition of features to the NeuroCAAS project.
### If you would like to contribute to any of these features, we ask that you read our [contributing guidelines](CONTRIBUTING.md) and let us know through the appropriate channels indicated there.

## Backend Improvements

> Improvements to the IaC platform that forms the backbone of the NeuroCAAS Project.
> Most of these improvements will be implemented as changes to this repo.
> Many of these changes are prerequisites to changes in other sections (see dates).

* Create “hub” users and “member” users: hub user is vetted by us, and assigned a budget- they can share with member users in their group. Reduces vetting burden on us. (Q3 2020)
* Create an option to delete data on successful job completion, set as default.
* Tag compute resources when jobs are launched for higher fidelity monitoring and improved security. (Q3 2020)
* Load test website with Locust. (Q3 2020)
* Move from SSM RunCommand Document based workflow to SSM Automation Document workflow for higher fidelity status updates on job progress/success, cleaner handling of termination. (Q4 2020)
* Move from single Lambda function based execution of jobs to AWS Step Functions. Distributes workload, reduces time that a single lambda function is active, and allows for easy analysis chaining. (Q4 2020)
* Add long term glacier storage in S3 for datasets. Facilitates analysis reproducibility workflows (see next). (Q4 2020)
* Provide DOIs for analysis blueprints+configs+data so they can be referenced, recreated, and cited (Q1 2021)
* Instead of referencing custom built AWS AMIs in blueprints, move to referencing Docker Containers as a more general and easily updated solution. (Q1 2021)
* Move users from IAM to Federated users expand potential user base size. (Q1 2021)
* Add streaming data capability for real time capable analyses by integrating real time workflows with Amazon Kinesis. (Q3 2021)


## Developer Package

> Independent software package for developers who would like to contribute their neuroscience data analyses to NeuroCAAS.

* V1: Streamline installation: remove python contribution api from main repo, package independently. Removes need to download full NeuroCAAS IaC repository. Also streamline job testing: remove  need for developers to manually upload data and write submit files themselves. (Q3 2020)
* V2: Handle Docker integration: given a docker image, load that image onto a provided ami. (Q1 2021)
* V3: Incorporate GUI tools in developer package for per-analysis GUI customization. (Q2 2021)


## Adding Analyses to NeuroCAAS

> Internally managed/developed contributions to NeuroCAAS Platform.
> Goal: Improve the developer package by adding these analyses using successive versions.

* Add YASS/other spike sorters (Q3 - Q4 2020)
* Update DLC to latest version/other pose trackers (Q4 2020)
* Add pipelines for genetics (Q3 2020)
* Add pipelines for generative modeling (Q4 2020)
* Add pipelines for cell segmentation, add GUI for pose trackers requiring manual labels through developer package V3. (Q2 2021)


## Website Development

> Development of the primary interface for this project. Follows many of the backend improvements specified in first section. Will be hosted through subsidiary repo jjhbriggs/neurocaas_frontend.

* Eliminate configuration parameter errors before jobs begin with website based linting (Q3 2020).
* Add support for “hub” and “member” users [see backend improvements] (Q4 2020)
* Introduce workflow for citable analysis workflows with long term glacier storage + DOI provided IaC blueprint (Q1 2021)
* Make analysis progress more easily visible across multiple jobs with GUI (Q1 2021)
* Add demo videos/code for currently hosted analysis algorithms. (Videos: Q3 2020, Code: Q4 2021)


## Programmatic User Package

> Independent software package for users who would like to use NeuroCAAS in code.
> Useful for workflows difficult to integrate with web frontend.

* Brainstorming/prototyping: Find way to easily list all available analyses in package (like passing string to boto3 client?) (Q3 2020)
* Integration with Datajoint Elements for modularity of our analyses with different preprocessing/postprocessing while maintaining data integrity.
* V1: create a package that uploads files to s3, and then downloads them back from s3 once job is completed. (Q3 2021)
* V2: provide option for real time streaming data analysis from generic camera sources (Q4 2021)
