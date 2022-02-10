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


    with open(os.path.join(dirname,"user_config_template.json"),'r') as f:
        d = json.load(f)
    print(d["UXData"]["Affiliates"][0])
    d["UXData"]["Affiliates"] = [d["UXData"]["Affiliates"][0]]
    d["UXData"]["Affiliates"][0]["AffiliateName"] = groupname
    d["UXData"]["Affiliates"][0]["UserNames"] = usernames 
    print(d)

    with open(os.path.join(dirname,"user_config_template.json"),'w') as f:
        json.dump(d,f,indent =4)
