import script_doc_utils

if __name__ == "__main__":
    md = script_doc_utils.initialize_doc()
    md.new_header(title = "Summary",level = 1)
    md.new_paragraph("Work summary for 11/30. We set up a project board on the neurocaas page to track progress over the next few weeks. We also set up tests on the neurocaas-contrib repo, and developed the autoscripting to the point that makes the most sense without knowing more about the docker implementation. I will now work on the docker implementation as a replacement for the nested script structure: the docker container should be able to do a lot of the work that the main script was doing to begin with.")

    md.create_md_file()
