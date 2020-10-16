from script_doc_utils import *

if __name__ == "__main__": 
    md = initialize_doc({"prev":"update_10_14_20"})
    md.new_header(title = "Summary",level = 1)
    md.new_paragraph("Today we prototyped the use of docker for our purposes. New things that I did not know:")
    
    md.new_list(["In a Dockerfile, one specifies a base image, requirements, and file system. These things can be updated efficiently through the use of a cache. Updating the file system is very very fast if one structures the dockerfile correctly (namely, if copying over files comes last. See neurocaas_contrib/Dockerfile).","Docker is inherently tied to individual processes. Once the process dies, the default behavior for a docker container is to exit.","Although one specifies a command for docker to run in the Dockerfile, it can be overwritten at runtime by passing an alternative command. This allows for interactive debugging by specifying 1) the -it flag, and 2) /bin/bash as the command to be run.","Containers are in esssence immutable analysis environments up to infrastructure. We should leverage this. They can be monitored posthoc with docker logs for stdout and stderr, and likewise can be restarted after they exit for inspection.", "Credential management: Managing Credentials inside an ec2 instance is easy, just use the same instance profile. Managing credentials locally is a bit harder- we can generate temp credentials, and copy them to a container via a volume (bind mounting to `root/.aws/credentials`)"])
    md.new_paragraph("How is this useful for us? 1. Updating a docker container is fast. Most rebuilds that are relevant for algorithm development can be done very quickly simply by copying over the appropriate files. 2. There is a version of neurocaas-contrib where we just need to give s3 credentials, and users emulate a deployment environment locally. This would be pretty ideal. 3. Even without this, containers (through ecs) open up a much easier update framework than what we currently have, all through the python api! 4. This makes the possibility of 'neurocaas local' much more real; whether that means deploying a container locally, or having an existing cluster these jobs get deployed to, this would be pretty cool as an extension. ")
    md.new_line("Todos: ")
    md.new_list(["make a minimal toy case work smoothly inside the container.","rewrite your utils in terms of a python codebase.","developer docs md file.","use this to update the carcea pipeline."])
    md.new_header(title= "Discovered API", level = 2)
    md.new_line("`docker images`: Lists the images that you have currently built. Note that the file sizes can be misleading, as some containers are built off of others and do not take up that much space on disk (i think)")
    md.new_line("`docker ps -a`: Lists all containers that are currently running. The flag -a will show stopped containers as well. This is a good way to get the randomly assigned names of containers.")
    md.new_line("`docker [container,image,system] prune`: with the correct choice of bracketed argument, removes all unused versions of that argument")
    md.new_line("`docker build -t [image name] .`: build a docker image. run this command in a directory that contains a dockerfile. ")
    md.new_line("`docker run [image name] --name [container name]`: creates a container layer on top of an image, and runs the command given in the corresponding dockerfile. If you want, you can give the name of the container which will make it easier to find later")
    md.new_line("`docker run [image name] -d --name [container name]`: creates a container layer on top of an image, and runs the command given in the corresponding dockerfile. Does so in detached mode (background process) with -d flag. stdout will not print, check logs instead.")
    md.new_line("`docker run [name] [command]`: creates a container layer on top of an image, and runs the given command instead of the dockerfile")
    md.new_line("`docker run --name [container name] --rm -i -t -d [name] [command]`: creates a container layer on top of an image, and prepares it to accept input to bash. Options as follows: 'rm':  remove after exiting. 'i': interactive. '-t' allocate a pseudo-TTY. -d 'detach'")
    md.new_line("`docker run -it [name] /bin/bash`: creates a container layer on top of an image, starts an interactive shell session. **INCREDIBLY useful for debugging, although you won't have a text editor unless you install one manually.**")
    md.new_line("`docker run -v [relative/path/to/local/credentials:/root/.aws/credentials:ro] [name] [command]`: bind-mounts the credentials file to your container as read only. Recommend using temporary credentials for this. ")
    md.new_line("`docker logs [container name]`: provides the stdout and stderr output given by the container. useful for writing logs!")
    md.new_line("`docker exec [name] [command]`: Execute arbitrary shell tricks. ")
    md.new_line("`docker commit`: I don't know if this is all the correct syntax, but it will take changes you have made to your container and create from it a new image.")
    md.new_line("\n")
    md.new_line("\n")

    md.new_line("Unresolved api tricks: passing parameters. see this site for more info: "+md.new_inline_link(text = "here",link = "https://manifold.co/blog/arguments-and-variables-in-docker-94746642f64b"))
    md.new_line("Additional tips for debugging with docker: see "+md.new_inline_link(text = "here",link = "https://medium.com/@betz.mark/ten-tips-for-debugging-docker-containers-cde4da841a1d"))



    

    md.create_md_file()
