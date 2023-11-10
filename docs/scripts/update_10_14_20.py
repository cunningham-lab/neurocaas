from script_doc_utils import *

if __name__ == "__main__":
    md = initialize_doc()
    md.new_header(title= "Notes 10/14/20",level = 1)
    md.new_paragraph("Work resumed today. Removed deprecated credentials from ioana's custom pipeline, and started a test job for zahra at i-0d6eec0077e0b3491")
    md.new_header(title = "Code ideas",level = 2)
    md.new_paragraph("In developer tools, add a `NeuroCAASAnalysis` object that lives above NeuroCAAS AMI. Have it take the same blueprint as input, and then use it to handle various template maintenance tasks. Let it answer questions like:")
    md.new_list(["Who are the subscribed users?","What are the job histories of a given user?","What is the job status of users? (look at cfn)","Where is their output going?","What does their processing code look like?"])
    md.new_line("Having this interface to the cli would dramatically speed up our ability to locate and fix issues. The AMI could even live within the Analysis class, and be called through subroutines in testing.")
    md.new_line("In the vein of ideas that speed up our development, we should really consider ECS. Think about the following workflow:")
    md.new_list(["One pulls the basic developer contrib tools along with an accompanying docker container.","One saves the docker container, and can switch to a cloud deployment through ECS (apparently currently in beta), directly onto an instance that one would like to test on.","One can version control containers without touching the blueprint with revisions, and then fast update via parameters.", "One can use ECS and deploy onto Fargate/Existing cluster for jobs that need to be faster."])
    md.create_md_file()
