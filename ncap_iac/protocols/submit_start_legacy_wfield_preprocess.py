import os
import json
from botocore.exceptions import ClientError
import traceback
from datetime import datetime as datetime


try:
    #import utils_param.config as config
    import utilsparam.s3
    import utilsparam.ssm
    import utilsparam.ec2
    import utilsparam.events
    import utilsparam.pricing
except Exception as e:
    try:
        ## Most likely this comes from pytest and relative imports.
        from ncap_iac.protocols import utilsparam
    except:
        error = str(e)
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

## Version to launch an instance
class Submission_Launch_Monitor():
    """ Collection of data for a single request to process a dataset. Appended functions to allow for job logging."""

    def __init__(self, bucket_name, key):
        """ """

        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-3])
        self.logger = utilsparam.s3.Logger(self.bucket_name, self.path)
        #self.out_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        #self.in_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File
        submit_config = utilsparam.s3.load_json(bucket_name, key)
        self.instance_type = submit_config['instance_type'] # TODO default option from config
        self.data_filename = submit_config['filename'] # TODO validate extensions & check existence

    #def get_costmonitoring(self):
    #    """
    #    Gets the cost incurred by a given group so far by looking at the logs bucket of the appropriate s3 folder.
    #
    #    """
    #    ## first get the path to the log folder we should be looking at.
    #    group_name = self.path
    #    assert len(group_name) > 0; "[JOB TERMINATE REASON] Can't locate the group that triggered analysis, making it impossible to determine incurred cost."
    #    logfolder_path = "logs/{}/".format(group_name)
    #    full_reportpath = os.path.join(logfolder_path,"i-")
    #    ## now get all of the computereport filenames:
    #    all_files = utilsparam.s3.ls_name(self.bucket_name,full_reportpath)

    #    ## for each, we extract the contents:
    #    jobdata = {}
    #    cost = 0
    #    ## now calculate the cost:
    #    for jobfile in all_files:
    #        instanceid = jobfile.split(full_reportpath)[1].split(".json")[0]
    #        jobdata = utilsparam.s3.load_json(self.bucket_name,jobfile)
    #        price = jobdata["price"]
    #        start = jobdata["start"]
    #        end = jobdata["end"]
    #        try:
    #            starttime = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
    #            endtime = datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
    #            diff = endtime-starttime
    #            duration = abs(diff.seconds)
    #            instcost = price*duration/3600.
    #        except TypeError:
    #            ## In rare cases it seems one or the other of these things don't actually have entries. This is a problem. for now, charge for the hour:
    #            instcost = price
    #        cost+= instcost
    #
    #    ## Now compare with budget:
    #    try:
    #        budget = float(utilsparam.ssm.get_budget_parameter(self.path,self.bucket_name))
    #    except ClientError as e:
    #        try:
    #            assert e.response["Error"]["Code"] == "ParameterNotFound"
    #            budget = float(os.environ["MAXCOST"])
    #            message = "        [Internal (get_costmonitoring)] Customized budget not found. Using default budget value of {}".format(budget)
    #            self.logger.append(message)
    #        except:
    #            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")
    #    except Exception:
    #        raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")
    #

    #    if cost < budget:
    #        message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Remaining budget: ${}".format(cost,budget-cost)
    #        self.logger.append(message)
    #        self.logger.write()
    #        validjob = True
    #    elif cost >= budget:
    #        message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Over budget (${}), cancelling job. Contact administrator.".format(cost,budget)
    #        self.logger.append(message)
    #        self.logger.write()
    #        validjob = False
    #    return validjob


    def acquire_instance(self):
        """ Acquires & Starts New EC2 Instance Of The Requested Type & AMI"""
        self.instance = utilsparam.ec2.launch_new_instance(
            instance_type=self.instance_type,
            ami=os.environ['AMI'],
            logger=self.logger
        )

    #def log_jobs(self):
    #    """
    #    Once instances are acquired, create logs that can be filled in as they run.
    #    """

    #    all_logs = []
    #    for instance in [self.instance]:
    #        log = {}
    #        log["instance-id"] = instance.instance_id
    #        name = "{}.json".format(log["instance-id"])
    #        log["instance-type"] = instance.instance_type
    #        if instance.spot_instance_request_id:
    #            log["spot"] = True
    #        else:
    #            log["spot"] = False
    #        log["price"] = utilsparam.pricing.price_instance(instance)
    #        log["databucket"] = self.bucket_name
    #        log["datapath"] = self.data_filename
    #        #log["configpath"] = self.config_name
    #        log["jobpath"] = instance.instance_id ## this should be okay. For single instances, the monitoring rule = the instance id.
    #        log["start"] = None
    #        log["end"] = None
    #        utilsparam.s3.write_active_monitorlog(self.bucket_name,name,log)
    #        all_logs.append(log)
    #    return all_logs

    def start_instance(self):
        utilsparam.ec2.start_instance_if_stopped(
            instance=self.instance,
            logger=self.logger
        )

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance """
        print(self.bucket_name,'bucket name')
        print(self.data_filename,'filename')
        print(os.environ['OUTDIR'],'outdir')
        print(os.environ['COMMAND'],'command')
        self.logger.append("Sending command: {}".format(
            os.environ['COMMAND'].format(
                self.bucket_name, self.data_filename, os.environ['OUTDIR']
            )
        ))
        response = utilsparam.ssm.execute_commands_on_linux_instances(
            commands=[os.environ['COMMAND'].format(
                self.bucket_name, self.data_filename, os.environ['OUTDIR']
            )], # TODO: variable outdir as option
            instance_ids=[self.instance.instance_id],
            working_dirs=[os.environ['WORKING_DIRECTORY']],
            log_bucket_name=self.bucket_name,
            log_path=self.logger.path
        )
    ## Declare rules to monitor the states of these instances.
    def put_instance_monitor_rule(self):
        self.logger.append('Setting up monitoring on instance')
        ## First declare a monitoring rule for this instance:
        ruledata,rulename = utilsparam.events.put_instance_rule(self.instance.instance_id)
        arn = ruledata['RuleArn']
        ## Now attach it to the given target
        targetdata = utilsparam.events.put_instance_target(rulename)


class Submission_Launch_folder(Submission_Launch_Monitor):
    "Generalization to a folder in the bucket"
    def __init__(self, bucket_name, key):
        """ """

        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-3])
        self.logger = utilsparam.s3.Logger(self.bucket_name, self.path)
        #self.out_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        #self.in_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File
        submit_config = utilsparam.s3.load_json(bucket_name, key)
        self.instance_type = submit_config['instance_type'] # TODO default option from config
        self.data_name = submit_config['dataname'] # TODO validate extensions & check existence
        ## Now get the actual paths to relevant data from the foldername:
        self.filenames = utilsparam.s3.extract_files(self.bucket_name,self.data_name,ext='zip')
        assert len(self.filenames) > 0, "we must have data to analyze."

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
        all_files = utilsparam.s3.ls_name(self.bucket_name,full_reportpath)

        ## for each, we extract the contents:
        jobdata = {}
        cost = 0
        ## now calculate the cost:
        for jobfile in all_files:
            instanceid = jobfile.split(full_reportpath)[1].split(".json")[0]
            jobdata = utilsparam.s3.load_json(self.bucket_name,jobfile)
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
        try:
            budget = float(utilsparam.ssm.get_budget_parameter(self.path,self.bucket_name))
        except ClientError as e:
            try:
                assert e.response["Error"]["Code"] == "ParameterNotFound"
                budget = float(os.environ["MAXCOST"])
                message = "        [Internal (get_costmonitoring)] Customized budget not found. Using default budget value of {}".format(budget)
                self.logger.append(message)
            except:
                raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")
        except Exception:
            raise Exception("        [Internal (get_costmonitoring)] Unexpected Error: Unable to get budget.")


        if cost < budget:
            message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Remaining budget: ${}".format(cost,budget-cost)
            self.logger.append(message)
            self.logger.write()
            validjob = True
        elif cost >= budget:
            message = "        [Internal (get_costmonitoring)] Incurred cost so far: ${}. Over budget (${}), cancelling job. Contact administrator.".format(cost,budget)
            self.logger.append(message)
            self.logger.write()
            validjob = False
        return validjob

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
            log["price"] = utilsparam.pricing.price_instance(instance)
            log["databucket"] = self.bucket_name
            log["datapath"] = self.data_name
            #log["configpath"] = self.config_name
            log["jobpath"] = instance.instance_id ## this should be okay. For single instances, the monitoring rule = the instance id.
            log["start"] = None
            log["end"] = None
            utilsparam.s3.write_active_monitorlog(self.bucket_name,name,log)
            all_logs.append(log)
        return all_logs

    def acquire_instance(self):
        """ Acquires & Starts New EC2 Instances Of The Requested Type & AMI"""
        instances = []
        nb_instances = len(self.filenames)
        for i in range(nb_instances):
            instance = utilsparam.ec2.launch_new_instance(
            instance_type=self.instance_type,
            ami=os.environ['AMI'],
            logger=self.logger
            )
            instances.append(instance)
        self.instances = instances


    def start_instance(self):
        """ Starts new instances if stopped. We write a special loop for this one because we only need a single 60 second pause for all the intances, not one for each in serial"""
        utilsparam.ec2.start_instances_if_stopped(
            instances=self.instances,
            logger=self.logger
        )

    ## Declare rules to monitor the states of these instances.
    def put_instance_monitor_rule(self):
        """ For multiple datasets."""
        for instance in self.instances:
            self.logger.append('Setting up monitoring on instance '+str(instance))
            ## First declare a monitoring rule for this instance:
            ruledata,rulename = utilsparam.events.put_instance_rule(instance.instance_id)
            arn = ruledata['RuleArn']
            ## Now attach it to the given target
            targetdata = utilsparam.events.put_instance_target(rulename)

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance """
        print(self.bucket_name,'bucket name')
        print(self.filenames,'filenames')
        print(os.environ['OUTDIR'],'outdir')
        print(os.environ['COMMAND'],'command')
        ## Should we vectorize the log here?
        [self.logger.append("Sending command: {}".format(
            os.environ['COMMAND'].format(
                self.bucket_name,
                os.path.join(*filename.split('/')[:-1]), #filename,
                filename.split('/')[-1]                #os.environ['OUTDIR']
            )
        )) for filename in self.filenames]
        print([os.environ['COMMAND'].format(
                    self.bucket_name,
                    os.path.join(*filename.split('/')[:-1]), #filename,
                    filename.split('/')[-1]                #os.environ['OUTDIR']
              ) for filename in self.filenames],"command send")
        for f,filename in enumerate(self.filenames):
            response = utilsparam.ssm.execute_commands_on_linux_instances(
                commands=[os.environ['COMMAND'].format(
                    self.bucket_name,
                    os.path.join(*filename.split('/')[:-1]), #filename,
                    filename.split('/')[-1]                #os.environ['OUTDIR']
                )], # TODO: variable outdir as option
                instance_ids=[self.instances[f].instance_id],
                working_dirs=[os.environ['WORKING_DIRECTORY']],
                log_bucket_name=self.bucket_name,
                log_path=self.logger.path
                )


class Submission_Start_Stack():
    ## Submission class for the case where the instances are being started.
    def __init__(self,bucket_name,key):
        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-3])
        print('logging at '+self.path)
        self.logger = utilsparam.s3.Logger(self.bucket_name, self.path)
        #self.out_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        #self.in_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File
        submit_config = utilsparam.s3.load_json(bucket_name, key)
        self.instance_id = submit_config['instance_id'] # TODO default option from config
        self.data_filename = submit_config['filename'] # TODO validate extensions & check existence

    def acquire_instance(self):
        self.instance = utilsparam.ec2.get_instance(self.instance_id,self.logger)

    def start_instance(self):
        utilsparam.ec2.start_instance_if_stopped(
            instance=self.instance,
            logger=self.logger
        )

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance """
        print(self.bucket_name,'bucket name')
        print(self.data_filename,'filename')
        print(os.environ['OUTDIR'],'outdir')
        self.logger.append("Sending command: {}".format(
            os.environ['COMMAND'].format(
                self.bucket_name, self.data_filename, os.environ['OUTDIR']
            )
        ))
        response = utilsparam.ssm.execute_commands_on_linux_instances(
            commands=[os.environ['COMMAND'].format(
                self.bucket_name, self.data_filename, os.environ['OUTDIR']
            )], # TODO: variable outdir as option
            instance_ids=[self.instance.instance_id],
            working_dirs=[os.environ['WORKING_DIRECTORY']],
            log_bucket_name=self.bucket_name,
            log_path=self.logger.path
        )
    ## Declare rules to monitor the states of these instances.
    def put_instance_monitor_rule(self):
        self.logger.append('Setting up monitoring on instance')
        ## First declare a monitoring rule for this instance:
        ruledata,rulename = utilsparam.events.put_instance_rule(self.instance.instance_id)
        arn = ruledata['RuleArn']
        ## Now attach it to the given target
        targetdata = utilsparam.events.put_instance_target(rulename)

def process_upload(bucket_name, key):
    """ Given an upload key and bucket name, determine & take appropriate action
    key: absolute path to created object within bucket.
    bucket: name of the bucket within which the upload occurred.
    """
    ## Conditionals for different deploy configurations:
    ## First check if we are launching a new instance or starting an existing one.
    ## NOTE: IN LAMBDA,  JSON BOOLEANS ARE CONVERTED TO STRING
    if os.environ['LAUNCH'] == 'true':
        ## Now check how many datasets we have
        submission = Submission_Launch_folder(bucket_name, key)
    elif os.environ["LAUNCH"] == 'false':
        submission = Submission_Start_Stack(bucket_name, key)
    valid = submission.get_costmonitoring()
    assert valid, "Job must be covered by budget."
    print("acquiring")
    submission.acquire_instance()
    print('writing0')
    submission.logger.write()
    print("logging jobs")
    submission.log_jobs()
    ## NOTE: IN LAMBDA,  JSON BOOLEANS ARE CONVERTED TO STRING
    if os.environ["MONITOR"] == "true":
        print('setting up monitor')
        submission.put_instance_monitor_rule()
    elif os.environ["MONITOR"] == "false":
        print("skipping monitor")
    print('writing1')
    submission.logger.write()
    print('starting')
    submission.start_instance()
    print('writing2')
    print('sending')
    submission.process_inputs()
    print("writing3")
    submission.logger.write()

def handler(event, context):
    """ Handler that get called by lambda whenever an event occurs. """
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        print("handler_params",bucket_name,key)
        process_upload(bucket_name, key);
