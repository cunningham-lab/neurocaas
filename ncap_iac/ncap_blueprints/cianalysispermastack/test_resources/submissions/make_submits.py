import json
import datetime
import os
import sys

if __name__ == "__main__":
    ## Declare inputs. 
    inputs = ["dataset1.json",["dataset1.json","dataset2.json"],"datasets/","dataset_fake.json",["dataset1.json","dataset_fake.json"]]
    input_succeeds = [True,True,True,False,False]
    ## Declare configs.
    configs = os.listdir("../configs")
    print(configs)
    config_succeeds = [name != "config_broken.json" for name in configs]
    configs.append("config_fake.json")
    config_succeeds.append(False)

    ## We will code these numerically and include a path to the s3 group. Include a success or failure code with each to indicate what the test result should be.   
    groupname = "traviscipermagroup"
    input_dict = {}
    for ind,inp in enumerate(inputs):
        if type(inp) is str:
            input_dict[ind] = {"path":os.path.join(groupname,"inputs",inp),"code":input_succeeds[ind]}
        elif type(inp) is list:
            input_dict[ind] = {"path":[os.path.join(groupname,"inputs",inpi) for inpi in inp],"code":input_succeeds[ind]}

    config_dict = {ind:{"path":os.path.join(groupname,"configs",conf),"code":config_succeeds[ind]} for ind,conf in enumerate(configs)}

    index_list = [(i,j) for i in range(len(input_dict)) for j in range(len(config_dict))]
    for i,j in index_list:
        input_data = input_dict[i]
        config_data = config_dict[j]
        dataname = input_data["path"]
        configname = config_data["path"]
        condition = "condition_{i}_{j}".format(i=i,j=j)
        timestamp = str(datetime.datetime.now()).split(" ")[-1]+condition
        boolcode = input_data["code"] and config_data["code"]
        if boolcode == True:
            code = 0
        else:
            code = 99

        submitdict = {
                "dataname":dataname,
                "configname":configname,
                "timestamp":timestamp,
                "exitcode":code
                }
        with open("{}submit.json".format(condition),"w") as s:
            json.dump(submitdict,s,indent = 4)
    with open("input_data.json","w") as iw:
        json.dump(input_dict,iw,indent = 4)
    with open("config_data.json","w") as cw:
        json.dump(config_dict,cw,indent = 4)

