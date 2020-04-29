import sys
import time
import boto3

#### This code updates an ami with a new executable. It will first launch an instance. from an ami  

if __name__  == "__main__":
    # First launch an instance: 
    ami_id = sys.argv[1]
    ec2_resource = boto3.resource('ec2')
    out = ec2_resource.create_instances(ImageId=ami_id,
            InstanceType = 't2.micro',
            MinCount=1,
            MaxCount=1,
            DryRun=False,
            KeyName = "ta_testkey",
            SecurityGroups=['launch-wizard-34'],
            IamInstanceProfile={
                'Name':'ec2_ssm'})
    ## Now get the instance id: 
    instance = out[0]
    ami_instance_id = instance.instance_id

    ## Wait until this thing is started: 
    started = False
    while not started:
        instance.load()
        state = instance.state
        print("current state is: "+str(state))

        started = state['Name'] == 'running'
        time.sleep(1)
    time.sleep(60) ## We need to wait until the instance gets set up. 
    auto = True
    print('done')

    try:
        ## Now we're going to send commands to this instance via our automation document. 
        print(ami_instance_id,'instance id')
        ssmclient = boto3.client('ssm')
        if auto == False: 
            response = ssmclient.send_command(
                    InstanceIds = [ami_instance_id],
                    DocumentName = "DisplaySalutationTest",
                    DocumentVersion = '$LATEST')

            ## Now get the command id so we can monitor: 
            commandid = response['Command']['CommandId']
            for i in range(30):
                updated = ssmclient.list_commands(CommandId=commandid)
                time.sleep(1)
                print(updated)
        else:
            response = ssmclient.start_automation_execution(
                    DocumentName = "LaunchImageTest",
                    DocumentVersion = '$LATEST',
                    Parameters = {"InstanceId": [ami_instance_id]})
            executionid = response["AutomationExecutionId"]
            status = "InProgress"
            while status in ["Pending","InProgress"]:
                updated = ssmclient.get_automation_execution(AutomationExecutionId = executionid)
                status = updated['AutomationExecution']['AutomationExecutionStatus']
                print(updated)
                print(status)
                time.sleep(1)

            ## Now turn off the instance. 

    except Exception as e:
        print(e)

    ## Terminate. 
    instance.terminate()





