import os 
import re
import json 
import traceback 

try:
    ## Works when running in lambda:
    from utilsparam import s3 as utilsparams3
    from utilsparam import ssm as utilsparamssm
    from utilsparam import ec2 as utilsparamec2
    from utilsparam import events as utilsparamevents
    from utilsparam import pricing as utilsparampricing
except Exception as e:
    try:
        ## Most likely this comes from pytest and relative imports. 
        from ncap_iac.protocols.utilsparam import s3 as utilsparams3
        from ncap_iac.protocols.utilsparam import ssm as utilsparamssm
        from ncap_iac.protocols.utilsparam import ec2 as utilsparamec2
        from ncap_iac.protocols.utilsparam import events as utilsparamevents
        from ncap_iac.protocols.utilsparam import pricing as utilsparampricing
    except Exception as e_supp:
        error = str(e)+str(e_supp)
        stacktrace = json.dumps(traceback.format_exc())
        message = "Exception: " + error + "  Stacktrace: " + stacktrace
        err = {"message": message}
        print(err)



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
    time = event['time']
    instanceid = event['detail']['instance-id']
    logname = "{}.json".format(instanceid)
    statechange = event['detail']['state']
    bucket_name = os.environ["BUCKET_NAME"]
    
    if statechange in ["running","shutting-down"]:
        print(logname)
        print(utilsparams3.ls_name(bucket_name,"logs/active/"))
        log = utilsparams3.update_monitorlog(bucket_name,logname,statechange,time) 
        path_to_data = log["datapath"]
        groupname = re.findall('.+?(?=/'+os.environ["INDIR"]+')',path_to_data)[0]
        print(groupname,"groupname")
        ## Log name for the group that make this job: 
        current_job_log = os.path.join("logs","active",logname)
        completed_job_log =  os.path.join("logs",groupname,logname)
        if statechange == "shutting-down":
            utilsparams3.mv(bucket_name,current_job_log,completed_job_log)
    else:
        print("unhandled state change. quitting")
        raise ValueError("statechange {} not expected".format(statechange))


