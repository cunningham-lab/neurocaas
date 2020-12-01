import script_doc_utils

if __name__ == "__main__":
    md = script_doc_utils.initialize_doc({"prev":"update_11_30_20"})
    md.new_header(title = "Todo list for docker workflow",level = 1)
    md.new_line("A more detailed todo list for the integration of docker into the developer workflow.")
    md.new_list([
        "[ ] Create a general neurocaas-contrib base image with attached input/output volume",
        "[ ] API to pull this base image to local.",
        "[ ] API to launch interactive shell into container based on base image",
        "[ ] API to start, stop, delete and save container into image.",
        "[ ] API to test image locally",
        "[ ] API to push to remote registry (on amazon?)",
        "[ ] Determine local testing criterion for pull request to be considered."
        ])
    md.new_paragraph("We want to design a way for analysis developers to easily build their analyses in docker containers. While we can always count on docker-fluent developers to tweak a Dockerfile, it's always nice to have a way to visualize what's going on, and build interactively, even if it leads to larger docker images in the long run. We will start out by making a docker base image that looks like this:")
    md.new_list([
            "root",
            ["neurocaas_contrib",
                ["analysis dockerfile",
                 ],
                "io-directory",
                ["inputs",
                 "configs",
                 "results",
                 "logs"
                ]
                ]
            ], marked_with = '+')

    md.new_paragraph("This image will contain the latest version of the neurocaas_contrib repository and a special input-output directory. We wil link this input-output directory to a docker volume on setup to faciliatate easy testing later, and stipulate that developers design their scripts so that incoming data starts in the io-directory and outgoing results end up there as well. Logs will be written to the logs subdirectory so that they can be inspected and modified by developers too.")
    md.new_paragraph("Once this image is set up, we can run a container from this image and set up a bash shell into the container. From this point forwards, we can create an API that is very similar to the NeuroCAASAMI API, except with everything happening locally in a docker container instead of on a remote instance. At the end of the development process, we would expect a container that looks like this:") 
    md.new_list([
            "root",
            ["neurocaas_contrib",
                ["analysis dockerfile",
                 "analysis script"],
                "installed analysis repo",
                "io-directory",
                ["inputs",
                 "configs",
                 "results",
                 "logs",
                ]
                ]
            ], marked_with = '+')
    
    md.new_paragraph("For most analyses, we will most likely require a second round of testing on the appropriate EC2 instance type similar to what we have now, but having a well setup local workflow should make things significantly easier.")
    md.create_md_file()

    
    
