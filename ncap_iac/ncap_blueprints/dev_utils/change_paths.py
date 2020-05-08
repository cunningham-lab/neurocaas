import json 
import sys
import os 

## Loops over all the configs in the tmp_config directory, and changes paths to match.  
thisdir = os.path.dirname(os.path.abspath(sys.argv[0]))
tmpdir = os.path.join(thisdir,"tmp_config")

all_configs = os.listdir(tmpdir)
for config in all_configs:
    with open(os.path.join(tmpdir,config),"rb") as configv:
        configdict = json.load(configv)
    a = configdict["traindata"]["trainpath"].format(sys.argv[1])
    print(a)

