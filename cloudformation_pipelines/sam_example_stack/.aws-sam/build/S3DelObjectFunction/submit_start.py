import os
import json
import traceback


try:
    #import utils_param.config as config
    import utilsparam.s3
    import utilsparam.ssm
    import utilsparam.ec2
    import utilsparam.events
except Exception as e:
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
class Submission_Launch():
    """ Collection of data for a single request to process a dataset """

    def __init__(self, bucket_name, key):
        """ """

        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-2])
        self.logger = utilsparam.s3.Logger(self.bucket_name, self.path)
        #self.out_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        #self.in_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File 
        submit_config = utilsparam.s3.load_json(bucket_name, key)
        self.instance_type = submit_config['instance_type'] # TODO default option from config
        self.data_filename = submit_config['filename'] # TODO validate extensions & check existence

    def acquire_instance(self):
        """ Acquires & Starts New EC2 Instance Of The Requested Type & AMI"""
        self.instance = utilsparam.ec2.launch_new_instance(
            instance_type=self.instance_type, 
            ami=os.environ['AMI'],
            logger=self.logger
        )

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


class Submission_Launch_folder(Submission_Launch):
    "Generalization to a folder in the bucket"
    def __init__(self, bucket_name, key):
        """ """

        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-2])
        self.logger = utilsparam.s3.Logger(self.bucket_name, self.path)
        #self.out_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        #self.in_path = utilsparam.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File 
        submit_config = utilsparam.s3.load_json(bucket_name, key)
        self.instance_type = submit_config['instance_type'] # TODO default option from config
        self.data_name = submit_config['dataname'] # TODO validate extensions & check existence
        ## Now get the actual paths to relevant data from the foldername: 
        self.filenames = utilsparam.s3.extract_files(self.bucket_name,self.data_name,ext = None) 
        assert len(self.filenames) > 0, "we must have data to analyze."
        
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
                self.bucket_name, filename, os.environ['OUTDIR']
            )
        )) for filename in self.filenames]
        print([os.environ['COMMAND'].format(
              self.bucket_name, filename, os.environ['OUTDIR']
              ) for filename in self.filenames],"command send")
        for f,filename in enumerate(self.filenames):
            response = utilsparam.ssm.execute_commands_on_linux_instances(
                commands=[os.environ['COMMAND'].format(
                    self.bucket_name, filename, os.environ['OUTDIR']
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
        self.path = os.path.join(*key.split('/')[:-2])
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
    print("acquiring")
    submission.acquire_instance()
    print('writing0')
    submission.logger.write()
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

