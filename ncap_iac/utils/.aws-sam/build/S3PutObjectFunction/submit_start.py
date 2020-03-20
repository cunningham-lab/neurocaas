import os
import json
import traceback

try:
    import lambda_utils.config as config
    import lambda_utils.s3
    import lambda_utils.ssm
    import lambda_utils.ec2
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

class Submission_Start():
    ## Submission class for the case where the instances are being started.
    def __init__(self,bucket_name,key):
        # Get Upload Location Information
        self.bucket_name = bucket_name
        self.path = os.path.join(*key.split('/')[:-1])
        self.logger = utils.s3.Logger(self.bucket_name, self.path)
        self.out_path = utils.s3.mkdir(self.bucket_name, self.path, config.OUTDIR)
        self.in_path = utils.s3.mkdir(self.bucket_name, self.path, config.INDIR)

        # Load Content Of Submit File
        submit_config = utils.s3.load_json(bucket_name, key)
        self.instance_id = submit_config['instance_id'] # TODO default option from config
        self.data_filename = submit_config['filename'] # TODO validate extensions & check existence
    def acquire_instance(self):
        self.instance = utils.ec2.get_instance(self.instance_id,self.logger)
        utils.ec2.start_instance_if_stopped(
            instance=self.instance,
            logger=self.logger
        )

    def process_inputs(self):
        """ Initiates Processing On Previously Acquired EC2 Instance """
        self.logger.append("Sending command: {}".format(
            config.COMMAND.format(
                self.bucket_name, self.path, self.data_filename
            )
        ))
        response = utils.ssm.execute_commands_on_linux_instances(
            commands=[config.COMMAND.format(
                self.bucket_name, self.path, self.data_filename
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
    submission = Submission_Start(bucket_name, key)
    submission.acquire_instance()
    submission.logger.write()
    submission.process_inputs()
    submission.logger.write()


def handler(event, context):
    """ Handler that get called by lambda whenever an event occurs. """
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        process_upload(bucket_name, key);
