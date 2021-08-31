import json 
import os
import sys

if __name__ == "__main__":
    # Should be a string. 
    dirname = sys.argv[1]
    groupname = sys.argv[2]
    

    with open(os.path.join(dirname,"test_resources/s3_putevent.json"),'r') as f:
        d = json.load(f)
    ## Initialize a testing pipeline with all the relevant details:
    arn = "{p}:::{b}".format(p=d["Records"][0]["s3"]["bucket"]["arn"].split(":::")[0],b=dirname)

    d["Records"][0]["s3"]["bucket"]["name"] = dirname
    d["Records"][0]["s3"]["bucket"]["arn"] = arn

    d["Records"][0]["s3"]["object"]["key"] = os.path.join(groupname,"submissions","submit.json")

    with open(os.path.join(dirname,"test_resources/s3_putevent.json"),'w') as f:
        json.dump(d,f,indent =4)
