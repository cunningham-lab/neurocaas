import json 
import os
import sys

if __name__ == "__main__":
    dirname = sys.argv[1]
    groupname = sys.argv[2]
    usernames = sys.argv[3:]
    assert type(dirname == str)
    assert type(groupname == str)
    assert type(usernames == list)


    with open(os.path.join(dirname,"stack_config_template.json"),'r') as f:
        d = json.load(f)
    ## Initialize a testing pipeline with all the relevant details:
    d["PipelineName"] = dirname
    d["REGION"] = "us-east-1"
    d["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"] = "t2.micro"
    d["Lambda"]["LambdaConfig"]["AMI"] = "ami-061f98a1f90c0d6fd"
    d["Lambda"]["LambdaConfig"]["COMMAND"] = "cd /home/ubuntu; neurocaas_remote/run_main.sh \"{}\" \"{}\" \"{}\" \"{}\"; . neurocaas_remote/ncap_utils/workflow.sh; cleanup"
    d["Lambda"]["LambdaConfig"]["REGION"] = "us-east-1"
    d["Lambda"]["LambdaConfig"]["MAXCOST"] = "300"

    d["STAGE"] = "webdev"
    d["UXData"]["Affiliates"] = [d["UXData"]["Affiliates"][0]]
    d["UXData"]["Affiliates"][0]["AffiliateName"] = groupname
    d["UXData"]["Affiliates"][0]["UserNames"] = usernames 

    with open(os.path.join(dirname,"stack_config_template.json"),'w') as f:
        json.dump(d,f,indent =4)

    ## Now get the main function environment variables:  
    with open(os.path.join(dirname,"test_resources","main_func_env_vars.json"),"r") as env:
        envdict = json.load(env)
    ## Initialize testing pipeline environment variables: 
    envdict["MainLambda"]["AMI"] = d["Lambda"]["LambdaConfig"]["AMI"]
    envdict["MainLambda"]["REGION"] = d["REGION"]
    envdict["MainLambda"]["INSTANCE_TYPE"] = d["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"]
    envdict["MainLambda"]["COMMAND"] = d["Lambda"]["LambdaConfig"]["COMMAND"]
    envdict["FigLambda"]["BUCKET_NAME"] = d["PipelineName"]
    envdict["FigLambda"]["REGION"] = d["Lambda"]["LambdaConfig"]["REGION"] 

    with open(os.path.join(dirname,"test_resources","main_func_env_vars.json"),"w") as env:
        json.dump(envdict,env,indent=4)
