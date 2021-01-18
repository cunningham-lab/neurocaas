import script_doc_utils

if __name__ == "__main__":
    md = script_doc_utils.initialize_doc()
    md.new_header(title = "Summary",level = 1)
    md.new_paragraph("Work summary for 11/30. We set up a project board on the neurocaas page to track progress over the next few weeks. We also set up tests on the neurocaas-contrib repo, and developed the autoscripting to the point that makes the most sense without knowing more about the docker implementation. I will now work on the docker implementation as a replacement for the nested script structure: the docker container should be able to do a lot of the work that the main script was doing to begin with.")
    md.new_header(title = "Project Board",level =2)
    md.new_paragraph("The neurocaas project board"+md.new_inline_link(link = "https://github.com/cunningham-lab/neurocaas/projects/1",text = " (found here)"+" collects together the various todo items across package development, paper writing, and documentation that will define the next phase of the project. We will also try using kanban style productivity tools for clarity and transparency."))
    md.new_header(title = "CI testing",level =2)
    md.new_paragraph("We have now set up basic tests on the neurocaas-contrib repo integrated with travis. This was more difficult than one might expect due to the degree to which our package interacts with its environment (checking that conda environments exist, for example), but it will be a good reference implementation for more complex deployments in the future. It's also the first time that we've tested a bona fide python package in ci, which is a good step.")
    md.new_header(title = "Autoscripting",level = 2)
    md.new_paragraph("The overall goal of autoscripting is to reduce the need for the developer to keep in mind environment variables declared elsewhere, or work with the AWS CLI api when building their analyses. However, as we built this out (handling setup of anaconda environments, sourcing of bash scripts, pulling inputs) it has become clear that this process will depend quite a bit on the docker implementation. In particular, we could standardize bash script calls to use sudo -u "+md.new_inline_link(link = "https://github.com/cunningham-lab/neurocaas_contrib/issues/2",text = " (see this issue, thanks Jackson and Shuonan) ")+", read stdin/err without a background process "+md.new_inline_link(link = "https://github.com/cunningham-lab/neurocaas/blob/master/docs/script_docs/update_10_15_20.md",text = " (see the docker api you're looking through), ") +" and assure that your process has terminated without relying on the machine to turn itself off.")

    md.create_md_file()
