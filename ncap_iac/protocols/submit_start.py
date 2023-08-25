import os
import sys
import json
import traceback
from botocore.exceptions import ClientError
import re
from datetime import datetime

defaultduration = 60 ## this should be picked up and set as a global parameter later. 

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
        raise


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
    
    :param bucket_name: name of the S3 bucket that this is a submission for (corresponds to an analysis). 
    :param key: key of submit file within this bucket. 
    :param time: some unique identifier that distinguishes this job from all others. 
    :ivar bucket_name: initial_value: bucket_name
    :ivar path: name of the group responsible for this job.  
    :ivar time: initial value: time  ## TODO Remove this field. 
    :ivar jobname: "job_{}_{}_{}".format(submit_name,bucket_name,self.timestamp)
    :ivar jobpath: os.path.join(path,"outputs",jobname)
    :ivar logger: s3.Logger object
    :ivar instance_type: either given in submit file, or default option of analysis. 
    :ivar data_name: submit file's dataname field. 
    :ivar config_name: submit file's configname field. 
    """
    def __init__(self,bucket_name,key,time):
        ## Initialize as before:
        # Get Upload Location Information
        self.bucket_name = bucket_name
        ## Get directory above the input directory: self.path is the groupname. 
        try:
            self.path = re.findall('.+?(?=/'+os.environ["SUBMITDIR"]+')',key)[0] 
        except IndexError:    
            raise FileNotFoundError("[JOB TERMINATE REASON] 'submit file {} is misformatted'".format(key))
        ## Now add in the time parameter: 
        self.time = time
        ## We will index by the submit file name prefix if it exists: 
        submit_search = re.findall('.+?(?=/submit.json)',os.path.basename(key))
        try:
            submit_name = submit_search[0]
        except IndexError as e:
            ## If the filename is just "submit.json, we just don't append anything to the job name. "
            submit_name = ""

        try:
            #### Parse submit file 
            submit_file = utilsparams3.load_json(bucket_name, key)
        except ClientError as e:
            print(e.response["Error"])
            raise FileNotFoundError("[JOB TERMINATE REASON] 'submit file {} could not be loaded from bucket {}'".format(key,bucket_name))
        
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
            create_jobdir  = utilsparams3.mkdir(self.bucket_name, os.path.dirname(self.jobpath),os.path.basename(self.jobpath))

            ## Create a logging object and write to it. 
            ## a logger for the submit area.  
            self.logger = utilsparams3.JobLogger_demo(self.bucket_name, self.jobpath)
            msg = "REQUEST START TIME: {} (GMT)".format(str(self.logger.basetime)[:-4])
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            msg = "ANALYSIS VERSION ID: {}".format(os.environ['versionid'])
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
            if type(self.data_name) == str:
                self.data_name_list = [self.data_name]
            else:    
                self.data_name_list = self.data_name 
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
        self.bypass_data = self.check_bypass(submit_file)

        ## overwrite logger if necessary:
        self.overwrite_jobpath_logger(submit_name,bucket_name)

    def overwrite_jobpath_logger(self,submit_name,bucket_name):     
        """Checks bypass data and overwrites the jobpath and logger if we need to. Keep the same jobname for ID purposes. 

        :param submit_name: name of original submit file
        :param bucket_name: name of bucket we associate with this analysis. 
        ivar: jobpath updated to be the new write location. 
        ivar: logger

        """
        #save current logger data: 
        old_logs  = self.logger._logs 
        old_config = self.logger._config
        if self.bypass_data["output"]["bucket"] is not None:
            ## Initialize s3 directory for this job.
            jobpath = os.path.join(self.bypass_data["output"]["resultpath"],self.jobname)
            self.jobpath = jobpath
            try:
                ## And create a corresponding directory in the submit area.
                create_jobdir  = utilsparams3.mkdir(self.bypass_data["output"]["bucket"],os.path.dirname(self.jobpath),os.path.basename(self.jobpath))

                ## Create a logging object and write to it.
                ## a logger for the submit area.
                self.logger = utilsparams3.JobLogger_demo(self.bypass_data["output"]["bucket"], self.jobpath)
                self.logger._logs = old_logs
                self.logger._config = old_config
                self.logger.write()
                print(self.logger.path)
            except ClientError as e:
                print("error with logging for bypass:", e.response["Error"])


    def check_bypass(self,submit_file):
        """Checks if we should perform any "bucket bypass" operations. 
        :param submit_file: the dictionary containing submit info. 
        :returns: dictionary with form {"input":{"bucket":None,"datapath":None,"configpath":None},"output":{"bucket":None,"resultpath":None}}, where fields are filled in based on existence of bypass options. 
        """
        ## Bucket bypass: if 1) full s3 path is given for both data and config, and 2) if they are both the same, overwrite bucket and path. 
        # check if both start with s3://:
        bypass_data = {"input":{"bucket":None,"datapath":None,"configpath":None},"output":{"bucket":None,"resultpath":None}}
        if self.data_name_list[0].startswith("s3://") and self.config_name.startswith("s3://"):
            dataname_split = self.data_name_list[0].replace("s3://","").split("/")
            configname_split = self.config_name.replace("s3://","").split("/")

            dataname_bucket = dataname_split[0]
            dataname_path = [("/").join(ds_split.replace("s3://","").split("/")[1:]) for ds_split in self.data_name_list]
            configname_bucket = configname_split[0]
            configname_path = ("/").join(configname_split[1:])

            assert dataname_bucket == configname_bucket, "If bypassing storage for input, data and config must be from same bucket."
            bypass_data["input"]["bucket"] = dataname_bucket
            bypass_data["input"]["datapath"] = dataname_path
            bypass_data["input"]["configpath"] = configname_path
            msg = "        [Internal (init)] Storage Bypass initiated from bucket: s3://{}".format(dataname_bucket)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()

        resultpath = submit_file.get("resultpath",False)
        if resultpath:
            assert resultpath.startswith("s3://"), "If bypassing storage for output, s3:// format path required"
            resultname_split = resultpath.replace("s3://","").split("/")
            resultname_bucket = resultname_split[0]
            resultname_path = ("/").join(resultname_split[1:])
            bypass_data["output"]["bucket"] = resultname_bucket
            bypass_data["output"]["resultpath"] = resultname_path

            msg = "        [Internal (init)] Storage Bypass initiated to bucket: s3://{}".format(resultname_bucket)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()

        msg = "        [Internal (init)] Full bypass info: {}".format(bypass_data)
        self.logger.append(msg)
        self.logger.printlatest()
        self.logger.write()
        return bypass_data    


    def check_existence(self):
        """
        Check for the existence of the corresponding data and config in s3. 
        """
        if self.bypass_data["input"]["bucket"] is not None:
            check_bucket = self.bypass_data["input"]["bucket"]
            data_check_paths = self.bypass_data["input"]["datapath"]
            config_check_path = self.bypass_data["input"]["configpath"]
        else:    
            check_bucket = self.bucket_name
            data_check_paths = self.data_name_list
            config_check_path = self.config_name

            
        exists_errmsg = "        [Internal (check_existence)] INPUT ERROR: S3 Bucket does not contain {}"

        print(check_bucket,data_check_paths,config_check_path,self.bypass_data,self.data_name,self.data_name_list)
        if not all([type(i) == str for i in data_check_paths]):
            raise TypeError("[JOB TERMINATE REASON] 'dataname' field is not the right type. Should be string or list.")
        check_data_exists = all([utilsparams3.exists(check_bucket,name) for name in data_check_paths])

        if not check_data_exists: 
            msg = exists_errmsg.format(data_check_paths)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] 'dataname' field refers to data that cannot be found. Be sure this is a full path to the data, without the bucket name.")
        elif not utilsparams3.exists(check_bucket,config_check_path): 
            msg = exists_errmsg.format(config_check_path)
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] 'configname' field refers to a configuration file that cannot be found. Be sure this is a fill path to the data, without the bucket name.")
        ###########################

        ## Now get the actual paths to relevant data from the foldername: 
        self.filenames = data_check_paths
        assert len(self.filenames) > 0, "[JOB TERMINATE REASON] The folder indicated is empty, or does not contain analyzable data."

    def prices_active_instances_ami(self,ami):
        """Calculate the price of each instance directly. 

        :param ami: (str) the id giving the number of instances with that ami. 
        :returns: float giving number of instances*minutes*price that they will be active.  
        """
        instances = utilsparamec2.get_active_instances_ami(ami)
        prices = [(int(tag["Value"])/60)*utilsparampricing.get_price(utilsparampricing.get_region_name(utilsparampricing.region_id),instance.instance_type,os = "Linux") for instance in instances for tag in instance.tags if tag["Key"] == "Timeout"]

        return sum(prices)

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
                message = "        [Internal (get_costmonitoring)] Duration of past jobs not found. Pricing for an hour"
                self.logger.append(message)
                self.logger.printlatest()
                instcost = price
            cost+= instcost
        
        ## Now compare against the cost of the job you're currently running: 
        ## need duration from config (self.parse_config), self.instance_type, and self.nb_instances
        ## By assuming they're all standard instances we upper bound the cost. 
        try:
            price = utilsparampricing.get_price(utilsparampricing.get_region_name(utilsparampricing.region_id),self.instance_type,os = "Linux")
            nb_instances = len(self.filenames)
            if self.jobduration is None:
                duration = defaultduration/60 ## in hours. 
            else:    
                duration = self.jobduration/60
            jobpricebound = duration*price*nb_instances    
            cost += jobpricebound
        except Exception as e:     
            print(e)
            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to estimate cost of current job.")

        ## Now compare agains the expected cost of instances with the current ami: 
        try:
            ami = os.environ["AMI"]
            total_activeprice = self.prices_active_instances_ami(ami)

        except Exception as e:    
            print(e)
            try:
                activeprice = utilsparampricing.get_price(utilsparampricing.get_region_name(utilsparampricing.region_id),self.instance_type,os = "Linux")
                number = len([i for i in utilsparamec2.get_active_instances_ami(ami)])
                activeduration = defaultduration*number/60 ## default to the default duration instead if not given. 
                total_activeprice = activeprice*activeduration
            except Exception as e:    
                print(e)
                raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to estimate cost of active jobs.")

        cost += total_activeprice   

        ## Now compare with budget:
        try:
            budget = float(utilsparamssm.get_budget_parameter(self.path,self.bucket_name))
        except ClientError as e:    
            try:
                assert e.response["Error"]["Code"] == "ParameterNotFound"
                budget = float(os.environ["MAXCOST"])
                message = "        [Internal (get_costmonitoring)] Customized budget not found. Using default budget value of {}".format(budget)
                self.logger.append(message)
                self.logger.printlatest()
            except:    
                raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")
        except Exception:    
            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")

        if cost < budget:
            message = "        [Internal (get_costmonitoring)] Projected total costs: ${}. Remaining budget: ${}".format(cost,budget-cost)
            self.logger.append(message)
            self.logger.printlatest()
            self.logger.write()
            validjob = True
        elif cost >= budget:
            message = "        [Internal (get_costmonitoring)] Projected total costs: ${}. Over budget (${}), cancelling job. Contact administrator.".format(cost,budget)
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
        if self.bypass_data["input"]["bucket"] is not None:
            check_bucket = self.bypass_data["input"]["bucket"]
            config_check_path = self.bypass_data["input"]["configpath"]
        else:    
            check_bucket = self.bucket_name
            config_check_path = self.config_name

        extension = os.path.splitext(config_check_path)[-1]
        if extension == ".json":
            passed_config = utilsparams3.load_json(check_bucket,config_check_path)
        elif extension == ".yaml":
            passed_config = utilsparams3.load_yaml(check_bucket,config_check_path)

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
        
        instances = utilsparamec2.launch_new_instances_with_tags_additional(
        instance_type=self.instance_type, 
        ami=os.environ['AMI'],
        logger=  self.logger,
        number = nb_instances,
        add_size = self.full_volumesize,
        duration = self.jobduration,
        group = self.path,
        analysis = self.bucket_name,
        job = self.jobname
        )
        #instances = utilsparamec2.launch_new_instances_with_tags(
        #instance_type=self.instance_type, 
        #ami=os.environ['AMI'],
        #logger=  self.logger,
        #number = nb_instances,
        #add_size = self.full_volumesize,
        #duration = self.jobduration
        #)

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

    def process_inputs(self,dryrun=False):
        """ Initiates Processing On Previously Acquired EC2 Instance. This version requires that you include a config (fourth) argument """
        try: 
            os.environ['COMMAND'].format("a","b","c","d")
        except IndexError as ie:
            msg = "        [Internal (process_inputs)] INPUT ERROR: not enough arguments in the COMMAND argument."
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] Not the correct format for arguments. Protocols for job manager are misformatted.")
     
        ## input bucket: 
        if self.bypass_data["input"]["bucket"] is not None:
            input_bucket = self.bypass_data["input"]["bucket"]
            data_check_paths = self.bypass_data["input"]["datapath"]
            config_check_path = self.bypass_data["input"]["configpath"]
        else:    
            input_bucket = self.bucket_name
            data_check_paths = self.data_name_list
            config_check_path = self.config_name

        if self.bypass_data["output"]["bucket"] is not None:
            output_bucket = self.bypass_data["output"]["bucket"]
            result_check_paths = self.bypass_data["output"]["resultpath"]
            outpath_full = "s3://{}/{}".format(output_bucket,os.path.join(result_check_paths,self.jobname))
        else:    
            outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)


        ## Bypass: 
        #self.bucket_name -> input_bucket
        #self.filenames -> data_check_paths
        #outpath_full -> resultpath(FULL)
        #self.config_name -> config_check_path

        ## Should we vectorize the log here? 
        #outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)
        commands = [os.environ['COMMAND'].format(
              input_bucket, filename, outpath_full, config_check_path
              ) for filename in data_check_paths]

        print(commands,"command to send")
        if not dryrun:
            for f,filename in enumerate(data_check_paths):
                response = utilsparamssm.execute_commands_on_linux_instances(
                    commands=[os.environ['COMMAND'].format(
                        input_bucket, filename, outpath_full, config_check_path
                        )], # TODO: variable outdir as option
                    instance_ids=[self.instances[f].instance_id],
                    working_dirs=[os.environ['WORKING_DIRECTORY']],
                    log_bucket_name=input_bucket,
                    log_path=os.path.join(self.jobpath,'internal_ec2_logs')
                    )
                self.logger.initialize_datasets_dev(filename,self.instances[f].instance_id,response["Command"]["CommandId"])
                self.logger.append("        [Internal (process_inputs)] Starting analysis {} with parameter set {}".format(f+1,os.path.basename(filename)))
                self.logger.printlatest()
                self.logger.write()
            self.logger.append("        [Internal (process_inputs)] All jobs submitted. Processing...")
        return commands


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


class Submission_multisession(Submission_dev):
    """
    Specific lambda for purposes of development.  
    
    :param bucket_name: name of the S3 bucket that this is a submission for (corresponds to an analysis). 
    :param key: key of submit file within this bucket. 
    :param time: some unique identifier that distinguishes this job from all others. 
    :ivar bucket_name: initial_value: bucket_name
    :ivar path: name of the group responsible for this job.  
    :ivar time: initial value: time  ## TODO Remove this field. 
    :ivar jobname: "job_{}_{}_{}".format(submit_name,bucket_name,self.timestamp)
    :ivar jobpath: os.path.join(path,"outputs",jobname)
    :ivar logger: s3.Logger object
    :ivar instance_type: either given in submit file, or default option of analysis. 
    :ivar data_name: submit file's dataname field. 
    :ivar config_name: submit file's configname field. 
    """
    def __init__(self,bucket_name,key,time):
        super().__init__(bucket_name,key,time)

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
                message = "        [Internal (get_costmonitoring)] Duration of past jobs not found. Pricing for an hour"
                self.logger.append(message)
                self.logger.printlatest()
                instcost = price
            cost+= instcost
        
        ## Now compare against the cost of the job you're currently running: 
        ## need duration from config (self.parse_config) and self.instance_type
        ## By assuming they're all standard instances we upper bound the cost. 
        try:
            price = utilsparampricing.get_price(utilsparampricing.get_region_name(utilsparampricing.region_id),self.instance_type,os = "Linux")
            if self.jobduration is None:
                duration = defaultduration/60 ## in hours. 
            else:    
                duration = self.jobduration/60
            jobpricebound = duration*price  
            cost += jobpricebound
        except Exception as e:     
            print(e)
            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to estimate cost of current job.")

        ## Now compare agains the expected cost of instances with the current ami: 
        try:
            ami = os.environ["AMI"]
            total_activeprice = self.prices_active_instances_ami(ami)

        except Exception as e:    
            print(e)
            try:
                activeprice = utilsparampricing.get_price(utilsparampricing.get_region_name(utilsparampricing.region_id),self.instance_type,os = "Linux")
                number = len([i for i in utilsparamec2.get_active_instances_ami(ami)])
                activeduration = defaultduration*number/60 ## default to the default duration instead if not given. 
                total_activeprice = activeprice*activeduration
            except Exception as e:    
                print(e)
                raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to estimate cost of active jobs.")

        cost += total_activeprice   

        ## Now compare with budget:
        try:
            budget = float(utilsparamssm.get_budget_parameter(self.path,self.bucket_name))
        except ClientError as e:    
            try:
                assert e.response["Error"]["Code"] == "ParameterNotFound"
                budget = float(os.environ["MAXCOST"])
                message = "        [Internal (get_costmonitoring)] Customized budget not found. Using default budget value of {}".format(budget)
                self.logger.append(message)
                self.logger.printlatest()
            except:    
                raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")
        except Exception:    
            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")

        if cost < budget:
            message = "        [Internal (get_costmonitoring)] Projected total costs: ${}. Remaining budget: ${}".format(cost,budget-cost)
            self.logger.append(message)
            self.logger.printlatest()
            self.logger.write()
            validjob = True
        elif cost >= budget:
            message = "        [Internal (get_costmonitoring)] Projected total costs: ${}. Over budget (${}), cancelling job. Contact administrator.".format(cost,budget)
            self.logger.append(message)
            self.logger.printlatest()
            self.logger.write()
            validjob = False
        return validjob

    def acquire_instances(self):
        """
        Streamlines acquisition, setting up of multiple instances. Better exception handling when instances cannot be launched, and spot instances with defined duration when avaialble.   

        """
        nb_instances = 1 #all datafiles will be used to train a single core model

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
        
        instances = utilsparamec2.launch_new_instances_with_tags_additional(
        instance_type=self.instance_type, 
        ami=os.environ['AMI'],
        logger=  self.logger,
        number = nb_instances,
        add_size = self.full_volumesize,
        duration = self.jobduration,
        group = self.path,
        analysis = self.bucket_name,
        job = self.jobname
        )
        #instances = utilsparamec2.launch_new_instances_with_tags(
        #instance_type=self.instance_type, 
        #ami=os.environ['AMI'],
        #logger=  self.logger,
        #number = nb_instances,
        #add_size = self.full_volumesize,
        #duration = self.jobduration
        #)

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

    def process_inputs(self,dryrun=False):
        """ Initiates Processing On Previously Acquired EC2 Instance. This version requires that you include a config (fourth) argument """
        try: 
            os.environ['COMMAND'].format("a","b","c","d")
        except IndexError as ie:
            msg = "        [Internal (process_inputs)] INPUT ERROR: not enough arguments in the COMMAND argument."
            self.logger.append(msg)
            self.logger.printlatest()
            self.logger.write()
            raise ValueError("[JOB TERMINATE REASON] Not the correct format for arguments. Protocols for job manager are misformatted.")
     
        ## input bucket: 
        if self.bypass_data["input"]["bucket"] is not None:
            input_bucket = self.bypass_data["input"]["bucket"]
            data_check_path = os.path.dirname(self.bypass_data["input"]["datapath"][0]) #use the path to the directory instead of the file paths
            config_check_path = self.bypass_data["input"]["configpath"]
        else:    
            input_bucket = self.bucket_name
            data_check_paths = os.path.dirname(self.data_name_list[0]) #use the path to the directory instead of the file paths
            config_check_path = self.config_name

        if self.bypass_data["output"]["bucket"] is not None:
            output_bucket = self.bypass_data["output"]["bucket"]
            result_check_paths = self.bypass_data["output"]["resultpath"]
            outpath_full = "s3://{}/{}".format(output_bucket,os.path.join(result_check_paths,self.jobname))
        else:    
            outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)


        ## Bypass: 
        #self.bucket_name -> input_bucket
        #self.filenames -> data_check_paths
        #outpath_full -> resultpath(FULL)
        #self.config_name -> config_check_path

        ## Should we vectorize the log here? 
        #outpath_full = os.path.join(os.environ['OUTDIR'],self.jobname)
        commands = [os.environ['COMMAND'].format(
              input_bucket, filename, outpath_full, config_check_path
              ) for filename in data_check_paths]

        print(commands,"command to send")
        if not dryrun:
            for f,dirname in enumerate(data_check_paths): #there will only be one
                response = utilsparamssm.execute_commands_on_linux_instances(
                    commands=[os.environ['COMMAND'].format(
                        input_bucket, dirname, outpath_full, config_check_path
                        )], # TODO: variable outdir as option
                    instance_ids=[self.instances[f].instance_id],
                    working_dirs=[os.environ['WORKING_DIRECTORY']],
                    log_bucket_name=input_bucket,
                    log_path=os.path.join(self.jobpath,'internal_ec2_logs')
                    )
                self.logger.initialize_datasets_dev(dirname,self.instances[f].instance_id,response["Command"]["CommandId"])
                self.logger.append("        [Internal (process_inputs)] Starting analysis {} with parameter set {}".format(f+1,os.path.basename(dirname)))
                self.logger.printlatest()
                self.logger.write()
            self.logger.append("        [Internal (process_inputs)] All jobs submitted. Processing...")
        return commands

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

class Submission_ensemble(Submission_dev):
    def check_existence(self):
        """
        Check existence for ensembling assumes there is only once dataset that we will copy n times. 
        """
        super().check_existence()
        assert len(self.filenames) == 1, "for ensembles, we must have only one dataset."



    def parse_config(self):
        """Parse the config file for the number of entries to include in this ensemble in addition to other neurocaas parameters. Additionally writes a copy of the config for each copy with just the jobnumber changed. Internally, creates a dictionary self.confignames and changes the self.filenames list to be duplicated, once for each item.    

        """
        super().parse_config()
        extension = os.path.splitext(self.config_name)[-1]
        if extension == ".json":
            passed_config = utilsparams3.load_json(self.bucket_name,self.config_name)
        elif extension == ".yaml":
            passed_config = utilsparams3.load_yaml(self.bucket_name,self.config_name)
        try:    
            self.ensemble_size = passed_config["ensemble_size"]    
        except KeyError:    
            raise KeyError("Ensemble size (ensemble_size) parameter not given.")
        ## Now change the filenames parameter accordingly.
        self.filenames = self.filenames*self.ensemble_size
        preconfigs = [dict(passed_config.items()) for i in range(self.ensemble_size)]
        [pc.update({"jobnb":i+1}) for i,pc in enumerate(preconfigs)]
        configdir = os.path.dirname(self.config_name)
        ## As is, this actually does not separate by jobname. Leads to overwrites and issues in processing :(
        self.ensembleconfigs = {os.path.join(configdir,"{}inst{}config.json".format(self.jobname,i+1)):preconfigs[i] for i in range(self.ensemble_size)} ## need to start at 1 because this parameter is parsed in analysis later. 
        for cfig in self.ensembleconfigs:
            utilsparams3.put_json(self.bucket_name,cfig,self.ensembleconfigs[cfig])
            
    def process_inputs(self):   
        """Uses per-dataset config files. as given in ensembleconfigs.  

        """
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
        configdir = os.path.dirname(self.config_name)

        print([os.environ['COMMAND'].format(
              self.bucket_name, filename, outpath_full, os.path.join(configdir,"{}inst{}config.json".format(self.jobname,f+1)) ## have to be consistent with parse_config. 
              ) for f,filename in enumerate(self.filenames)],"command send")
        for f,filename in enumerate(self.filenames):
            response = utilsparamssm.execute_commands_on_linux_instances(
                commands=[os.environ['COMMAND'].format(
                    self.bucket_name, filename, outpath_full, os.path.join(configdir,"{}inst{}config.json".format(self.jobname,f+1)) ## have to be consistent with parse_config
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
        pass

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
            print("creating submission object")
            submission = Submission_dev(bucket_name, key, time)
            print("created submission object")
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
        submission.parse_config()
        valid = submission.get_costmonitoring()
        assert valid
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except AssertionError as e:
        print(e)
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
            submission.logger.append("        [Internal (monitoring)] Skipping monitor.")
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
        try:
            [inst.terminate() for inst in instances]
        except UnboundLocalError:     
            submission.logger.append("No instances to terminate")
            submission.logger.printlatest()
            submission.logger.write()

        submission.logger.append(internalerrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()

    return exitcode

def process_upload_ensemble(bucket_name, key,time):
    """ 
    Ensemble processing for dgp. Make sure to read timeout, and update the jobnb field in the config across the ensemble.
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
            print("creating submission object")
            submission = Submission_ensemble(bucket_name, key, time)
            print("created submission object")
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
        submission.parse_config()
        valid = submission.get_costmonitoring()
        assert valid
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except AssertionError as e:
        print(e)
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
            submission.logger.append("        [Internal (monitoring)] Skipping monitor.")
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
    
def process_upload_multisession(bucket_name,key,time):
    exitcode = 99

    donemessage = "[Job Manager] {s}: DONE" 
    awserrormessage = "[Job Manager] {s}: AWS ERROR. {e}\n[Job Manager] Shutting down job."
    internalerrormessage = "[Job Manager] {s}: INTERNAL ERROR. {e}\n[Job Manager] Shutting down job."

    
    ## Step 1: Initialization. Most basic checking for submit file. If this fails, will not generate a certificate. 
    step = "STEP 1/4 (Initialization)"
    try:
        if os.environ['LAUNCH'] == 'true':
            ## Make submission object
            print("creating submission object")
            submission = Submission_multisession(bucket_name, key, time)
            print("created submission object")
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
        submission.parse_config()
        valid = submission.get_costmonitoring()
        assert valid
        submission.logger.append(donemessage.format(s = step))
        submission.logger.printlatest()
        submission.logger.write()
    except AssertionError as e:
        print(e)
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
            submission.logger.append("        [Internal (monitoring)] Skipping monitor.")
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
        try:
            [inst.terminate() for inst in instances]
        except UnboundLocalError:     
            submission.logger.append("No instances to terminate")
            submission.logger.printlatest()
            submission.logger.write()

        submission.logger.append(internalerrormessage.format(s = step,e = e))
        submission.logger.printlatest()
        submission.logger.write()

    return exitcode

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

def handler_ensemble(event,context):
    """
    Newest version of handler that logs outputs to a subfolder of the result folder that is indexed by the job submission date and the submit name.
    Update 05/25: first check the config file to see if this is predict mode or train mode. 
    """

    for record in event['Records']:
        time = record['eventTime']
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        submit_file = utilsparams3.load_json(bucket_name, key)
        configpath = submit_file["configname"]
        try:
            configfile = utilsparams3.load_json(bucket_name,configpath)
        except ValueError:    
            try:
                configfile = utilsparams3.load_yaml(bucket_name, configpath)
            except Exception:    
                raise Exception("Config is not json or yaml.")
        print("Processing in {} mode".format(configfile["mode"]))    
        if configfile["mode"] == "train":
            #print("handler_params",bucket_name,key,time)
            #print(event,context,'event, context')
            exitcode = process_upload_ensemble(bucket_name, key, time);
            print("processing returned exit code {}".format(exitcode))
        else:    
            exitcode = process_upload_dev(bucket_name, key, time);
            print("processing returned exit code {}".format(exitcode))
    return exitcode 

def handler_multisession(event,context):
    """
    Handler for multisession modeling. 
    """
    for record in event['Records']:
        time = record['eventTime']
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        submit_file = utilsparams3.load_json(bucket_name, key)
        configpath = submit_file["configname"]
        try:
            configfile = utilsparams3.load_yaml(bucket_name, configpath)
        except Exception:
            raise Exception("Config must be a valid YAML file.")
        try:
            if configfile["multisession"] == "True":
                print("Creating a single machine image for multisession modeling.")
                exitcode = process_upload_multisession(bucket_name, key, time)
                print("process returned exit code {}".format(exitcode))
            else: 
                exitcode = process_upload_dev(bucket_name, key, time)
                print("process returned with exit code {}".format(exitcode))
        except KeyError:
            raise Exception("Config file does not specify \"multisession\" param.")

    return exitcode