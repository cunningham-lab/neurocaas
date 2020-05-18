import os 
import numpy as np 
import calculate_cost

## Test the custom cost calculator against the baseline cost calculators. 
path = "Custom_CostFiles/test_templates"
pathtemplate = "hardwarecost{a}_{b}.yaml"
analyses = ["CaImAn","DLC","PMDLocaNMF"]
prices = ["workstation","cluster"]
caimanworkstation = os.path.join(path,"hardwarecostCaImAn_workstation.json") 
caimancluster = os.path.join(path,"hardwarecostCaImAn_cluster.json") 
dlcworkstation = os.path.join(path,"hardwarecostDLC_workstation.json") 
dlccluster = os.path.join(path,"hardwarecostDLC_cluster.json") 
pmdlocanmfworkstation = os.path.join(path,"hardwarecostPMDLocaNMF_workstation.json") 
pmdlocanmfcluster = os.path.join(path,"hardwarecostPMDLocaNMF_cluster.json") 

for analysis in analyses:
    for price in prices:
        if price == "workstation":
            pricing = "PowerMatch"
        elif price == "cluster":
            pricing = "Cluster"
        print("testing {} against {} price".format(analysis,price))
        analysispath = os.path.join(path,pathtemplate.format(a=analysis,b = price))
        baseLCC = calculate_cost.plot_LCC(analysis,pricing = pricing)
        baseLUC = calculate_cost.plot_LUC(analysis,pricing = pricing)
        testLCC,testLUC = calculate_cost.getCustomMetrics(analysispath)
        assert np.all(baseLCC == testLCC)
        assert np.all(baseLUC[1] == testLUC[1])
        assert np.all(baseLUC[3] == testLUC[3])
print("all tests passed")        
