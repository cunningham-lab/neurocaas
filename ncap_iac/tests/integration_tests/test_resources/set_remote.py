import json

## Get the location that we will upload to: 

with open("test_params.json","r") as params:
    paramdict = json.load(params)
    groupname = paramdict["groupname"]
    bucketname = paramdict["bucketname"]


## What are the names of the files we will be updating? 
singles = ["i-1costhigh.json","i-1costlow.json"]
folderfiles = ["logfiles_5_{f}/i-5{i}cost{f}.json".format(f = value,i = i+1) for i in range(5) for value in ["low","high"]]
allfiles = singles+folderfiles
## plug these in
for filename in allfiles:
    with open(filename,"r") as f:
        fj = json.load(f)
        current_datapath = fj["datapath"]
        parts = current_datapath.split("/")
        parts[0] = groupname
        new_datapath = "/".join(parts)
        fj["datapath"] = new_datapath
        fj["databucket"] = bucketname
        with open(filename,"w") as openfile:
            json.dump(fj,openfile,indent = 4)

