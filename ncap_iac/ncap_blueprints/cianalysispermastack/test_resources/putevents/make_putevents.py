# Script to make putevents out of submission files. 
import os
import json

## First get the names of all submit files
submit_directory = "../submissions"

## get all files
def submitfile(string):
    return string.endswith("submit.json")
listdir = os.listdir(submit_directory)
filterfiles = filter(submitfile,listdir)

## Get template s3_putevent.json
with open("../s3_putevent.json", "r") as template:
    templatedict = json.load(template)

for submitfile in filterfiles:
    with open(os.path.join(submit_directory,submitfile),"r") as submit:
        submitdict = json.load(submit)
    code = submitdict["exitcode"]
    templatedict["Records"][0]["s3"]["object"]["key"] = "traviscipermagroup/submissions/{}".format(submitfile) 
    name = submitfile.split("submit.json")[0]
    templatedict["code"] = code
    with open("{}_s3_putevent.json".format(name),"w") as newputevent:
        json.dump(templatedict,newputevent, indent = 4)

