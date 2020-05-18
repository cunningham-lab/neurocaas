import sys
import os
import numpy as np
import pandas as pd
from calculate_cost import getCustomMetrics 

if __name__ == "__main__":
    try:
        path = sys.argv[1]
    except IndexError: 
        raise ValueError("please provide the path to the cost file you would like to analyze.")

    except FileNotFoundError: 
        raise ValueError("file not found at specified location. Please ensure the path is correct.")

    templatefilename = "template_{}_{}"
 
    output = getCustomMetrics(path)
    LCC = output[0].squeeze()
    LUC = output[1].squeeze()

    if LCC.shape == (5,3,2):
        arrays = [["small","medium","large"]*2,["Standard","Save"]*3]
        columns = pd.MultiIndex.from_arrays(arrays,names = ["Dataset Size","NeuroCAAS Analysis Mode"])
        index = pd.Index(data = range(1,6), name = "Hardware Lifetime (Years)")
        LCCdf = np.concatenate([LCC[:,i,:] for i in range(3)],axis=1)
        LUCdf = np.concatenate([LUC[:,i,:] for i in range(3)],axis=1)
    elif LCC.shape == (5,2):
        columns = pd.Index(data = ["Standard","Save"],name = "NeuroCAAS Analysis Mode")
        index = pd.Index(data = range(1,6), name = "Hardware Lifetime (Years)")
        LCCdf = LCC # = np.concatenate([LCC[:,i,:] for i in range(3)],axis=1)
        LUCdf = LUC #np.concatenate([LUC[:,i,:] for i in range(3)],axis=1)
    else:
        print(LCC.shape)



    dataframeLCC = pd.DataFrame(LCCdf,columns = columns, index= index)
    LCCsavepath = os.path.join(os.path.dirname(path),templatefilename.format(os.path.basename(path.split(".yaml")[0]),"LCC"))
    dataframeLCC.to_csv(LCCsavepath)
    dataframeLUC = pd.DataFrame(LUCdf,columns = columns, index= index)
    LUCsavepath = os.path.join(os.path.dirname(path),templatefilename.format(os.path.basename(path.split(".yaml")[0]),"LUC"))
    dataframeLUC.to_csv(LUCsavepath)
    print("\nLCC for Custom Data:\n\n",dataframeLCC)
    print("See file {} for saved LCC data.\n".format(LCCsavepath))
    print("LUC for Custom Data:\n\n",dataframeLUC)
    print("See file {} for saved LUC data.".format(LUCsavepath))
