
Script documentation for file: docker_todos, Updated on:2020-12-10 12:50:21.400101
==================================================================================
 
  
**prev file: [update_11_30_20](./update_11_30_20.md)**
# Todo list for docker workflow
  
A more detailed todo list for the integration of docker into the developer workflow.
- [x] Create a general neurocaas-contrib base image with attached input/output volume
- [x] ~~API to pull this base image to local.~~ have the right dockerfile to set up this image.
- [x] API to launch interactive shell into container based on base image
- [x] API to start, stop, delete and save container into image.
- [x] API to test image locally (docker exec)
- [x] API to pull from remote registry (on dockerhub)
- [ ] Revision of logging files for compatibility
- [ ] API to test image locally (LocalEnv)
- [ ] See if we need to test with Amazon Linux 2 base docker images.[ ] ~~Determine local testing criterion for pull request to be considered.~~ The criterion is exactly the success of a local deployment with localstack. This removes all burden from us to provision AWS resources before a plausible working pipeline can be set up.
- [ ] Command line workflow with console scripts
- [ ] API to push to remote registry (on amazon?)


We want to design a way for analysis developers to easily build their analyses in docker containers. While we can always count on docker-fluent developers to tweak a Dockerfile, it's always nice to have a way to visualize what's going on, and build interactively, even if it leads to larger docker images in the long run. We will start out by making a docker base image that looks like this:
+ root
    + neurocaas_contrib
        + analysis dockerfile
    + io-directory
        + inputs
        + configs
        + results
        + logs


This image will contain the latest version of the neurocaas_contrib repository and a special input-output directory. We wil link this input-output directory to a docker volume on setup to faciliatate easy testing later, and stipulate that developers design their scripts so that incoming data starts in the io-directory and outgoing results end up there as well. Logs will be written to the logs subdirectory so that they can be inspected and modified by developers too.

Once this image is set up, we can run a container from this image and set up a bash shell into the container. From this point forwards, we can create an API that is very similar to the NeuroCAASAMI API, except with everything happening locally in a docker container instead of on a remote instance. At the end of the development process, we would expect a container that looks like this:
+ root
    + neurocaas_contrib
        + analysis dockerfile
        + analysis script
    + installed analysis repo
    + io-directory
        + inputs
        + configs
        + results
        + logs


For most analyses, we will most likely require a second round of testing on the appropriate EC2 instance type similar to what we have now, but having a well setup local workflow should make things significantly easier.
## Update 12/1


We have now completed two elements of our original todo list. The second element is complicated by the fact we're trying to use the AWS ECR to store images, which has weird interactions with the AWS CLI version. Bottom line is that for now, I'm happy to have our developers run `docker pull continuum/anaconda3` to get the base image we used, and then build the image locally.
## Update 12/4


We have now completed an api to run a container, and give users instructions to log in with the bash shell. This is a big step. In addition, we have prototyped the workflow for setting up a new development instance with an analysis from the base image. There are some gotchas there that we should look out for:
- Activating an environment
    - When activating a new conda environment inside a bash script, it appears that `conda activate` does not work, and will cause complaints about the conda not being initialized. If we use `source activate`, these complaints go away.
- Relative paths
    - It's always a pain to do path handling in bash. I have a routine in to automatically naviagate to the script location thanks to a helpful stackoverflow comment. This can be kept in our working example now.
- Documentation
    - Apparently the common method of handling documentation in bash scripts is to have a `usage` function declared at the top of your script. This can then print when you pass the -h switch, so for now the docstring prints at the top of the output always.
- File permissions
    - File permissions can be decieving- for some reason I am able to run bash scripts that only have read/write permissions when run interactively from the shell, but NOT when run via docker exec. Make sure that permissions are correctly configured before beginning testing from outside the container.
- Argument handling
    - When running docker exec, it is very useful to run the bash shell with the -c flag. This will let you parse the string that succeeds this flag as commands to the shell. The correct way to do this is to use single quotes (literals) around the whole command, and standard double quotes nested inside the command.


Now, we need to figure out some diagnostics around running docker containers. Can we time how long the process takes? Can we get the logs more easily than we are doing now? How do we handle failure cases? More pragmatically, it would be good to setup a docker volume in the background so we can work with the process outputs independently. This is probably where your autoscripting wil come in handy.

UPDATE: it looks like it is patently easy to do diagnostics on our instance.  
We can run `docker logs [containername]` to get the output from stdout and stderr at any time. This can be improved further with the `--timestamps` flag to prepend each command with a timestamp, and the --details command to add declared environment variables. We should run all containers in detached mode and read the logs from here.   
We can further get the time that a container was started, the time that it stopped and status code information by running `docker inspect`. This is a much more robust way to keep track of jobs as they are running, and log them afterwards than the periodically outputting setup we have now.   
The right way to incorporate these features into our setup is to create a NeuroCAASLocalEnv object that sets up a local environment (docker volume + directory). This way, we can let developers *locally* test their setup and examine the way logs would be generated, handle different test cases, etc. 
## Update 12/5


Today we took care of the bookkeeping necessary to save containers to new images locally. We are managing this through image tags on the repository neurocaas/contrib, with the suggestion that tags be formatted as [github repo].[commit hash]. We also introduced the api necessary to test containers through docker exec, which should speed things up significantly. Now, the next step is setting up a local version of io-dir, creating a volume from it, and attaching it to containers on startup through the api.
## Update 12/8


We were able to successfully write logs to local. One issue now is how much to make the contents if io-dir mirror the contents in the s3 file. The best thing to do might be to just have it mirror the s3 file contents (as relevant for the analysis) exactly. The only issue here is that when results are written, they are written from inside the docker container. How do we make it so that users still have the freedom to write results into the docker container, but that they stay organized as we would like them to? Where should this logic be handled? One option would be to handle this on container exit. This would introduce a function that moves files around, which we can do via docker diff.
## Udate 12/10


We were able to successfully start testing the log module using localstack. Localstack is a very powerful tool, and taking it seriously is a great idea for our workflow. We should consider as a non-critical update implementing localstack testing features directly into the developer package. By doing so, we can effectively simulate the whole workflow: The appearance of output files in a virtual s3 bucket, as well as generating a submit file to the localstack bucket and watching the whole process take place. This gives us a nice way to slot the current devutils code into a consistent workflow as well, as we would only have to introduce minimal changes in order to make it compatible with localstack. This could also be the foundation for a local workflow, etc...

With more knowledge of localstack and docker, here is a new proposal for a developer workflow.
1. Developer downloads and installs neurocaas_contrib repo + package.
2. Developer interactively builds their compute resources into a docker container on their local machine. (advanced users can just provide a dockerfile with the right image tag)
3. Developer test 1: execute the container and make sure the logs look right (NeuroCAASImage.test_container).
4. Developer test 2: save the container into a new image (NeuroCAASImage.save_container_to_image) and then run that image with the appropriate commands (NeuroCAASImage.run_analysis). See the logs and outputs in the designated local location.
5. Developer test 3: (optional) use localstack to simulate a full run, triggering via submit files and examining the output in a localstack bucket.
6. Developer test 4: Request an AWS instance, and make sure your container works with the instance (important for GPU containers).
7. Submit pull request to neurocaas-contrib repo.
