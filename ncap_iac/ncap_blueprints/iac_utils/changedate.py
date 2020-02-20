## Script to change the date in a json file 
from datetime import datetime
import json 
import sys
 
if __name__ == "__main__":
    filepath = sys.argv[1]
    currenttime = str(datetime.now())[:-3].replace(" ","T")+"Z"
    with open(filepath,"r") as f:
        dicto = json.load(f)
        print(dicto)
        dicto["Records"][0]["eventTime"] = currenttime
        print(dicto)
    filename_now = filepath.split(".json")[0]+"_now.json"
    with open(filename_now,"w") as f:
        json.dump(dicto,f)

    

