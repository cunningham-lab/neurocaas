import os 
import json 
import traceback 
import utils.s3

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
    
    


