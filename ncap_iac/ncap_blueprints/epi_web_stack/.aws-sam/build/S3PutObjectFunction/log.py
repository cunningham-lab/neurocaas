import os 
import re
import json 
import traceback 
import time as timepkg

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
        error = "error from original import: {}; error from second import: {}".format(str(e),str(e_supp))
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
    try: 
        print(event)
        print(context)
        time = event['time']
        instanceid = event['detail']['instance-id']
        logname = "{}.json".format(instanceid)
        statechange = event['detail']['state']
        bucket_name = os.environ["BUCKET_NAME"]
        
        if statechange in ["running","shutting-down"]:
            log = utilsparams3.update_monitorlog(bucket_name,logname,statechange,time) 
            if type(log["datapath"]) is str:
                path_to_data = log["datapath"]
            elif type(log["datapath"]) is list:
                assert type(log["datapath"][0]) == str
                path_to_data = log["datapath"][0]
            else:
                print("datapath type unsupported, exiting.")
            jobname = os.path.basename(log["jobpath"]).replace(":","_") ## Monitoring names cannot have 

            print(path_to_data,"path_to_data")
            groupname = re.findall('.+?(?=/'+os.environ["INDIR"]+')',path_to_data)[0]
            ## Log name for the group that make this job: 
            current_job_log = os.path.join("logs","active",logname)
            completed_job_log =  os.path.join("logs",groupname,logname)
            if statechange == "shutting-down":
                utilsparams3.mv(bucket_name,current_job_log,completed_job_log)
                timepkg.sleep(5)
                ## Now check if we can delete this rule:
                rulename = "Monitor{}".format(jobname)
                instances_under_rule = utilsparamevents.get_monitored_instances(rulename) 
                condition = [utilsparams3.exists(bucket_name,os.path.join("logs","active","{}.json".format(inst))) for inst in instances_under_rule]
                ## Delete the rule
                if not any(condition):
                    ## get the target:
                    response = utilsparamevents.full_delete_rule(rulename)
                    
                else:
                    pass

        else:
            print("unhandled state change. quitting")
            raise ValueError("statechange {} not expected".format(statechange))
        exitcode = 0 
    except Exception as e:
        print("error: {}".format(e))
        exitcode = 99 
    return exitcode
        


