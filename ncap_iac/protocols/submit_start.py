import os
import sys
import json
import traceback
from botocore.exceptions import ClientError
import re
from datetime import datetime

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


def respond(err, res=None):
    return {
        "statusCode": "400" if err else "200",
        "body": err["message"] if err else json.dumps(res),
        "headers": {"Content-Type": "application/json"},
    }

## Lambda code for developmemt. 
class Submission_dev():
    """
    Specific lambda for purposes of development.  
    """
    def __init__(self,bucket_name,key,time):
        ## Initialize as before:
        # Get Upload Location Information
        self.bucket_name = bucket_name
        ## Get directory above the input directory. 
        self.path = re.findall('.+?(?=/'+os.environ["SUBMITDIR"]+')',key)[0] 
        ## Now add in the time parameter: 
        self.time = time
        ## We will index by the submit file name prefix if it exists: 
        submit_search = re.findall('.+?(?=/submit.json)',os.path.basename(key))
        try:
            submit_name = submit_search[0]
        except IndexError as e:
            ## If the filename is just "submit.json, we just don't append anything to the job name. "
            submit_name = ""

        #### Parse submit file 
        submit_file = utilsparams3.load_json(bucket_name, key)
        
        ## Machine formatted fields (error only available in lambda) 
        ## These next three fields check that the submit file is correctly formatted
        try: 
            self.timestamp = submit_file["timestamp"]
            ## KEY: Now set up logging in the input folder too: 
        except KeyError as ke:
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("[JOB TERMINATE REASON] 'timestamp' field not given in submit.json file.")

        ## Initialize s3 directory for this job. 
        self.jobname = "job_{}_{}_{}".format(submit_name,bucket_name,self.timestamp)
        jobpath = os.path.join(self.path,os.environ['OUTDIR'],self.jobname)
        self.jobpath = jobpath
        try:
            ## And create a corresponding directory in the submit area. 
            create_jobdir  = utilsparams3.mkdir(self.bucket_name, os.path.join(self.path,os.environ['OUTDIR']),self.jobname)

            ## Create a logging object and write to it. 
            ## a logger for the submit area.  
            self.logger = utilsparams3.JobLogger_demo(self.bucket_name, self.jobpath)
            msg = "REQUEST START TIME: {} (GMT)".format(str(self.logger.basetime)[:-4])
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            msg = "ANALYSIS VERSION ID: {}".format(os.environ['versionid'].split("\n")[0])
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            msg = "JOB ID: {}".format(self.timestamp)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            self.logger._logs.append("\n ")
            msg = "[Job Manager] Detected new job: starting up."
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            msg = "        [Internal (init)] Initializing job manager."
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            ########################
            ## Now parse the rest of the file. 
            print("finished logging setup.")
        except ClientError as e:
            print("error with logging:", e.response["Error"])
        try:
            self.instance_type = submit_file['instance_type'] # TODO default option from config
        except KeyError as ke: 
            msg = "        [Internal (init)] Using default instance type {} from config file.".format(os.environ["INSTANCE_TYPE"])
            self.instance_type = os.environ["INSTANCE_TYPE"]
            # Log this message 
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()

        ## Check that we have a dataname field:
        submit_errmsg = "        [Internal (init)] INPUT ERROR: Submit file does not contain field {}, needed to analyze data."
        try: 
            self.data_name = submit_file['dataname'] # TODO validate extensions 
        except KeyError as ke:

            ## Write to logger
            self.logger.append(submit_errmsg.format(ke))
            self.logger.printlatest()
            self.logger.write()
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("[JOB TERMINATE REASON] 'dataname' field not given in submit.json file")

        try:
            self.config_name = submit_file["configname"] 
            self.logger.assign_config(self.config_name)
        except KeyError as ke:
            ## Write to logger
            self.logger.append(submit_errmsg.format(ke))
            self.logger.printlatest()
            self.logger.write()
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("[JOB TERMINATE REASON] 'configname' field not given in submit.json file")

        msg = "        [Internal (init)] Analysis request with dataset(s): {}, config file {}".format(self.data_name,self.config_name)
        self.logger.append(msg)
        self.logger.printlatest()
        self.logger.write()

    def check_existence(self):
        """
        Check for the existence of the corresponding data and config in s3. 
        """
        exists_errmsg = "        [Internal (check_existence)] INPUT ERROR: S3 Bucket does not contain {}"
        if type(self.data_name) is str:
            check_data_exists = utilsparams3.exists(self.bucket_name,self.data_name)
        elif type(self.data_name) is list:
            check_data_exists = all([utilsparams3.exists(self.bucket_name,name) for name in self.data_name])
        else:
            raise TypeError("[JOB TERMINATE REASON] 'dataname' field is not the right type. Should be string or list.")

        if not check_data_exists: 
            msg = exists_errmsg.format(self.data_name)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] 'dataname' field refers to data that cannot be found. Be sure this is a full path to the data, without the bucket name.")
        elif not utilsparams3.exists(self.bucket_name,self.config_name): 
            msg = exists_errmsg.format(self.config_name)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] 'configname' field refers to a configuration file that cannot be found. Be sure this is a fill path to the data, without the bucket name.")
        ###########################

        ## Now get the actual paths to relevant data from the foldername: 
        if type(self.data_name) is str:
            self.filenames = utilsparams3.extract_files(self.bucket_name,self.data_name,ext = None) 
        elif type(self.data_name) is list:
            self.filenames = self.data_name
        assert len(self.filenames) > 0, "[JOB TERMINATE REASON] The folder indicated is empty, or does not contain analyzable data."

    def get_costmonitoring(self):
        """
        Gets the cost incurred by a given group so far by looking at the logs bucket of the appropriate s3 folder.  
         
        """
        ## first get the path to the log folder we should be looking at. 
        group_name = self.path
        assert len(group_name) > 0; "[JOB TERMINATE REASON] Can't locate the group that triggered analysis, making it impossible to determine incurred cost."
        logfolder_path = "logs/{}/".format(group_name) 
        full_reportpath = os.path.join(logfolder_path,"i-")
        ## now get all of the computereport filenames: 
        all_files = utilsparams3.ls_name(self.bucket_name,full_reportpath)

        ## for each, we extract the contents: 
        jobdata = {}
        cost = 0
        ## now calculate the cost:
        for jobfile in all_files:
            instanceid = jobfile.split(full_reportpath)[1].split(".json")[0]
            jobdata = utilsparams3.load_json(self.bucket_name,jobfile)
            price = jobdata["price"]
            start = jobdata["start"]
            end = jobdata["end"]
            try:
                starttime = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
                endtime = datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
                diff = endtime-starttime
                duration = abs(diff.seconds)
                instcost = price*duration/3600.
            except TypeError:
                ## In rare cases it seems one or the other of these things don't actually have entries. This is a problem. for now, charge for the hour: 
                instcost = price
            cost+= instcost
        
        ## Now compare with budget:
        budget = float(os.environ["MAXCOST"])

        if cost < budget:
            message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Remaining budget: ${}".format(cost,budget-cost)
            self.logger.append(message)
            self.logger.printlatest()
            self.logger.write()
            validjob = True
        elif cost >= budget:
            message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Over budget (${}), cancelling job. Contact administrator.".format(cost,budget)
            self.logger.append(message)
            self.logger.printlatest()
            self.logger.write()
            validjob = False
        return validjob

    def parse_config(self):
        """
        Parse the config file given for specific neurocaas parameters. In particular, the *duration* of the job, and the *dataset size* 
        TODO: check for type in these configuration files. 
        """
        extension = os.path.splitext(self.config_name)[-1]
        if extension == ".json":
            passed_config = utilsparams3.load_json(self.bucket_name,self.config_name)
        elif extension == ".yaml":
            passed_config = utilsparams3.load_yaml(self.bucket_name,self.config_name)

        try:
            self.jobduration = passed_config["__duration__"]
            self.logger.append("        [Internal (parse_config)] parameter __duration__ given: {}".format(self.jobduration))
            self.logger.printlatest()
            self.logger.write()
        except KeyError:
            self.logger.append("        [Internal (parse_config)] parameter __duration__ not given, proceeding with standard compute launch.")
            self.logger.printlatest()
            self.logger.write()
            self.jobduration = None
        try:
            self.jobsize = passed_config["__dataset_size__"]
            self.logger.append("        [Internal (parse_config)] parameter __dataset_size__ given: {}".format(self.jobsize))
            self.logger.printlatest()
            self.logger.write()
        except KeyError:
            self.logger.append("        [Internal (parse_config)] parameter __dataset_size__ is not given, proceeding with standard storage." )
            self.logger.printlatest()
            self.logger.write()
            self.jobsize = None

    def acquire_instances(self):
        """
        Streamlines acquisition, setting up of multiple instances. Better exception handling when instances cannot be launched, and spot instances with defined duration when avaialble.   

        """
        nb_instances = len(self.filenames)

        ## Check how many instances are running. 
        active = utilsparamec2.count_active_instances(self.instance_type)
        ## Ensure that we have enough bandwidth to support this request:
        if active +nb_instances < int(os.environ['DEPLOY_LIMIT']):
            pass
        else:
            self.logger.append("        [Internal (acquire_instances)] RESOURCE ERROR: Instance requests greater than pipeline bandwidth. Please contact NeuroCAAS admin.")
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] Instance requests greater than pipeline bandwidth. Too many simultaneously deployed analyses.")
        
        instances = utilsparamec2.launch_new_instances(
        instance_type=self.instance_type, 
        ami=os.environ['AMI'],
        logger=  self.logger,
        number = nb_instances,
        add_size = self.full_volumesize,
        duration = self.jobduration
        )

        ## Even though we have a check in place, also check how many were launched:
        try:
            assert len(instances) > 0
        except AssertionError:
            self.logger.append("        [Internal (acquire_instances)] RESOURCE ERROR: Instances not launched. AWS capacity reached. Please contact NeuroCAAS admin.")
            self.logger.printlatest()
            self.logger.write()
            raise AssertionError("[JOB TERMINATE REASON] Instance requests greater than pipeline bandwidth (base AWS capacity). Too many simultaneously deployed analyses")

        self.instances = instances
        return instances

    def log_jobs(self):
        """
        Once instances are acquired, create logs that can be filled in as they run.  
        """

        all_logs = []
        for instance in self.instances:
            log = {}
            log["instance-id"] = instance.instance_id 
            name = "{}.json".format(log["instance-id"])
            log["instance-type"] = instance.instance_type
            if instance.spot_instance_request_id:
                log["spot"] = True
            else:
                log["spot"] = False
            log["price"] = utilsparampricing.price_instance(instance)
            log["databucket"] = self.bucket_name
            log["datapath"] = self.data_name 
            log["configpath"] = self.config_name
            log["jobpath"] = self.jobpath
            log["start"] = None
            log["end"] = None
            utilsparams3.write_active_monitorlog(self.bucket_name,name,log)
            all_logs.append(log)
        return all_logs

    def start_instance(self):
        """ Starts new instances if stopped. We write a special loop for this one because we only need a single 60 second pause for all the intances, not one for each in serial. Specialized certificate messages. """
        utilsparamec2.start_instances_if_stopped(
            instances=self.instances,
            logger=self.logger
        )
        self.logger.append("        [Internal (start_instance)] Created {} immutable analysis environments.".format(len(self.filenames)))
        self.logger.printlatest()
        self.logger.write()

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance. This version requires that you include a config (fourth) argument """
        try: 
            os.environ['COMMAND'].format("a","b","c","d")
        except IndexError as ie:
            msg = "        [Internal (process_inputs)] INPUT ERROR: not enough arguments in the COMMAND argument."
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] Not the correct format for arguments. Protocols for job manager are misformatted.")
     

        ## Should we vectorize the log here? 
        outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)

        print([os.environ['COMMAND'].format(
              self.bucket_name, filename, outpath_full, self.config_name
              ) for filename in self.filenames],"command send")
        for f,filename in enumerate(self.filenames):
            response = utilsparamssm.execute_commands_on_linux_instances(
                commands=[os.environ['COMMAND'].format(
                    self.bucket_name, filename, outpath_full, self.config_name
                    )], # TODO: variable outdir as option
                instance_ids=[self.instances[f].instance_id],
                working_dirs=[os.environ['WORKING_DIRECTORY']],
                log_bucket_name=self.bucket_name,
                log_path=os.path.join(self.jobpath,'internal_ec2_logs')
                )
            self.logger.initialize_datasets_dev(filename,self.instances[f].instance_id,response["Command"]["CommandId"])
            self.logger.append("        [Internal (process_inputs)] Starting analysis {} with parameter set {}".format(f+1,os.path.basename(filename)))
            self.logger.printlatest()
            self.logger.write()
        self.logger.append("        [Internal (process_inputs)] All jobs submitted. Processing...")


    ## Declare rules to monitor the states of these instances.  
    def put_instance_monitor_rule(self): 
        """ For multiple datasets."""
        self.logger.append("        [Internal (put_instance_monitor_rule)] Setting up monitoring on all instances...") 
        ruledata,rulename = utilsparamevents.put_instances_rule(self.instances,self.jobname)
        self.rulename = rulename
        self.ruledata = ruledata
        arn = ruledata['RuleArn']
        ## Now attach it to the given target
        targetdata = utilsparamevents.put_instance_target(rulename) 

    def compute_volumesize(self):
        """
        Takes the current ami volume size and adds in the size of the data that will be analyzed.  
        """
        ## First compute default volume size. 
        default_size = utilsparamec2.get_volumesize(os.environ["AMI"]) 
        if self.jobsize is not None: 
            self.full_volumesize = default_size+self.jobsize
        else: 
            self.full_volumesize = default_size

## We are no longer using this function. It depends upon automation documents that can be found in the cfn utils_stack template. Consider using this as a reference when switching to automation documents instead of pure runcommand. 
    def add_volumes(self):
        """
        adds volumes to the data you will process. 
        """
        print(self.jobsize,"self.jobsize")
        if self.jobsize is not None: 
            ## create a dictionary pairing your instance_ids with jobsize. 
            ## later we can tailor this. 
            instancedict = {inst.instance_id:self.jobsize for inst in self.instances}
            attach_responses = utilsparamec2.prepare_volumes(instancedict)
            utilsparamssm.mount_volumes(attach_responses)
        else: 
            pass


## Lambda code for deployment from other buckets. 
class Submission_deploy():
    """
    Object for ncap upload handling where inputs can come from specific user buckets. We then need to partition and replicate output between the user input bucket and the submit bucket. Input and submit buckets are structured as follows:  
    Input Bucket:
    -inputs
    +data
    +configs
    -results
    -job folder
    +results
    +per-dataset logs
    +per-job certificate

    Submit Bucket: 
    - group name
    -inputs
    +submit.json files referencing the input bucket. 
    -results
    +per-job certificate 
    +internal ec2 logs. 
    """
    def __init__(self,bucket_name,key,time):
        #### Declare basic parameters: 
        # Get Upload Location Information
        self.bucket_name = bucket_name

        ## Important paths: 
        ## Get directory above the input directory where the job was submitted. 
        self.path = re.findall('.+?(?=/'+os.environ["INDIR"]+')',key)[0] 
        ## The other important directory is the actual base directory of the input bucket itself. 

        ## Now add in the time parameter: 
        self.time = time

        #### Set up basic logging so we can get a trace when errors happen.   
        ## We will index by the submit file name prefix if it exists: 
        submit_search = re.findall('.+?(?=/submit.json)',os.path.basename(key))
        try:
            submit_name = submit_search[0]
        except IndexError as e:
            ## If the filename is just "submit.json, we just don't append anything to the job name. "
            submit_name = ""
        #### Parse submit file 
        submit_file = utilsparams3.load_json(bucket_name, key)
        
        ## These next three fields check that the submit file is correctly formatted
        try: 
            self.timestamp = submit_file["timestamp"]
            ## KEY: Now set up logging in the input folder too: 
        except KeyError as ke:
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("Missing timestamp when data was uploaded.")

        ## Now we're going to get the path to the results directory in the submit folder: 
        self.jobname = "job_{}_{}_{}".format(submit_name,bucket_name,self.timestamp)
        jobpath = os.path.join(self.path,os.environ['OUTDIR'],self.jobname)
        self.jobpath_submit = jobpath
        ## And create a corresponding directory in the submit area. 
        create_jobdir  = utilsparams3.mkdir(self.bucket_name, os.path.join(self.path,os.environ['OUTDIR']),self.jobname)
        ## a logger for the submit area.  
        self.logger = utilsparams3.JobLogger_demo(self.bucket_name, self.jobpath)
        self.logger.append("Initializing EPI analysis: Parameter search for 2D LDS.")
        self.logger.write()


        try:
            self.instance_type = submit_file['instance_type'] # TODO default option from config
        except KeyError as ke: 
            msg = "Using default instance type {} from config file".format(os.environ["INSTANCE_TYPE"])
            self.instance_type = os.environ["INSTANCE_TYPE"]

        ## Check that we have a dataname field:
        submit_errmsg = "INPUT ERROR: Submit file does not contain field {}, needed to analyze data."
        try: 
            self.input_bucket_name = submit_file["bucketname"]
            ## KEY: Now set up logging in the input folder too: 
            self.inputlogger = utilsparams3.JobLogger(self.input_bucket_name,os.path.join(os.environ['OUTDIR'],self.jobname)) ##TODO: this relies upon "OUTDIR" being the same in the submit and input buckets. Make sure to alter this later. 
        except KeyError as ke:

            print(submit_errmsg.format(ke))
            ## Write to logger
            self.submitlogger.append(submit_errmsg.format(ke))
            self.submitlogger.write()
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("Missing bucket name where data is located.")

        try: 
            self.data_name = submit_file['dataname'] # TODO validate extensions 
        except KeyError as ke:

            print(submit_errmsg.format(ke))
            ## Write to logger
            self.submitlogger.append(submit_errmsg.format(ke))
            self.submitlogger.write()
            self.inputlogger.append(submit_errmsg.format(ke))
            self.inputlogger.write()
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError("Missing data name to analyze")

        try:
            self.config_name = submit_file["configname"] 
            self.submitlogger.assign_config(self.config_name)
        except KeyError as ke:
            print(submit_errmsg.format(ke))
            ## Write to logger
            self.submitlogger.append(submit_errmsg.format(ke))
            self.submitlogger.write()
            self.inputlogger.append(submit_errmsg.format(ke))
            self.inputlogger.write()
            ## Now raise an exception to halt processing, because this is a catastrophic error.  
            raise ValueError(os.environ["MISSING_CONFIG_ERROR"])

        ## Check that we have the actual data in the bucket.  
        exists_errmsg = "INPUT ERROR: S3 Bucket does not contain {}"
        if not utilsparams3.exists(self.input_bucket_name,self.data_name): 
            msg = exists_errmsg.format(self.data_name)
            self.submitlogger.append(msg)
            self.submitlogger.write()
            self.inputlogger.append(msg)
            self.inputlogger.write()
            raise ValueError("dataname given does not exist in bucket.")
        elif not utilsparams3.exists(self.input_bucket_name,self.config_name): 
            msg = exists_errmsg.format(self.config_name)
            self.submitlogger.append(msg)
            self.submitlogger.write()
            self.inputlogger.append(msg)
            self.inputlogger.write()
            raise ValueError("configname given does not exist in bucket.")

        ## Check what instance we should use. 
        try:
            self.instance_type = submit_file['instance_type'] 
        except KeyError as ke: 
            msg = "Instance type {} does not exist, using default from config file".format(ke)
            self.instance_type = os.environ["INSTANCE_TYPE"]
            ## Log this message.
            self.submitlogger.append(msg)
            self.submitlogger.write()
            self.inputlogger.append(msg)
            self.inputlogger.write()
        ###########################

        ## Now get the actual paths to relevant data from the foldername: 

        self.filenames = utilsparams3.extract_files(self.input_bucket_name,self.data_name,ext = None) 
        assert len(self.filenames) > 0, "we must have data to analyze."

    def acquire_instance(self):
        """ Acquires & Starts New EC2 Instances Of The Requested Type & AMI"""
        instances = []
        nb_instances = len(self.filenames)

        ## Check how many instances are running. 
        active = utilsparamec2.count_active_instances(self.instance_type)
        ## Ensure that we have enough bandwidth to support this request:
        if active +nb_instances < int(os.environ['DEPLOY_LIMIT']):
            pass
        else:
            self.submitlogger.append("RESOURCE ERROR: Instance requests greater than pipeline bandwidth. Please contact NCAP administrator.")
            self.inputlogger.append("RESOURCE ERROR: Instance requests greater than pipeline bandwidth. Please contact NCAP administrator.")
        
        for i in range(nb_instances):
            instance = utilsparamec2.launch_new_instance(
            instance_type=self.instance_type, 
            ami=os.environ['AMI'],
            logger=self.inputlogger
            )
            instances.append(instance)
        self.instances = instances

    def start_instance(self):
        """ Starts new instances if stopped. We write a special loop for this one because we only need a single 60 second pause for all the intances, not one for each in serial"""
        utilsparamec2.start_instances_if_stopped(
            instances=self.instances,
            logger=self.inputlogger
        )

    ## Declare rules to monitor the states of these instances.  
    def put_instance_monitor_rule(self): 
        """ For multiple datasets."""
        for instance in self.instances:
            self.submitlogger.append('Setting up monitoring on instance '+str(instance))
            self.inputlogger.append('Setting up monitoring on instance '+str(instance))
            ## First declare a monitoring rule for this instance: 
            ruledata,rulename = utilsparamevents.put_instance_rule(instance.instance_id)
            arn = ruledata['RuleArn']
            ## Now attach it to the given target
            targetdata = utilsparamevents.put_instance_target(rulename) 

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance. This version requires that you include a config (fourth) argument """
        print(self.input_bucket_name,'bucket name')
        print(self.filenames,'filenames')
        print(os.environ['OUTDIR'],'outdir')
        print(os.environ['COMMAND'],'command')
        try: 
            os.environ['COMMAND'].format("a","b","c","d")
        except IndexError as ie:
            msg = "not enough arguments in the COMMAND argument."
            self.submitlogger.append(msg)
            self.submitlogger.write()
            self.inputlogger.append(msg)
            self.inputlogger.write()
            raise ValueError("Not the correct format for arguments.")

        ## Should we vectorize the log here? 
        outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)
        [self.submitlogger.append("Sending command: {}".format(
            os.environ['COMMAND'].format(
                self.input_bucket_name, filename, outpath_full, self.config_name
            )
        )) for filename in self.filenames]
        [self.inputlogger.append("Sending command: {}".format(
            os.environ['COMMAND'].format(
                self.input_bucket_name, filename, outpath_full, self.config_name
            )
        )) for filename in self.filenames]

        print([os.environ['COMMAND'].format(
              self.input_bucket_name, filename, outpath_full, self.config_name
              ) for filename in self.filenames],"command sent")

        print(self.instances)
        for f,filename in enumerate(self.filenames):
            response = utilsparamssm.execute_commands_on_linux_instances(
                commands=[os.environ['COMMAND'].format(
                    self.input_bucket_name, filename, outpath_full, self.config_name
                    )], # TODO: variable outdir as option
                instance_ids=[self.instances[f].instance_id],
                working_dirs=[os.environ['WORKING_DIRECTORY']],
                log_bucket_name=self.bucket_name,
                log_path=os.path.join(self.jobpath_submit,'internal_ec2_logs')
                )
            #self.submitlogger.initialize_datasets_dev(filename,self.instances[f].instance_id,response["Command"]["CommandId"])
            self.inputlogger.initialize_datasets_dev(filename,self.instances[f].instance_id,response["Command"]["CommandId"])



def process_upload_dev(bucket_name, key,time):
    """ 
    Updated version that can handle config files. 
    Inputs:
    key: absolute path to created object within bucket.
    bucket: name of the bucket within which the upload occurred.
    time: the time at which the upload event happened. 
    
    Outputs:
    (int) error code
    """
    exitcode = 99

    donemessage = "[Job Manager] {s}: DONE" 
    awserrormessage = "[Job Manager] {s}: AWS ERROR. {e}\n[Job Manager] Shutting down job."
    internalerrormessage = "[Job Manager] {s}: INTERNAL ERROR. {e}\n[Job Manager] Shutting down job."

    
    ## Step 1: Initialization. Most basic checking for submit file. If this fails, will not generate a certificate. 
    step = "STEP 1/4 (Initialization)"
    try:
        if os.environ['LAUNCH'] == 'true':
            ## Now check how many datasets we have
            submission = Submission_dev(bucket_name, key, time)
        elif os.environ["LAUNCH"] == 'false':
            raise NotImplementedError("This option not available for configs. ")
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except ClientError as ce:
        e = ce.response["Error"]
        print(awserrormessage.format(s= step,e = e))
        return exitcode
    except Exception: 
        e = traceback.format_exc()
        print(internalerrormessage.format(s= step,e = e))
        return exitcode

    ## Step 2: Validation. If we the data does not exist, or we are over cost limit, this will fail.
    step = "STEP 2/4 (Validation)"
    try:
        submission.check_existence()
        valid = submission.get_costmonitoring()
        assert valid
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except AssertionError as e:
        e = "Error: Job is not covered by budget. Contact NeuroCAAS administrator."
        submission.logger.append(internalerrormessage.format(s= step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        return exitcode
    except ClientError as ce:
        e = ce.response["Error"]
        submission.logger.append(awserrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        return exitcode
    except Exception: 
        e = traceback.format_exc()
        submission.logger.append(internalerrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        return exitcode

    # Step 3: Setup: Getting the volumesize, hardware specs of immutable analysis environments. 
    step = "STEP 3/4 (Environment Setup)"
    try:
        submission.parse_config()
        submission.compute_volumesize()
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except ClientError as ce:
        e = ce.response["Error"]
        submission.logger.append(awserrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        utilsparams3.write_endfile(submission.bucket_name,submission.jobpath)
        return exitcode
    except Exception: 
        e = traceback.format_exc()
        submission.logger.append(internalerrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        utilsparams3.write_endfile(submission.bucket_name,submission.jobpath)
        return exitcode
    
    # Step 4: Processing: Creating the immutable analysis environments, sending the commands to them. 
    step = "STEP 4/4 (Initialize Processing)"
    try:
        ## From here on out, if something goes wrong we will terminate all created instances.
        instances=submission.acquire_instances()
        submission.logger.printlatest()
        submission.logger.write()
        jobs = submission.log_jobs()
        submission.logger.printlatest()
        submission.logger.write()
        ## NOTE: IN LAMBDA,  JSON BOOLEANS ARE CONVERTED TO STRING
        if os.environ["MONITOR"] == "true":
            submission.put_instance_monitor_rule()
        elif os.environ["MONITOR"] == "false":
            submission.append("        [Internal (monitoring)] Skipping monitor.")
        submission.logger.write()
        submission.start_instance()
        submission.logger.write()
        submission.process_inputs()
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
        submission.logger.append("JOB MONITOR LOG COMPLETE. SEE TOP FOR LIVE PER-DATASET MONITORING")
        submission.logger.initialize_monitor()
        ## should be a success at this point. 
        exitcode = 0
    except ClientError as ce:
        e = ce.response["Error"]
        ## We occasianally get "Invalid Instance Id calls due to AWS side errors."
        if e["Code"] == "InvalidInstanceId":
            e = "Transient AWS Communication Error. Please Try Again"
        submission.logger.append(awserrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()
        ## We need to separately attempt all of the relevant cleanup steps. 
        try:
            ## In this case we need to delete the monitor log: 
            [utilsparams3.delete_active_monitorlog(submission.bucket_name,"{}.json".format(inst.id)) for inst in instances]
        except Exception:
            se = traceback.format_exc()
            message = "While cleaning up from AWS Error, another error occured: {}".format(se)
            submission.logger.append(internalerrormessage.format(s = step,e = message))
            submission.logger.printlatest()
            submission.logger.write()
        try:
            ## We also need to delete the monitor rule:
            utilsparamevents.full_delete_rule(submission.rulename)
        except Exception:
            se = traceback.format_exc()
            message = "While cleaning up from AWS Error, another error occured: {}".format(se)
            submission.logger.append(internalerrormessage.format(s = step,e = message))
            submission.logger.printlatest()
            submission.logger.write()
        ## We finally need to terminate the relevant instances:  
        for inst in instances: 
            try:
                inst.terminate()
            except Exception:
                se = traceback.format_exc()
                message = "While cleaning up from AWS Error, another error occured: {}".format(se)
                submission.logger.append(internalerrormessage.format(s = step,e = message))
                submission.logger.printlatest()
                submission.logger.write()
                continue
    except Exception:
        e = traceback.format_exc()
        [inst.terminate() for inst in instances]
        submission.logger.append(internalerrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()

    return exitcode

## New 2/11: for disjoint data and upload buckets. 
def process_upload_deploy(bucket_name, key,time):
    """ 
    Updated version that can handle config files. 
    Inputs:
    key: absolute path to created object within bucket.
    bucket: name of the bucket within which the upload occurred.
    time: the time at which the upload event happened. 
    """

    ## Conditionals for different deploy configurations: 
    ## First check if we are launching a new instance or starting an existing one. 
    ## NOTE: IN LAMBDA,  JSON BOOLEANS ARE CONVERTED TO STRING
    if os.environ['LAUNCH'] == 'true':
        ## Now check how many datasets we have
        submission = Submission_deploy(bucket_name, key, time)
    elif os.environ["LAUNCH"] == 'false':
        raise NotImplementedError("This option not available for configs. ")
    print("acquiring")
    submission.acquire_instance()
    print('writing0')
    submission.inputlogger.write()
    submission.submitlogger.write()
    ## NOTE: IN LAMBDA,  JSON BOOLEANS ARE CONVERTED TO STRING
    if os.environ["MONITOR"] == "true":
        print('setting up monitor')
        submission.put_instance_monitor_rule()
    elif os.environ["MONITOR"] == "false":
        print("skipping monitor")
    print('writing1')
    submission.inputlogger.write()
    submission.submitlogger.write()
    print('starting')
    submission.start_instance()
    print('writing2')
    print('sending')
    submission.process_inputs()
    print("writing3")
    submission.inputlogger.write()
    submission.submitlogger.write()
    
## Actual lambda handlers. 
def handler_develop(event,context):
    """
    Newest version of handler that logs outputs to a subfolder of the result folder that is indexed by the job submission date and the submit name.
    """
    for record in event['Records']:
        time = record['eventTime']
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        #print("handler_params",bucket_name,key,time)
        #print(event,context,'event, context')
        exitcode = process_upload_dev(bucket_name, key, time);
        print("processing returned exit code {}".format(exitcode))
    return exitcode 


def handler_deploy(event,context):
    """
    E
    """
    
    for record in event['Records']:
        time = record['eventTime']
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        process_upload_deploy(bucket_name, key, time);
