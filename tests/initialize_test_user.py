import json 
import os
import sys

if __name__ == "__main__":
    dirname = sys.argv[1]

    with open(os.path.join(dirname,"user_config_template.json"),'r') as f:
        d = json.load(f)
    print(d["UXData"]["Affiliates"][0])
    d["UXData"]["Affiliates"][0]["AffiliateName"] = "traviscitestgroup"
    d["UXData"]["Affiliates"][0]["UserNames"] = ["ciuser1","ciuser2"] 
    print(d)

    with open(os.path.join(dirname,"user_config_template.json"),'w') as f:
        json.dump(d,f,indent =4)
