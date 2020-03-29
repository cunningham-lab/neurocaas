import os 
import json 
import traceback 
import utils.s3
#from utils import s3 as utilss3

## Function to take output of cloudwatch events and write to figure file. 



## Strip the event of relevant information.  
def eventshandler(event,context):
    ## Get the event time, and details. These are the only ones we care about.  
    ## We will write per-instance-id logs.
    time = event['time']
    instanceid = event['detail']['instance-id']
    statechange = event['detail']['state']
    ## We have a unique write object for each instance: 
    bucket_name = 'ncapctnfigurelogs'
    path = 'state'
    ## Write this to a logger object: 
    writer = utils.s3.WriteMetric(bucket_name,path,instanceid,time)
    writer.append('State: '+statechange)
    writer.write()
    
    

## 
def monitor_updater(event,context):
    """
    Newest version of events monitoring that updates pre-existing logs. 

    """
    ## 1. First, find the instance id. 
    ## 2. Go find the appropriate log folder in the bucket [bucket available through os. ]
    ## 3. Now figure out if this is an "running" or "shutting-down" statechange. "
    ## 4. accordingly, either update the log [running] or update the log and move it to the appropriate folder [given by the log contents.]
    ## Include exception handling for the case where one of the fields is not completed. 

