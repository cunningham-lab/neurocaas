import json 
import os
import sys

if __name__ == "__main__":
    dirname = sys.argv[1]

    with open(os.path.join(dirname,"stack_config_template.json"),'r') as f:
        d = json.load(f)
    ## Initialize a testing pipeline with all the relevant details:
    d["PipelineName"] = "citestpipeline"
    d["REGION"] = "us-east-1"
    d["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"] = "t2.micro"
    d["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"] = "ami-061f98a1f90c0d6fd"
    d["Lambda"]["LambdaConfig"]["COMMAND"] = "cd /home/ubuntu; neurocaas_remote/run_main.sh \"{}\" \"{}\" \"{}\" \"{}\"; . neurocaas_remote/ncap_utils/workflow.sh; cleanup"
    d["Lambda"]["LambdaConfig"]["REGION"] = "us-east-1"
    d["Lambda"]["LambdaConfig"]["MAXCOST"] = "300"

    d["STAGE"] = "webdev"
    d["UXData"]["Affiliates"] = [d["UXData"]["Affiliates"][0]]
    d["UXData"]["Affiliates"][0]["AffiliateName"] = "traviscitestgroup"
    d["UXData"]["Affiliates"][0]["UserNames"] = ["ciuser1","ciuser2"] 
    print(d)

    with open(os.path.join(dirname,"stack_config_template.json"),'w') as f:
        json.dump(d,f,indent =4)
