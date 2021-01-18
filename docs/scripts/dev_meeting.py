import script_doc_utils

if __name__ == "__main__":
    md = script_doc_utils.initialize_doc()
    md.new_header(title = "Aggregating information from churchland lab meeting 11/9/20 and developer meetin 11/10/20",level = 1)
    md.new_paragraph("Joao's feedback from meeting 11/9 is that most useful features would be being able to track jobs as they are running, and being able to cancel them as the developer. One interesting thought in this direction is that these features could be built for the dev directly from a blueprint. Given a blueprint that references the right (deployed) resources, we could deploy a GUI that shows the users signed up to use the stack, the number of people currently working, cost, success to failure rate, etc. This could work as an extension of the current NeuroCAAS AMI interface. Let's look into this more. ")
    md.new_header(title = "Developer meeting",level = 2)
    md.new_header(title = "Discussion Forum",level = 3)
    md.new_paragraph("Slack seems fairly limited, especially re: searchability. Gitter might be a good option- there is good github integration and referencing of issues, so using issues extensively + gitter is probably a good choice. Implement this. ")
    md.new_header(title = "Pain Points",level =3)
    md.new_paragraph("The developer guide is 1) pretty dense, and 2) still had significant holes. Try to ease the transitions a bit more: show some images of what things should look like if you did something correctly, and simultaneously be prescriptive about what should come next. Take a look at Sian's comments on the latex version, and incorporate these into the markdown version.")
    md.new_paragraph("In the future, maybe have a nice 'hello world' example that people can play with.")
    md.new_header(title = "Features",level = 3)
    md.new_paragraph("Having a nice way to do integration of new features via pull requests would be really cool. Likewise being able to develop through docker containers (although this seemed less exciting than the integration step.)")



    md.create_md_file()
