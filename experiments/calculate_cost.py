import datetime
import os 
import numpy as np
import pandas as pd
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
        maxdiff =max(abs(np.array(all_ends)-np.array(all_starts))).total_seconds()
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
        elif self.dict['InstanceType'] == 'p3.2xlarge':
            costpersec = 3.06/(3600)
        else:
            raise NotImplementedError("Other option {} not implemented.".format(self.dict['InstanceType']))

        self.costrate = costpersec
        self.computecostper = np.array(self.computediffs)*self.costrate
        self.computecost = np.sum(self.computecostper)
        
    ## This is slightly more involved than the baseline calculation. We need the spot instance costs for one and six hours to estimate the actual cost 
    def get_computecost_spotduration(self,spot1,spot6):
        #interpolate an hourly rate: 
        diff = spot6-spot1
        rate = diff/6.
        ## Now get a upper bound on the number of hours 
        maxdiff_hrs = np.ceil(np.max(self.computediffs)/(3600))
        baseprice = (maxdiff_hrs-1)*rate+spot1
        costpersec = baseprice/(3600)
        self.costrate = costpersec
        self.computecostper_spotduration = np.array(self.computediffs)*self.costrate
        self.computecost_spotduration = np.sum(self.computecostper_spotduration)

    def get_computecost_spot(self,spotprice):
        #0.0000166667interpolate an hourly rate: 
        costpersec = spotprice/(3600)
        self.costrate = costpersec
        self.computecostper_spot = np.array(self.computediffs)*self.costrate
        self.computecost_spot = np.sum(self.computecostper_spot)

    ## Get lambda cost:
    def get_lambdacost(self):
        ## times in seconds
        times = np.array(self.dict['LambdaComputeTimes'])/1000.
        ## size in GB
        size = self.dict['LambdaMemory']/1000.
        ## Cost per GBseconds
        self.lambdacostper = times*size*0.000016667
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

    ## Calculate also with defined duration spot instance prices. 
    def get_costmetrics_spotduration(self,spot1,spot6):
        self.get_computecost_spotduration(spot1,spot6)
        self.get_lambdacost()
        self.get_transfercost()
        return [self.computecost_spotduration,self.lambdacost,self.transfercost]

    ## Calculate also with defined duration spot instance prices. 
    def get_costmetrics_spot(self,spot):
        self.get_computecost_spot(spot)
        self.get_lambdacost()
        self.get_transfercost()
        return [self.computecost_spot,self.lambdacost,self.transfercost]

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

## Plot cost as bar plots,comparing duration spot with nonduration spot
def plot_costbar_spot(filepaths,xlabels,title,spot,spot1,spot6):
    """
    Parameters:

    filepaths: a list of filepaths in order that you would like the bars to be in. 
    xlabels: a list of the xlabels to use: 
    """
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics_spotduration(spot1,spot6) for job in metricobjects]
    costmetrics_spot = [job.get_costmetrics_spot(spot) for job in metricobjects]
    computecost,lambdacost,transfercost = zip(*costmetrics)
    computecost_s,lambdacost_s,transfercost_s = zip(*costmetrics_spot)
    ## Mock local processing
    nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]

    ind = np.arange(len(xlabels))
    width = 0.10
    offset = 0.12
    fig,ax = plt.subplots(figsize = (36,16))
    ## Plot the actual
    plt.bar(ind-offset,computecost,label = 'compute',width = width,color = 'blue')
    plt.bar(ind-offset,lambdacost,bottom = computecost,label = 'management',width = width,color = 'orange')
    plt.bar(ind-offset,transfercost,bottom = np.array(computecost)+np.array(lambdacost),label = 'transfer',width = width,color = 'red')
    ## Plot the local 
    plt.bar(ind+offset,computecost_s,label = 'compute',width = width,color = 'blue')
    plt.bar(ind+offset,lambdacost,bottom = computecost_s,label = 'management',width = width,color = 'orange')
    plt.bar(ind+offset,transfercost,bottom = np.array(computecost_s)+np.array(lambdacost),label = 'transfer',width = width,color = 'red')
    ## Plot the local
    #plt.bar(ind12*wid'upload',color = 'blue')
    #plt.bar(ind-offset,np.array(computetimes)*np.array(nb_datasets),width=width,color = 'red')
    
    ## Plot ticks: 
    #ax.set_xticks(ind)
    #ax.set_xticklabels([xlabels[0]+' (NCAP)',xlabels[1]+' (NCAP)',xlabels[2]+' (NCAP)'],fontsize = 38)
    offset_inds = np.stack([ind-offset,ind+offset],axis = 1).flatten()
    ax.set_xticks(offset_inds)
    ax.set_xticklabels([xlabels[0]+' (Std)',xlabels[0]+" (Save)",xlabels[1]+' (Std)',xlabels[1]+" (Save)",xlabels[2]+' (Std)',xlabels[2]+" (Save)"],rotation = 25,ha = 'right')
    ax.set_title(title,fontsize = 54)
    ax.set_ylabel('Cost (dollars)',fontsize = 38)
    ax.set_xlabel('Dataset Size',fontsize = 38)
    plt.legend(fontsize = 38)
    plt.setp(ax.get_xticklabels(), fontsize=38)
    plt.setp(ax.get_yticklabels(), fontsize=38)
    plt.tight_layout()
    plt.savefig('../Figures/'+title+'.png')
    plt.show()

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
def plot_TCO_xover_multiple_spotduration(filepaths,hardware,spot1,spot6,title,labels,xaxis = [None,None,None]):
    fig,ax = plt.subplots(figsize = (12,14))
    #labels = ['8 GB','36 GB','79 GB']
    for fi,filepath in enumerate(filepaths):
        plot_TCO_xover_spotduration(filepath,hardware,spot1,spot6,None,axes = (fig,ax),label = labels[fi],xaxis = xaxis[fi])
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

def plot_TCO_xover_multiple_spot(filepaths,hardware,spot,title,labels,xaxis = [None,None,None]):
    fig,ax = plt.subplots(figsize = (12,14))
    #labels = ['8 GB','36 GB','79 GB']
    for fi,filepath in enumerate(filepaths):
        plot_TCO_xover_spot(filepath,hardware,spot,axes = (fig,ax),label = labels[fi],xaxis = xaxis[fi])
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
    
def plot_TCO_xover_spot(filepath,hardware,spot,title=None,axes = False,label = None,xaxis =None):
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
    price_ncap = np.sum(metricobj.get_costmetrics_spot(spot))
    price_ncap_store = (np.sum(metricobj.get_costmetrics_spot(spot))+0.0125)
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
        plt.title(title)
        #plt.title('Crossover point as a function of Data Analysis Rate: Caiman, 72 GB')
        plt.ylabel('Weeks')
        plt.xlabel('Datasets Analyzed Per Week')

def plot_TCO_xover_spotduration(filepath,hardware,spot1,spot6,title= None,axes = False,label = None,xaxis =None):
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
    price_ncap = np.sum(metricobj.get_costmetrics_spotduration(spot1,spot6))
    price_ncap_store = (np.sum(metricobj.get_costmetrics_spotduration(spot1,spot6))+0.0125)
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
        plt.title(title)
        #plt.title('Crossover point as a function of Data Analysis Rate: Caiman, 72 GB')
        plt.ylabel('Weeks')
        plt.xlabel('Datasets Analyzed Per Week')

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

################################################################################################################################################################ 
## Edits on September 10th to output tab separated text file readable from adobe illustrator as a table. 
def plot_cost_bar_data(filepaths,xlabels,legend,filename):
    """
    filepaths:(list) A list of strings giving the experiments we want to analyze in tandem. 
    xlabels:(list) A list of strings giving the x labels of the bar plot groups  
    legend:(list) A list of strings giving the legends for the bar plot groups 
    filename:(string) A string giving the name of the text file we should be saving our results to.   
    """
    ## Spot instance cost sampling: 
    CNMFspot1 = 1.536
    CNMFspot6 = 1.996
    CNMFspot = 0.6385
    DLCspot1 = 0.45 
    DLCspot6 = 0.585
    DLCspot = 0.2764
    Locaspot1 = 1.683 
    Locaspot6 = 2.142 
    Locaspot = 0.918 

    CNMF_costs = [CNMFspot,CNMFspot1,CNMFspot6]
    DLC_costs = [DLCspot,DLCspot1,DLCspot6]
    Loca_costs = [Locaspot,Locaspot1,Locaspot6]
    processing = os.path.dirname(filepaths[0])
    if processing == "DLC":
        costs = DLC_costs
    elif processing in ("CaImAn","PMD"):
        costs = CNMF_costs
    elif processing == "LocaNMF":
        costs = Loca_costs
        
    metricobjects = [JobMetrics(path) for path in filepaths]
    costmetrics = [job.get_costmetrics_spotduration(costs[1],costs[2]) for job in metricobjects]
    costmetrics_save = [job.get_costmetrics_spot(costs[0]) for job in metricobjects]
    totalcost = [np.sum(costmetric) for costmetric in costmetrics]
    totalcost_save = [np.sum(costmetric) for costmetric in costmetrics_save]
    ## Now we want to format this as rows and columns 
    transposed = list(zip(totalcost,totalcost_save))
    ## Now append the x labels to each row: 
    fulldata = [["xlabel"]+legend]
    for i in range(len(xlabels)):
       fullrow = [xlabels[i]]+list(transposed[i]) 
       fulldata.append(fullrow)
    ## Now write this to a text file: 
    with open(filename,'w') as f: 
        for row in fulldata:
            for e,entry in enumerate(row):
                if e != len(row)-1:
                    f.write(str(entry)+'\t')
                else:
                    f.write(str(entry))
            f.write('\n')
    

## Edits on September 10th to output tab separated text file readable from adobe illustrator as a table 
def plot_time_bar_data(filepaths,xlabels,legend,breakout,filename):
    """
    filepaths:(list) A list of strings giving the experiments we want to analyze in tandem. 
    xlabels:(list) A list of strings giving the experimental dataset condition  
    legend:(list) A list of strings giving the tested method 
    breakout:(list) A list of the different time periods accounted for in processing. 
    filename:(string) A string giving the name of the text file we should be saving our results to.   
    """
    ## Plotting Parameters: 
    metricobjects = [JobMetrics(path) for path in filepaths]
    timemetrics = [job.get_timemetrics() for job in metricobjects]
    totaltime = [np.sum(timemetric) for timemetric in timemetrics]
    ## Cartesian product the x labels and legends to get the labels: 
    plexlabels = [lab+' '+leg for lab in xlabels for leg in legend]

    #
    processing = os.path.dirname(filepaths[0])
    if processing == 'DLC':
        ## Infer the compute times: 
        nb_datasets= [len(job.dict['LambdaComputeTimes']) for job in metricobjects]
        computetimes_local = [tm[1]*nb_datasets[t] for t,tm in enumerate(timemetrics)]
        ## Generate a stacked list
        all_entries = []
        for i,c in enumerate(computetimes_local):
            init = [0]
            init.append(c) 
            all_entries.append(init)
            all_entries.append(timemetrics[i])
        
    elif processing in ('CaImAn','PMD','LocaNMF'):
        ## Get manual data: 
        manual = os.path.join(processing,'Manual_Data.json')
        with open(manual,'r') as f:
           manual_records = json.load(f)
        all_processing = manual_records['ProcessingTime']
        manualtimes = [all_processing[xlabel] for xlabel in xlabels]
        ## Generate a stacked list
        all_entries = []
        for i,c in enumerate(manualtimes):
            init = [0]
            init.append(c)
            all_entries.append(init)
            all_entries.append(timemetrics[i])
    else:
        raise NotImplementedError("Not implemented for this case.")
     
    ## Now we will write this to a text file separated by tabs.  
    ## Now append the x labels to each row: 
    fulldata = [["xlabel"]+breakout]
    for i in range(len(plexlabels)):
       fullrow = [plexlabels[i]]+all_entries[i] 
       fulldata.append(fullrow)

    ## Now write this to a text file: 
    with open(filename,'w') as f: 
        for row in fulldata:
            for e,entry in enumerate(row):
                if e != len(row)-1:
                    f.write(str(entry)+'\t')
                else:
                    f.write(str(entry))
            f.write('\n')

## Define functions that plot the final graphs for us. This is separated from the actual data generation, which is done above.  
## Define a function that plots given a pipeline name: 
def plot_cost(pipeline,compute =True):
    """
    Inputs: 
    pipeline:(string) the name of the pipeline we are analyzing
    compute:(boolean) the boolean giving whether we should re-compute tables or not. 
    """
    figure_size = (21,27)
    title_size = 80 
    xlabel_size = 80
    ylabel_size = 90 
    yticklabel_size = 90 

    if pipeline == "CaImAn":
        filenames = ['batchN.02.00_2.json','batchJ123_2.json','batchJ115_2.json']
        #xlabels = ['8 GB','36 GB','79 GB']
        xlabels = ['8.39 x 1','35.8 x 1','78.7 x 1']
        ylabels = [0,0.5,1,1.5,2]
    elif pipeline == 'DLC':
        filenames = ['batch_5.json','batch_10.json','batch_15.json']
        #xlabels = ['1 hr','2 hrs','3 hrs']
        xlabels = ['0.22 x 5', '0.22 x 10','0.22 x 15']
        ylabels = [0,0.5,1,1.5,2]
    elif pipeline == "PMDLocaNMF":
        filenames = ['batch_1.json','batch_3.json','batch_5.json']
        #xlabels = ['1 vid','3 vids','5 vids']
        xlabels = ['20.1 x 1','20.1 x 3', '20.1 x 5']
        ylabels = [0,1.5,3,4.5,6]
        #ylabels = [0,2,4,6,8,13]
        #ylabels = [0,0.5,1,1.5,2]
    else:
        raise NotImplementedError("This option does not exist yet.")

    legend = ['NCAP','NCAP Save']
    ## Save to a file because it's easy. 
    tablename = os.path.join(pipeline,pipeline+'costlog.txt')
    ## Compute if we are supposed to:
    if compute == True:
        paths = [os.path.join(pipeline,filename) for filename in filenames]
        plot_cost_bar_data(paths,xlabels,legend,tablename)

    ## Load in the data:  
    df = pd.read_csv(tablename,sep = '\t',index_col = 0)

    ## Now we will plot by xlabel and then by condition.  
    xpositions = [1,8,15]
    offset = [-1.5,1.5]
    width = 2.2

    ## Load in colorbrewer colors: 
    ## Colorbrewer YlGnBu, interleaved dark and light pale
    colors = ['#41b6c4','#ffffcc','#2c7fb8','#c7e9b4','#253494','#7fcdbb']
    colors = ['#253494','#7fcdbb']

    fig,ax = plt.subplots(figsize = figure_size)
    #ax = fig.add_axes([0.1, 0.1, 5, 4])

    ## legend
    plotlegend = ['Std','Save']
    for xi,xl in enumerate(xlabels):
        for li,leg in enumerate(legend): 
            datapoint = df.loc[xl][leg]
            if xi == 0:
                ax.bar(xpositions[xi]+offset[li],datapoint,width = width,color = colors[li],label = plotlegend[li])
            else:
                ax.bar(xpositions[xi]+offset[li],datapoint,width = width,color = colors[li])
    ax.set_xticks([xp+os*1.1 for xp in xpositions for os in offset])
    for spine in ax.spines.values():
        spine.set_visible(False)
    dellegend = [""]
    #ax.set_xticklabels([plotlegend[i%2] for i in range(len(xlabels)*len(legend))],size = 50,rotation = 30)
    ax.set_xticklabels([dellegend[0] for i in range(len(xlabels)*len(legend))],size = 50,rotation = 30)
    ## We're going to do some axis trickery so we need the limits: 
    xlims = plt.xlim()
    l, b, w, h = ax.get_position().bounds
    ax.set_position([l+0.05,b+0.1,w,h])

    ## Add a secondary axis for dataset size labels: 
    newax = fig.add_axes(ax.get_position())
    newax.set_xlim(xlims)
    newax.set_xticks([xp for xp in xpositions])
    newax.patch.set_visible(False)
    newax.yaxis.set_visible(False)
    newax.spines['bottom'].set_position(('outward',55))
    newax.set_xlabel("Dataset Size (GB x batch size)",size = xlabel_size)
    for spine in newax.spines.values():
        spine.set_visible(False)

    newax.set_xticklabels([xlabel for xlabel in xlabels],size = xlabel_size)
    ## Now we will set ylabels
    ax.set_yticks(np.array(ylabels))
    ax.set_yticklabels(ylabels,size = yticklabel_size)
    ax.set_ylabel('Cost (Dollars)',size = ylabel_size)
    #ax.set_aspect(2.5)
    #ax.set_title('NCAP Cost vs. Dataset Size',size = title_size,pad = 10.0)

    ## Only plot the legend if CaImAn
    if pipeline == "CaImAn":
        ax.legend(prop = {'size': 80},loc = 0)
    else: 
        pass
    plt.savefig(os.path.join(pipeline,pipeline+'AnalysisCost.png'))


    return df

def plot_time(pipeline,compute= True):
    """
    Inputs: 
    pipeline:(string) the name of the pipeline we are analyzing
    """
    ## Figure size parameters. 
    figure_size = (21,27)
    title_size = 80 
    xlabel_size = 80
    ylabel_size = 90 
    yticklabel_size = 90 
    if pipeline == "CaImAn":
        filenames = ['batchN.02.00_2.json','batchJ123_2.json','batchJ115_2.json']
        xlabels = ['8.39 x 1','35.8 x 1','78.7 x 1']
        timeint = 1600
    elif pipeline == 'DLC':
        filenames = ['batch_5.json','batch_10.json','batch_15.json']
        xlabels = ['0.22 x 5', '0.22 x 10','0.22 x 15']
        timeint = 2400
    elif pipeline == "PMDLocaNMF":
        filenames = ['batch_1.json','batch_3.json','batch_5.json']
        xlabels = ['20.1 x 1','20.1 x 3', '20.1 x 5']
        timeint = 2800 
    else:
        raise NotImplementedError("This option does not exist yet.")
    legend = ['Local','NCAP']
    breakout = ['Upload','Compute']
    ## Save to a file because it's easy. 
    tablename = os.path.join(pipeline,pipeline+'timelog.txt')
    if compute == True:
        print("updated")
        paths = [os.path.join(pipeline,filename) for filename in filenames]
        plot_time_bar_data(paths,xlabels,legend,breakout,tablename)
    ## Load in the data:  
    df = pd.read_csv(tablename,sep = '\t',index_col = 0)
    
    ## Now we will plot by xlabel and then by condition.  
    xpositions = [1,8,15]
    offset = [-1.5,1.5]
    width = 2.2

    ## Load in colorbrewer colors: 
    ## Colorbrewer YlGnBu, interleaved dark and light pale
    colors = ['#41b6c4','#ffffcc','#2c7fb8','#c7e9b4','#253494','#7fcdbb']
    colors = ['#fc8d59','#fc8d59','#ffffbf','#91cf60']

    fig,ax = plt.subplots(figsize = figure_size)
    for xi,xl in enumerate(xlabels):
        for li,leg in enumerate(legend): 
            for bi,br in enumerate(breakout):
                datapoint = df.loc[xl+' '+leg][br]
                print(li+2*bi)
                if bi == 0:
                    base = datapoint
                    if xi == 0 and bi+li >= 1:
                        ax.bar(xpositions[xi]+offset[li],datapoint,width = width,color = colors[2*li+bi],label = leg+'\n'+"({})".format(br))
                    else:
                        ax.bar(xpositions[xi]+offset[li],datapoint,width = width,color = colors[2*li+bi])
                if bi == 1:
                    if xi == 0:
                        if li == 0:
                            ax.bar(xpositions[xi]+offset[li],datapoint,width = width,bottom = base,color = colors[2*li+bi],label = leg)
                        if li == 1:
                            ax.bar(xpositions[xi]+offset[li],datapoint,width = width,bottom = base,color = colors[2*li+bi],label = leg+'\n'+"({})".format(br))
                    else: 
                        ax.bar(xpositions[xi]+offset[li],datapoint,width = width,bottom = base,color = colors[2*li+bi])
    ax.set_xticks([xp+os for xp in xpositions for os in offset])
    for spine in ax.spines.values():
        spine.set_visible(False)
    dellegend = [""]
    #ax.set_xticklabels([legend[i%2] for i in range(len(xlabels)*len(legend))],size = 50,rotation = 20)
    ax.set_xticklabels([dellegend[0] for i in range(len(xlabels)*len(legend))],size = 50,rotation = 20)
    ## We're going to do some axis trickery so we need the limits: 
    xlims = plt.xlim()
    l, b, w, h = ax.get_position().bounds
    ax.set_position([l+0.05,b+0.1,w,h])

    ## Add a secondary axis for dataset size labels: 
    newax = fig.add_axes(ax.get_position())
    newax.set_xlim(xlims)
    newax.set_xticks([xp for xp in xpositions])
    newax.patch.set_visible(False)
    newax.yaxis.set_visible(False)
    newax.spines['bottom'].set_position(('outward',55))
    newax.set_xlabel("Dataset Size (GB x batch size)",size = xlabel_size)
    for spine in newax.spines.values():
        spine.set_visible(False)

    newax.set_xticklabels([xlabel for xlabel in xlabels],size = xlabel_size)
    ## Now we will set ylabels
    #ax.set_yticks([0,0.5,1,1.5,2])
    ytick_secs = np.array([timeint*i for i in range(0,10,2)])
    hours = np.array([np.round(yi,1) for yi in ytick_secs/3600])
    sec_round = [h*3600 for h in hours]
     
    ax.set_yticks(sec_round)
    ax.set_yticklabels(hours,size = yticklabel_size)

    ax.set_ylabel('Time (Hours)',size = ylabel_size)
    #ax.set_title('Analysis Time vs. Dataset Size',size = title_size,pad = 10.0)
    if pipeline == "CaImAn":
        ax.legend(prop = {'size': 76},loc = 'upper left')
    else:
        pass
    plt.savefig(os.path.join(pipeline,pipeline+'AnalysisTime.png'))
    return df

## Now, more processed metrics 1. A plot that gives the Hardware Cost Crossover.  
def plot_humans(pipeline,pricing = "Orig",compute = True):
    """
    Converts these measures into those that are most meaningful to humans. Uses Wipro whitepaper commissioned by intel in 2010.  
    Inputs: 
    pipeline:(string) the name of the pipeline we are analyzing
    pricing:(string) the pricing to use. Options are Orig, Local, and Cluster.  
    compute:(bool) whether we should recompute the metrics (time and cost).   
    """
    figure_size = (40,13)
    title_size = 95 
    xlabel_size = 50
    ylabel_size = 50
    xticklabel_size = 50 
    yticklabel_size = 50 
    assert pricing in ["Orig","Local","Cluster","Hard"], "input must be one of known quantities" 
    
    if pipeline == "CaImAn":
        filenames = ['batchN.02.00_2.json','batchJ123_2.json','batchJ115_2.json']
        xlabels = ['8.39 x 1','35.8 x 1','78.7 x 1']
        if pricing == "Orig":
            ## Also have a baseline cost for computer: 
            cost = 1599 
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [716,768,824,891+75,969+171]
            maxval = 9 
        if pricing == "Local":
            ## Also have a baseline cost for computer: 
            cost = 1539
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [716,768,824,891+75,969+171]
            maxval = 9 
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 1499+1000 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [225+4+135]*5
            maxval = 12 
        if pricing == "Hard":
            ## Also have a baseline cost for computer: 
            cost = 1539
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [0]*5
            maxval = 9 
    elif pipeline == 'DLC':
        filenames = ['batch_5.json','batch_10.json','batch_15.json']
        xlabels = ['0.22 x 5', '0.22 x 10','0.22 x 15']
        if pricing == "Orig":
            ## Baseline cost for computer + gpu
            cost = 700+5000
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [433,465,499,539+26,585+59]
            maxval = 5
        if pricing == "Local":
            cost = 1489+1680# 700+5000
            support = [433,465,499,539+26,585+59]
            maxval = 3
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 1701+400+1680 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [255+2+135]*5
            maxval = 3 
        if pricing == "Hard":
            cost = 1489+1680# 700+5000
            support = [0]*5
            maxval = 3
    elif pipeline == "PMDLocaNMF":
        filenames = ['batch_1.json','batch_3.json','batch_5.json']
        xlabels = ['20.1 x 1','20.1 x 3', '20.1 x 5']
        if pricing == "Orig":
            #benchmark desktop: https://www.newegg.com/p/1VK-01UA-000U4 for the PMD processing.  
            #add in a K80 GPU:
            cost = 3199+5000 
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [433,465,499,539+26,585+59]
            maxval = 4
        if pricing == "Local":
            cost = 3979+1680 
            support = [433,465,499,539+26,585+59]
            maxval = 4 
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 10836+150+1680 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [1625+1+135]*5
            maxval = 9 
        if pricing == "Hard":
            cost = 3979+1680 
            support = [0]*5
            maxval = 3 
    else:
        raise NotImplementedError("This option does not exist yet.")
    paths = [os.path.join(pipeline,filename) for filename in filenames]
    ## Additional information w.r.t. plotting:
    costlegend = ['NCAP','NCAP Save']
    breakout = ['Upload','Compute']
    timelegend = ['Local','NCAP']
    ## Save to a file because it's easy. 
    costfilename = os.path.join(pipeline,pipeline+'costlog.txt')
    timefilename = os.path.join(pipeline,pipeline+'timelog.txt')
    if compute == True:
        plot_cost_bar_data(paths,xlabels,costlegend,costfilename)
        plot_time_bar_data(paths,xlabels,timelegend,breakout,timefilename)
    ## Load in the data:  
    cost_df = pd.read_csv(costfilename,sep = '\t',index_col = 0)
    time_df = pd.read_csv(timefilename,sep = '\t',index_col = 0)

    ## We want to benchmark at 1,3,5 years: 
    r = 0.1
    annuity_rate = lambda n: (1-(1+r)**(-n))/r

    ## Get the total amount   
    annual_cost = cost/np.array([annuity_rate(ni+1) for ni in range(5)])+np.array(support)
 
    ## Now take the cost dataframe and divide by the annual cost (?)
    tco_cost = annual_cost*(np.arange(5)+1)
    tco_weekly_tiled = np.tile(annual_cost/52.,len(costlegend)*len(xlabels)).reshape(len(costlegend),len(xlabels),5)
    ## Take the weekly cost according to tco and divide by dataset price: 
    crossover = tco_weekly_tiled.T/cost_df.values

    print(crossover[0,:,:])
    print(crossover[0,1,:])
    ## Now we will plot by xlabel and then by condition.  
    ypositions = [21,11,1]
    offset = [1.9,-1.9]
    offset_cost = [0.9,-0.9]
    height = 1.7 

    ## Load in colorbrewer colors: 
    ## Colorbrewer YlGnBu, interleaved dark and light pale
    colors = ['#41b6c4','#ffffcc','#2c7fb8','#c7e9b4','#253494','#7fcdbb']
    ## Colorbrewer PuBuGn, YlGuBn (backwards), YlOrRd
    colors = [
             [['#f6eff7','#67a9cf'],['#d0d1e6','#1c9099'],['#a6bddb','#016c59']],
             [['#253494','#7fcdbb'],['#2c7fb8','#c7e9b4'],['#41b6c4','#ffffcc']],
             [['#ffffd4','#fe9929'],['#fee391','#d95f0e'],['#fec44f','#993404']],
             ] 
    colors = [["#b35806","#542788"],["#f1a340","#998ec3"],["#fee0b6","#d8daeb"]]
    colors = [["#f1a340","#998ec3"],["#fee0b6","#d8daeb"]]

    fig,ax = plt.subplots(figsize = figure_size)
    years_to_use = [2,4]
    years = ['Realistic','Optimistic']
    for yi,yr in enumerate(years_to_use):
        for xi,xl in enumerate(xlabels):
            for li,leg in enumerate(costlegend): 
                if xi == 1:
                    datapoint = crossover[yi,xi,li]
                    ax.barh(ypositions[xi]+offset[yi]+offset_cost[li],width = datapoint,height = height,color = colors[yi][li],label =years[yi]+ ' (vs. '+costlegend[li]+')')
                else:
                    datapoint = crossover[yi,xi,li]
                    ax.barh(ypositions[xi]+offset[yi]+offset_cost[li],width = datapoint,height = height,color = colors[yi][li])
    ax.set_yticks([yp+os+1.9 for yp in ypositions for os in offset])
    for spine in ax.spines.values():
        spine.set_visible(False)
    #ax.set_yticklabels([years[i%len(years_to_use)] for i in range(len(xlabels)*len(costlegend)*3)],size = 30,rotation = 50,ha = 'right')
    ax.set_yticklabels(["" for i in range(len(xlabels)*len(costlegend)*3)],size = yticklabel_size,rotation = 80,ha = 'right')
    ## We're going to do some axis trickery so we need the limits: 
    ylims = plt.ylim()
    l, b, w, h = ax.get_position().bounds
    ax.set_position([l+0.05,b,w,h])

    ## Add a secondary axis for dataset size labels: 
    newax = fig.add_axes(ax.get_position())
    newax.set_ylim(ylims)
    newax.set_yticks([yp for yp in ypositions])
    newax.patch.set_visible(False)
    newax.xaxis.set_visible(False)
    newax.spines['left'].set_position(('outward',25))
    newax.set_ylabel("Dataset Size (GB x batch size)",size = ylabel_size)
    for spine in newax.spines.values():
        spine.set_visible(False)
    

    ## Now we will set ylabels
    newax.set_yticklabels([xlabel for xlabel in xlabels],size = yticklabel_size)
    weeks = [50*zi for zi in np.arange(0,maxval+1,np.round((maxval+1)/5).astype('int'))]
    ax.set_xticks(weeks)
    ax.set_xticklabels(weeks,size = xticklabel_size)
    ax.set_xlabel('Datasets per Week',size = xlabel_size)

    lower = [0.755,0.400,0.045]

    if pipeline == "CaImAn":
        legend = ax.legend(prop = {'size': 52},title = 'Hardware Lifetime',loc = "lower right")
        legend.get_title().set_fontsize('50')
    else:
        pass


    if pricing == "Orig":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisTotal.png'))
    if pricing == "Local":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisTotal_alt.png'))
    if pricing == "Cluster":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisTotal_cluster.png'))
    if pricing == "Hard":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisTotal_hard.png'))
    ## Calculate the max number of datasets that can be analyzed per size: 
    print(time_df)
    for xl in xlabels:
        local_compute = time_df.loc[xl+' '+'Local']['Compute']
        ## Number of seconds in a week is: 
        weeksec = 60*60*24*7

        print(local_compute,weeksec, weeksec/local_compute)



    return cost_df,tco_cost

## Now get the utilization necessary in order to actually *meet* this crossover.
def plot_utilization(pipeline,pricing = "Orig"):
    """
    Converts these measures into those that are most meaningful to humans. Uses Wipro whitepaper commissioned by intel in 2010.  
    Inputs: 
    pipeline:(string) the name of the pipeline we are analyzing
    """
    figure_size = (40,13)
    title_size = 95 
    xlabel_size = 50
    ylabel_size = 50
    xticklabel_size = 50 
    yticklabel_size = 50 
    assert pricing in ["Orig","Local","Cluster","Hard"], "input must be one of known quantities" 
    if pipeline == "CaImAn":
        filenames = ['batchN.02.00_2.json','batchJ123_2.json','batchJ115_2.json']
        xlabels = ['8.39 x 1','35.8 x 1','78.7 x 1']
        if pricing == "Orig":
            ## Also have a baseline cost for computer: 
            cost = 1599 
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [716,768,824,891+75,969+171]
            maxval = 200 
        if pricing == "Local":
            ## Also have a baseline cost for computer: 
            cost = 1539
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [716,768,824,891+75,969+171]
            maxval = 200 
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 1499+1000 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [225+4+135]*5
            maxval = 200 
        if pricing == "Hard":
            ## Also have a baseline cost for computer: 
            cost = 1539
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [0]*5
            ## maximum utilization percentage
            maxval = 150 
    elif pipeline == 'DLC':
        filenames = ['batch_5.json','batch_10.json','batch_15.json']
        xlabels = ['0.22 x 5', '0.22 x 10','0.22 x 15']
        if pricing == "Orig":
            ## Baseline cost for computer + gpu
            cost = 700+5000
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [433,465,499,539+26,585+59]
            maxval = 300 
        if pricing == "Local":
            cost = 1489+1680# 700+5000
            support = [433,465,499,539+26,585+59]
            ## maximum utilization percentage
            maxval = 200
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 1701+400+1680 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [255+2+135]*5
            maxval = 200
        if pricing == "Hard":
            cost = 1489+1680# 700+5000
            support = [0]*5
            ## maximum utilization percentage
            maxval = 200
    elif pipeline == "PMDLocaNMF":
        filenames = ['batch_1.json','batch_3.json','batch_5.json']
        xlabels = ['20.1 x 1','20.1 x 3', '20.1 x 5']
        if pricing == "Orig":
            #benchmark desktop: https://www.newegg.com/p/1VK-01UA-000U4 for the PMD processing.  
            #add in a K80 GPU:
            cost = 3199+5000 
            ## Factor in support cost per year (from wipro whitepaper [morey & nambiar 2010]): 
            support = [433,465,499,539+26,585+59]
            ## maximum utilization percentage
            maxval = 200
        if pricing == "Local":
            cost = 3979+1680 
            support = [433,465,499,539+26,585+59]
            ## maximum utilization percentage
            maxval =  125
        if pricing == "Cluster":
            ## TCO cost calculator 
            cost = 10836+150+1680 # for hardware + storage  
            ## Factor in support cost per year (from AWS TCO calculator) server maintenance, storage maintenance, : 
            support = [1625+1+135]*5
            maxval = 250
        if pricing == "Hard":
            cost = 3979+1680 
            support = [0]*5
            ## maximum utilization percentage
            maxval =  125
    else:
        raise NotImplementedError("This option does not exist yet.")
    paths = [os.path.join(pipeline,filename) for filename in filenames]
    ## Additional information w.r.t. plotting:
    costlegend = ['NCAP','NCAP Save']
    breakout = ['Upload','Compute']
    timelegend = ['Local','NCAP']
    ## Save to a file because it's easy. 
    costfilename = pipeline+'costlog.txt'
    timefilename = pipeline+'timelog.txt'

    ## Load in the data:  
    cost_df = pd.read_csv(os.path.join(pipeline,costfilename),sep = '\t',index_col = 0)
    time_df = pd.read_csv(os.path.join(pipeline,timefilename),sep = '\t',index_col = 0)

    ## We want to benchmark at 1,3,5 years: 
    r = 0.1
    annuity_rate = lambda n: (1-(1+r)**(-n))/r

    ## Get the total amount   
    annual_cost = cost/np.array([annuity_rate(ni+1) for ni in range(5)])+np.array(support)
 
    ## Now take the cost dataframe and divide by the annual cost (?)
    tco_cost = annual_cost*(np.arange(5)+1)
    tco_weekly_tiled = np.tile(annual_cost/52.,len(costlegend)*len(xlabels)).reshape(len(costlegend),len(xlabels),5)
    ## Take the weekly cost according to tco and divide by dataset price: 
    crossover = tco_weekly_tiled.T/cost_df.values
    ## Get the local timings: 
    compute = time_df["Compute"]
    local_compute = [compute["{} Local".format(x)] for x in xlabels]
    print(local_compute)
    print(time_df)
    ypositions = [21,11,1]
    offset = [1.9,-1.9]
    offset_cost = [0.9,-0.9]
    height = 1.7 

    ## Load in colorbrewer colors: 
    ## Colorbrewer YlGnBu, interleaved dark and light pale
    colors = ['#41b6c4','#ffffcc','#2c7fb8','#c7e9b4','#253494','#7fcdbb']
    ## Colorbrewer PuBuGn, YlGuBn (backwards), YlOrRd
    colors = [
             [['#f6eff7','#67a9cf'],['#d0d1e6','#1c9099'],['#a6bddb','#016c59']],
             [['#253494','#7fcdbb'],['#2c7fb8','#c7e9b4'],['#41b6c4','#ffffcc']],
             [['#ffffd4','#fe9929'],['#fee391','#d95f0e'],['#fec44f','#993404']],
             ] 
    colors = [["#b35806","#542788"],["#f1a340","#998ec3"],["#fee0b6","#d8daeb"]]
    colors = [["#f1a340","#998ec3"],["#fee0b6","#d8daeb"]]

    fig,ax = plt.subplots(figsize = figure_size)
    years_to_use = [2,4]
    years = ['Realistic','Optimistic']

    for yi,yr in enumerate(years_to_use):
        for xi,xl in enumerate(xlabels):
            for li,leg in enumerate(costlegend): 
                spw = 7*24*60*60
                dpw = spw/local_compute[xi]
                if xi == 1:
                    ## first get out the max number that can be done per week: 
                    ## Now divide by the required: 
                    datapoint = crossover[yi,xi,li]/dpw*100
                    ax.barh(ypositions[xi]+offset[yi]+offset_cost[li],width = datapoint,height = height,color = colors[yi][li],label =years[yi]+ ' (vs. '+costlegend[li]+')')
                else:
                    datapoint = crossover[yi,xi,li]/dpw*100
                    ax.barh(ypositions[xi]+offset[yi]+offset_cost[li],width = datapoint,height = height,color = colors[yi][li])
                print(datapoint, "datapoint value")
    ax.set_yticks([yp+os+1.9 for yp in ypositions for os in offset])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_yticklabels(["" for i in range(len(xlabels)*len(costlegend)*3)],size = yticklabel_size,rotation = 50,ha = 'right')
    ## We're going to do some axis trickery so we need the limits: 
    ylims = plt.ylim()
    l, b, w, h = ax.get_position().bounds
    ax.set_position([l+0.05,b,w,h])

    ## Add a secondary axis for dataset size labels: 
    newax = fig.add_axes(ax.get_position())
    newax.set_ylim(ylims)
    newax.set_yticks([yp for yp in ypositions])
    newax.patch.set_visible(False)
    newax.xaxis.set_visible(False)
    newax.spines['left'].set_position(('outward',10))
    newax.set_ylabel("Dataset Size (GB x batch size)",size = ylabel_size)
    for spine in newax.spines.values():
        spine.set_visible(False)
    
    ## Now we will set ylabels
    newax.set_yticklabels([xlabel for xlabel in xlabels],size = yticklabel_size)
    percentage = np.arange(0,maxval*5/4,maxval/4).astype("int")
    ax.set_xticks(percentage)
    ax.set_xticklabels(percentage,size = xticklabel_size)
    ax.set_xlabel('Utilization (%)',size = xlabel_size)
    ax.axvline(x = 100,color = "black",linestyle = "--")

    lower = [0.755,0.400,0.045]

    
    if pricing == "Orig":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisUtilization.png'))
    if pricing == "Local":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisUtilization_alt.png'))
    if pricing == "Cluster":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisUtilization_cluster.png'))
    if pricing == "Hard":
        plt.savefig(os.path.join(pipeline,pipeline+'AnalysisUtilization_hard.png'))

    



    return cost_df,tco_cost
    

    return crossover
