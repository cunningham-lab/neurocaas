import datetime
import numpy as np
import json
import matplotlib.pyplot as plt

## First get difference between two times, given as a list of lists. 

def secdiff(a,b):
    ## Assumbe both are lists representing a time. 
    day = datetime.datetime(1,1,1,0,0,0)
    timea = datetime.time(*a)
    timeb = datetime.time(*b)
    datea = datetime.datetime.combine(day,timea)
    dateb = datetime.datetime.combine(day,timeb)

    diff = abs(datea-dateb).total_seconds()
    return diff

def to_sec(a):
    ## converts a lenght of time to seconds (minutes, ) 
    delt = a[0]*60+a[1]+a[2]/1000.#datetime.timedelta(minutes = a[0],seconds = a[1],milliseconds = a[2])
    return delt

def total_time(upload,start,stop):
    ## First convert start,stop to a duration in seconds: 
    diff = secdiff(start,stop)
    ## Convert upload duration to seconds:
    upsec = to_sec(upload)
    return upsec,diff,upsec+diff

def total_cost(upload,start,stop,lambdaduration,datasize,lambdasize,number):
    ## First get the durations: 
    pre,during,total = total_time(upload,start,stop)
    ## Now, multiply during with the ec2 instance cost: 
    p2x_rate = 0.9/60/60 # almost a dollar an hour. 
    ec2cost = p2x_rate*during*number ## cost per second times seconds. 
    ## Now, get the lambda cost: 
    ## Duration in milliseconds, size in megabytes,cost in gigabyte-seconds
    lambdacost = number*(lambdaduration/1000.)*(lambdasize/1000.)*0.0000166667
    ## Now finally we can think about data transfer cost: 
    transfercost = 0.1*datasize/1000.*number
    return [pre,during],[ec2cost,lambdacost,transfercost] 

## Make an object class to accept a dictionary of parameters and have methods to return the reelvant quantities for us. 
class JobMetrics(object):
    """
    Parameters:
    dictname: path to json object representing one completed ncap job. Fields are described in the sample template provided.
    """
    def __init__(self,jobdict):
        with open(jobdict,'r') as f:
            obj = json.load(f)
        self.dict = obj
        self.convert_times()

    ## Convert times to datetime format:
    def convert_times(self):
        times = self.dict["InstanceComputeTimes"]
        day = datetime.datetime(1,1,1,0,0,0)
        all_intervals = []
        all_diffs = []
        for interval in times:
            ## Convert strings to list format:
            listinterval = [list(map(int,time.split(':'))) for time in interval]
            ## Convert lists to datetime format:
            timea = datetime.time(*listinterval[0])
            timeb = datetime.time(*listinterval[1])
            datea = datetime.datetime.combine(day,timea)
            dateb = datetime.datetime.combine(day,timeb)
            dateinterval = [datea,dateb]
            all_intervals.append(dateinterval)

            diff = abs(datea-dateb).total_seconds()
            all_diffs.append(diff)
        self.computeintervals = all_intervals
        self.computediffs = all_diffs
            
    ## Get the maximum difference between a start time and an end time to get the full compute time. 
    def get_maxdiff(self):
        all_starts,all_ends = zip(*self.computeintervals)
        maxdiff =abs(max(all_ends)-min(all_starts)).total_seconds()
        return maxdiff

    ## Method for calculating the relevant times for our metrics. Returns in seconds. 
    def get_timemetrics(self):
        pretime = self.dict["UploadTime"]
        ## Now what we care about is the maximum compute time. 
        duringtime = self.get_maxdiff()
        return [pretime,duringtime]

    ## Get the compute cost as a function of instance type:
    def get_computecost(self):
        if self.dict['InstanceType'] == 'p2.xlarge':
            costpersec = 0.9/(3600)
        elif self.dict['InstanceType'] == 'm5.16xlarge':
            costpersec = 3.072/(3600)
        self.costrate = costpersec
        self.computecostper = np.array(self.computediffs)*self.costrate
        self.computecost = np.sum(self.computecostper)
        
    ## Get lambda cost:
    def get_lambdacost(self):
        ## times in seconds
        times = np.array(self.dict['LambdaComputeTimes'])/1000.
        ## size in GB
        size = self.dict['LambdaMemory']/1000.
        ## Cost per GBseconds
        self.lambdacostper = times*size*0.0000166667
        self.lambdacost = np.sum(self.lambdacostper)

    ## Get transfer cost:
    def get_transfercost(self):
        ## Keep track 
        ## Get cost per result: 
        self.transfercostper = np.array(self.dict['ResultSizes'])*0.09
        self.transfercost = np.sum(self.transfercostper)

    def get_costmetrics(self):
        self.get_computecost()
        self.get_lambdacost()
        self.get_transfercost()
        return [self.computecost,self.lambdacost,self.transfercost]

## Now plot the time as bar plots, compare to other cases:
def plot_timebar_compare(filepaths,comptimes,xlabels,title):
    """
    Parameters:

    filepaths: a list of filepaths in order that you would like the bars to be in. 
    xlabels: a list of the xlabels to use: 
    """
    metricobjects = [JobMetrics(path) for path in filepaths]
    timemetrics = [job.get_timemetrics() for job in metricobjects]
    pretimes,computetimes = zip(*timemetrics)
    ## Mock local processing
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]

    ind = np.arange(len(xlabels))
    width = 0.10
    offset = 0.1
    fig,ax = plt.subplots(figsize = (22,16))
    ## Plot the actual
    plt.bar(ind+offset,pretimes,label = 'upload',width = width,color = 'blue')
    plt.bar(ind+offset,computetimes,bottom = pretimes,label='compute',width = width,color = 'red')
    ## Plot the local
    #plt.bar(ind12*wid'upload',color = 'blue')
    plt.bar(ind-offset,comptimes,width=width,color = 'red')
    
    ## Plot ticks: 
    offset_inds = np.stack([ind-offset,ind+offset],axis = 1).flatten()
    ax.set_xticks(offset_inds)
    ax.set_xticklabels([xlabels[0]+' (local)',xlabels[0]+" (NCAP)",xlabels[1]+' (local)',xlabels[1]+" (NCAP)",xlabels[2]+' (local)',xlabels[2]+" (NCAP)"],rotation = 25,ha = 'right',fontsize = 38)
    ax.set_title(title,fontsize = 54)
    ax.set_ylabel('Time (seconds)',fontsize = 38)
    ax.set_xlabel('Dataset Size (GB)',fontsize = 38)
    plt.setp(ax.get_xticklabels(),fontsize=38)
    plt.setp(ax.get_yticklabels(),fontsize=38)
    ax.legend(fontsize = 38)
    plt.tight_layout()
    plt.savefig('../Figures/'+title+'.png')
    
## Now plot the time as bar plots, compare to other cases:
def plot_timebar_compare_mock(filepaths,xlabels,title):
    """
    Parameters:

    filepaths: a list of filepaths in order that you would like the bars to be in. 
    xlabels: a list of the xlabels to use: 
    """
    metricobjects = [JobMetrics(path) for path in filepaths]
    timemetrics = [job.get_timemetrics() for job in metricobjects]
    pretimes,computetimes = zip(*timemetrics)
    ## Mock local processing
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]

    ind = np.arange(len(xlabels))
    width = 0.10
    offset = 0.1
    fig,ax = plt.subplots(figsize = (26,16))
    ## Plot the actual
    plt.bar(ind+offset,pretimes,label = 'upload',width = width,color = 'blue')
    plt.bar(ind+offset,computetimes,bottom = pretimes,label='compute',width = width,color = 'red')
    ## Plot the local
    #plt.bar(ind12*wid'upload',color = 'blue')
    plt.bar(ind-offset,np.array(computetimes)*np.array(nb_datasets),width=width,color = 'red')
    
    ## Plot ticks: 
    offset_inds = np.stack([ind-offset,ind+offset],axis = 1).flatten()
    ax.set_xticks(offset_inds)
    ax.set_xticklabels([xlabels[0]+' (local)',xlabels[0]+" (NCAP)",xlabels[1]+' (local)',xlabels[1]+" (NCAP)",xlabels[2]+' (local)',xlabels[2]+" (NCAP)"],rotation = 25,ha = 'right',fontsize = 38)
    ax.set_title(title,fontsize = 54)
    ax.set_ylabel('Time (seconds)',fontsize = 38)
    plt.setp(ax.get_xticklabels(), fontsize=38)
    plt.setp(ax.get_yticklabels(), fontsize=38)
    ax.set_xlabel('Dataset Size (hrs)',fontsize = 38)
    ax.legend(fontsize = 38)
    plt.tight_layout()
    plt.savefig('../Figures/'+title+'.png')

### Plot time as bar plots without comparing to other cases. 
#def plot_timebar_baseline(filepaths,xlabels,title):
#    """
#    Parameters:
#
#    filepaths: a list of filepaths in order that you would like the bars to be in. 
#    xlabels: a list of the xlabels to use: 
#    """
#    metricobjects = [JobMetrics(path) for path in filepaths]
#    timemetrics = [job.get_timemetrics() for job in metricobjects]
#    pretimes,computetimes = zip(*timemetrics)
#    ## Mock local processing
#    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]
#
#    ind = np.arange(len(xlabels))
#    width = 0.10
#    offset = 0
#    fig,ax = plt.subplots()
#    ## Plot the actual
#    plt.bar(ind+offset,pretimes,label = 'upload',width = width,color = 'blue')
#    plt.bar(ind+offset,computetimes,bottom = pretimes,label='compute',width = width,color = 'red')
#    ## Plot the local
#    #plt.bar(ind12*wid'upload',color = 'blue')
#    #plt.bar(ind-offset,np.array(computetimes)*np.array(nb_datasets),width=width,color = 'red')
#    
#    ## Plot ticks: 
#    ax.set_xticks(ind)
#    ax.set_xticklabels([xlabels[0]+' (NCAP)',xlabels[1]+' (NCAP)',xlabels[2]+' (NCAP)'])
#    #offset_inds = np.stack([ind-offset,ind+offset],axis = 1).flatten()
#    #ax.set_xticks(offset_inds)
#    #ax.set_xticklabels([xlabels[0]+' (local)',xlabels[0]+" (NCAP)",xlabels[1]+' (local)',xlabels[1]+" (NCAP)",xlabels[2]+' (local)',xlabels[2]+" (NCAP)"],rotation = 25,ha = 'right')
#    ax.set_title(title)
#    ax.set_ylabel('seconds')
#    ax.legend()
#    plt.show()

## Plot cost as bar plots without comparing to other cases. 
def plot_costbar_baseline(filepaths,xlabels,title):
    """
    Parameters:

    filepaths: a list of filepaths in order that you would like the bars to be in. 
    xlabels: a list of the xlabels to use: 
    """
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics() for job in metricobjects]
    computecost,lambdacost,transfercost = zip(*costmetrics)
    print(computecost,lambdacost,transfercost,'costs')
    ## Mock local processing
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]

    ind = np.arange(len(xlabels))
    width = 0.10
    offset = 0
    fig,ax = plt.subplots(figsize = (36,16))
    ## Plot the actual
    plt.bar(ind+offset,computecost,label = 'compute',width = width,color = 'blue')
    plt.bar(ind+offset,lambdacost,bottom = computecost,label = 'management',width = width,color = 'orange')
    plt.bar(ind+offset,transfercost,bottom = np.array(computecost)+np.array(lambdacost),label = 'transfer',width = width,color = 'red')
    ## Plot the local
    #plt.bar(ind12*wid'upload',color = 'blue')
    #plt.bar(ind-offset,np.array(computetimes)*np.array(nb_datasets),width=width,color = 'red')
    
    ## Plot ticks: 
    ax.set_xticks(ind)
    ax.set_xticklabels([xlabels[0]+' (NCAP)',xlabels[1]+' (NCAP)',xlabels[2]+' (NCAP)'],fontsize = 38)
    #offset_inds = np.stack([ind-offset,ind+offset],axis = 1).flatten()
    #ax.set_xticks(offset_inds)
    #ax.set_xticklabels([xlabels[0]+' (local)',xlabels[0]+" (NCAP)",xlabels[1]+' (local)',xlabels[1]+" (NCAP)",xlabels[2]+' (local)',xlabels[2]+" (NCAP)"],rotation = 25,ha = 'right')
    ax.set_title(title,fontsize = 54)
    ax.set_ylabel('Cost (dollars)',fontsize = 38)
    ax.set_xlabel('Dataset Size',fontsize = 38)
    plt.legend(fontsize = 38)
    plt.setp(ax.get_xticklabels(), fontsize=38)
    plt.setp(ax.get_yticklabels(), fontsize=38)
    plt.tight_layout()
    plt.savefig('../Figures/'+title+'.png')
    plt.show()


## Define a function that takes in a dataset generation rate, an NCAP dataset cost rate, a machine tco and storage rate and caluclates crossovers. 
def plot_TCO_xover_multiple(filepaths,hardware,title,labels,xaxis = [None,None,None]):
    fig,ax = plt.subplots(figsize = (12,14))
    #labels = ['8 GB','36 GB','79 GB']
    for fi,filepath in enumerate(filepaths):
        plot_TCO_xover(filepath,hardware,axes = (fig,ax),label = labels[fi],xaxis = xaxis[fi])
    plt.ylim([0,300])
    plt.legend(fontsize = 38)
    plt.setp(ax.get_xticklabels(), fontsize=38)
    plt.setp(ax.get_yticklabels(), fontsize=38)
    plt.xlabel('Datasets Analyzed Per Week',fontsize = 38)
    plt.ylabel('Weeks',fontsize = 38)
    #plt.title('Crossover point as a function of Data Analysis Rate: Caiman')
    plt.title(title,fontsize = 54)
    plt.tight_layout()
    plt.savefig('../Figures/'+title+'.png')
    plt.show()

def plot_TCO_xover(filepath,hardware,axes = False,label = None,xaxis =None):
    ## Set up axes: 
    if axes == False:
        fig,ax = plt.subplots()
    else:
        fig,ax = axes 
    ## Get average size of dataset (matters for storage)
    metricobj = JobMetrics(filepath)
    sizes = metricobj.dict["DatasetSizes"]

    meansize = np.mean(sizes)
    
    ## Get storage cost per dataset: 
    gb_store = meansize

    ## Convert to cost 
    price_store = 0#0.01250 #gb_store*0.05 ## Assume 50$ per terabyte
    ## Assuming a rate of n datasets per week, this gives: 

    ## Now get the cost per dataset for NCAP
    price_ncap = np.sum(metricobj.get_costmetrics())
    price_ncap_store = (np.sum(metricobj.get_costmetrics())+0.0125)
    print(hardware,price_ncap,price_store)

    # Solve for the crossover point as a function of rate:
    xover = lambda r: hardware/((price_ncap-price_store)*r)
    xover_store = lambda r: hardware/((price_ncap_store-price_store)*r)
    
    #rates = np.arange(1,20*3*24*7)
    if xaxis is None:
        xaxis = np.arange(1,100)
    #ax.plot(rates,xover(rates))
    ax.plot(xaxis,xover_store(xaxis),label = label)
    if axes == False:
        plt.ylim([0,520])
        plt.title('Crossover point as a function of Data Analysis Rate: Caiman, 72 GB')
        plt.ylabel('Weeks')
        plt.xlabel('Datasets Analyzed Per Week')
    
def plot_TCO_rate(filepath,hardware,rate):
    ## Set up axes: 
    fig,ax = plt.subplots()
    inds = np.arange(150)
    ## Get average size of dataset (matters for storage)
    metricobj = JobMetrics(filepath)
    sizes = metricobj.dict["DatasetSizes"]

    meansize = np.mean(sizes)
    
    ## Get gb per week: 
    gb_store = meansize*rate
    ## Convert to cost 
    price_store = 0#gb_store*0.05 ## Assume 50$ per terabyte
    ## Assuming a rate of n datasets per week, this gives: 
    ax.plot(inds,hardware+price_store*inds,label = 'Local')

    ## Now get the cost per week for NCAP
    #price_ncap = np.sum(metricobj.get_costmetrics())*rate
    price_ncap_store = (np.sum(metricobj.get_costmetrics())+0.0125)*rate

    # Solve for the crossover point:
    #xover = hardware/(price_ncap-price_store)
    xover_store = hardware/(price_ncap_store-price_store)
    

    #ax.plot(inds,price_ncap*inds)
    ax.plot(inds,price_ncap_store*inds,label = 'NCAP')
    plt.xlabel('Weeks')
    plt.ylabel('Cost')
    ax.axvline(x = xover_store,color = 'black')
    plt.title('Cost over time, Caiman, 78 GB per dataset, 5 datasets per week')




## Let's make a TCO crossover calculator that takes in 1 ncap dataset and one comparison implementation. 

def plot_cost_TCO_datasetsxover(filepaths,tco,title):
    fig,ax = plt.subplots()
    ## Get the x axis in terms of datasets analyzed. 
    ind = np.arange(20000)

    plt.axhline(y = tco,linestyle = '--',color = 'red',label = 'base cost (Tesla K80)')
    #plt.axhline(y = tco+298+74+125,linestyle = '--',color = 'blue',label = 'tco estimate')
    ## Get the cost for the dataset: 
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics() for job in metricobjects]
    totalcost = [np.sum(costmetric) for costmetric in costmetrics]
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]
    ## Normed cost per unit
    normed = np.array(totalcost)/np.array(nb_datasets)
    mean = np.mean(normed)
    std = np.std(normed)
    print(mean,std)
    plt.plot(ind,mean*ind,'black',label = 'NCAP')
    plt.plot(ind,(mean+std)*ind,'black',linestyle ='--')
    plt.plot(ind,(mean-std)*ind,'black',linestyle ='--')
    plt.xlabel('Datasets Analyzed (225 MB, 20 minutes)')
    plt.ylabel('Cost (Dollars)')
    plt.legend()
    plt.title(title)




## Now make a TCO crossover calculation: 
def plot_cost_TCO_datasets(filepaths,tco,title):
    fig,ax = plt.subplots()
    ## Get the x axis in terms of datasets analyzed. 
    ind = np.arange(20000)

    plt.axhline(y = tco,linestyle = '--',color = 'red',label = 'base cost (Tesla K80)')
    #plt.axhline(y = tco+298+74+125,linestyle = '--',color = 'blue',label = 'tco estimate')
    ## Get the cost for the dataset: 
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics() for job in metricobjects]
    totalcost = [np.sum(costmetric) for costmetric in costmetrics]
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]
    ## Normed cost per unit
    normed = np.array(totalcost)/np.array(nb_datasets)
    mean = np.mean(normed)
    std = np.std(normed)
    print(mean,std)
    plt.plot(ind,mean*ind,'black',label = 'NCAP')
    plt.plot(ind,(mean+std)*ind,'black',linestyle ='--')
    plt.plot(ind,(mean-std)*ind,'black',linestyle ='--')
    plt.xlabel('Datasets Analyzed (225 MB, 20 minutes)')
    plt.ylabel('Cost (Dollars)')
    plt.legend()
    plt.title(title)

def plot_cost_TCO_gb(filepaths,tco,title):
    fig,ax = plt.subplots()
    #ind = np.arange(np.round(tco).astype(int)).astype(float)
    ind = np.arange(70000)
    plt.axhline(y = tco,linestyle = '--',color = 'red',label = 'base cost (Mac Pro 15 inches)')
    plt.axhline(y = tco+298+74+125,linestyle = '--',color = 'blue',label = 'TCO estimate')
    ## Get the cost for the dataset: 
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics() for job in metricobjects]
    totalcost = [np.sum(costmetric) for costmetric in costmetrics]
    gb_datasets= [sum(job.dict['DatasetSizes']) for job in metricobjects]
    print(gb_datasets)
    ## Normed cost per unit
    normed = np.array(totalcost)/np.array(gb_datasets)
    mean = np.mean(normed)
    std = np.std(normed)
    print(mean,std)
    plt.plot(ind,mean*ind,'black',label = 'NCAP')
    plt.plot(ind,(mean+std)*ind,'black',linestyle ='--')
    plt.plot(ind,(mean-std)*ind,'black',linestyle ='--')
    plt.xlabel('GB Analyzed')
    plt.ylabel('Cost (Dollars)')
    plt.legend()
    plt.title(title)






