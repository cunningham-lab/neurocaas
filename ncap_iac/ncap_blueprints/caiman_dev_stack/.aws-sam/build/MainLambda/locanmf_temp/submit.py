import os
import json
import traceback

try:
    import utils.config as config
    import utils.s3
    import utils.ssm
    import utils.ec2
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


class Submission():
    """ Collection of data for a single request to process a dataset """

    def __init__(self, bucket_name, key):
        """ """

        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-1])
        self.logger = utils.s3.Logger(self.bucket_name, self.path) # creates log folder
        # self.out_path = utils.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        # self.in_path = utils.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File 
        submit_config = utils.s3.load_json(bucket_name, key)
        self.instance_type = submit_config['instance_type'] # TODO default option from config
        self.data_filename = submit_config['data_filename'] # TODO validate extensions
        self.atlas_filename = submit_config['atlas_filename'] # TODO validate extensions
        self.params_filename = submit_config['params_filename'] # TODO validate extensions

    def check_inputs(self):
        """ Checks inputs, here: data, atlas and parameter files"""
        utils.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        goahead=1
        if not utils.s3.existfile(self.bucket_name,os.path.join(self.path,config.INDIR,self.data_filename)):
            self.logger.append("Please upload data file named: {}, and then upload submit file again!".format(os.path.join(self.path,config.INDIR,self.data_filename)))
            goahead=0
        if not utils.s3.existfile(self.bucket_name,os.path.join(self.path,config.INDIR,self.atlas_filename)):
            self.logger.append("Please upload atlas file named: {}, and then upload submit file again!".format(os.path.join(self.path,config.INDIR,self.atlas_filename)))
            goahead=0
        if not utils.s3.existfile(self.bucket_name,os.path.join(self.path,config.INDIR,self.params_filename)):
            self.logger.append("Please upload parameter file named: {}, and then upload submit file again!".format(os.path.join(self.path,config.INDIR,self.params_filename)))
            goahead=0
        return goahead
            
    def acquire_instance(self):
        """ Acquires & Starts New EC2 Instance Of The Requested Type & AMI"""
        # # Temporary; for debugging
        # INSTANCE_ID='i-0197dcd60c0ba26e9'
        # self.instance = utils.ec2.get_instance(instanceid=INSTANCE_ID,logger=self.logger)
        self.instance = utils.ec2.launch_new_instance(
            instance_type=self.instance_type, 
            ami=config.AMI,
            logger=self.logger
        )
        utils.ec2.start_instance_if_stopped(
            instance=self.instance,
            logger=self.logger
        )

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance """
        self.logger.append("Sending command: {}".format(
            config.COMMAND.format(
                self.bucket_name, self.path, config.INDIR, config.OUTDIR, config.LOGDIR, self.data_filename, self.atlas_filename, self.params_filename
            )
        ))
        response = utils.ssm.execute_commands_on_linux_instances(
            commands=[config.COMMAND.format(
                self.bucket_name, self.path, config.INDIR, config.OUTDIR, config.LOGDIR, self.data_filename, self.atlas_filename, self.params_filename
            )], # TODO: variable outdir as option
            instance_ids=[self.instance.instance_id],
            working_dirs=[config.WORKING_DIRECTORY],
            log_bucket_name=self.bucket_name,
            log_path=self.logger.path
        )



def process_upload(bucket_name, key):
    """ Given an upload key and bucket name, determine & take appropriate action
    key: absolute path to created object within bucket.
    bucket: name of the bucket within which the upload occurred.
    """
    object = key.split('/')[-1]
    if object == config.SUBMIT_FILE:
        submission = Submission(bucket_name, key)
        if submission.check_inputs():
            submission.acquire_instance()
            submission.logger.write()
            submission.process_inputs()
            submission.logger.write()
        else: 
            submission.logger.write()


def handler(event, context):
    """ Handler that get called by lambda whenever an event occurs. """
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        process_upload(bucket_name, key)