from __future__ import print_function
import sys
import boto3
import subprocess
from paramiko import SSHClient
import paramiko
from botocore.exceptions import ClientError
import psutil
import time


# from CreateInstance import *


# from boto.ec2.instance import Instance as _Instance


def awsInstance(appName, vmType, Bclass):  # , imageType, nodeID):
    if vmType == "1":
        instanceType2run = "c4.large"  # 2 vCPU 4 RAM
        numThread = "2"
    elif vmType == "2":
        instanceType2run = "c4.xlarge"  # 4 vCPU 8 RAM
        numThread = "4"
    elif vmType == "3":
        instanceType2run = "m4.2xlarge"  # 8 vCPU 32 RAM
        numThread = "8"
    elif vmType == "4":
        instanceType2run = "m4.4xlarge"  # 16 vCPU 64 RAM
        numThread = "16" ## change in rehanna code

    # instanceType2run = 't2.micro'  # microsmall

    commandsList = """cd ~; echo $PWD
        cd Downloads/NFS/NPB3.3.1/NPB3.3-OMP/; sh run1s-OMP-p-c-C-id-appName.sh aws """ + numThread +""" """+Bclass+ """ 17.7.24 """ + appName + """ 
        #sudo shutdown -f # sudo should be granted """
    # ImageId='	ami-43829a3a'

    # region=us-west-2

    ec2c = boto3.client('ec2', aws_access_key_id='AKI',
                        aws_secret_access_key='6qz', region_name='us-west-2')
    ec2s = boto3.resource('ec2', aws_access_key_id='AKIAJSFSIMVMOOXMC2AQ',
                          aws_secret_access_key='6qz', region_name='us-west-2')

    response = ec2c.describe_instances()
    print(' ')
    print('ec2c.describe_instances():', response)
    print(' ')

    print('Current VMs')
    instances = ec2s.instances.filter()
    for instance in instances:
        print('   ', instance.state["Name"], ', ', instance.id, ', ', instance.public_ip_address, ', ',
              instance.private_ip_address, ', ', instance.instance_type)
        # , u'InstanceId': 'i-06bf8ec62112ea75e',
        # , u'State': {u'Code': 16, u'Name': 'running'},
        # , u'Tags': [{u'Value': 'm0', u'Key': 'Name'}] ,
    print(' ')

    # key_pair = ec2.create_key_pair('ec2-sample-key')  # only needs to be done once
    # key_pair.save('/Users/patrick/.ssh')
    # exit(0)
    # reservationc = ec2c.run_instances(ImageId='ami-43829a3a',MinCount=1,MaxCount=1,InstanceType=instanceType2run)
    instanceCreated = ec2s.create_instances(ImageId='ami-43829a3a', MinCount=1, MaxCount=1,
                                            InstanceType=instanceType2run, KeyName='aws',
                                            SecurityGroups=['launch-wizard-1'])
    # class instance1:
    #    id = "i-017a788e21dcda1c7"
    # instanceCreated = [instance1]

    print('Checking VM Creation')
    notCreated = 0
    while notCreated == 0:
        sys.stdout.write('.')
        ec2s = boto3.resource('ec2', aws_access_key_id='AKI',
                              aws_secret_access_key='6qz',
                              region_name='us-west-2')  # 3
        instances = ec2s.instances.filter()
        # Wait a minute or two while it boots
        for instance in instances:
            if instance.id == instanceCreated[0].id:
                print(' ')
                print('   instance with id >', instance.id, ' created.')
                notCreated = 1
                break

    print(' ')
    print('Checking IP assignment')
    wait4ip = 0
    while wait4ip == 0:
        sys.stdout.write('.')
        ec2s = boto3.resource('ec2', aws_access_key_id='AKI',
                              aws_secret_access_key='6qz',
                              region_name='us-west-2')
        instances = ec2s.instances.filter(InstanceIds=[instanceCreated[0].id])
        for instance in instances:
            # print ('wait 4 ip assignment:',  instance2.tags[0]["Value"],instance2.state["Name"])
            if instance.public_ip_address != None:
                print(' ')
                print('   IP assigned to instance with id >', instance.id, ' IP >', instance.public_ip_address)
                wait4ip = 1
                instanceCreatedIP = instance.public_ip_address
                break

    print(' ')
    print('Checking BOOT')
    i = 0
    boot = 0
    while boot == 0:
        try:
            i = i + 1
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instanceCreatedIP, username="hrmoradi", password="113818", timeout=1)
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('echo ready')
            for line in ssh_stdout:
                if 'ready' in line:
                    print(' ')
                    print('   line:', line)
                    print('   server booted in > ', i, 'th attempt.')
                    print('   ')
                    ssh_stdin.close()
                    ready = 1
                    boot = 1
                    break
            ssh_stdin.close()
        except:
            sys.stdout.write('.')

    print('CommandsList')
    i = 0
    for line in commandsList.splitlines():
        i = i + 1
        print('   line', i, ' :', line)
        # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(line)
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instanceCreatedIP, username="hrmoradi", password="113818")
        sleeptime = 0.001
        ssh_transp = ssh.get_transport()
        chan = ssh_transp.open_session()
        # chan.settimeout(3 * 60 * 60)
        chan.setblocking(0)
        outdata, errdata = '', ''
        chan.exec_command(line)
        for OutputLines in ssh_stdout:
            print('      execution results: ssh_stdout >', OutputLines)
        while True:  # monitoring process
            # Reading from output streams
            while chan.recv_ready():
                outdata += chan.recv(1000)
            while chan.recv_stderr_ready():
                errdata += chan.recv_stderr(1000)
            if chan.exit_status_ready():  # If completed
                print('      execution results: outdata >')
                for OutputLines in outdata.splitlines():
                    print('                               ', OutputLines)
                print('      execution results: errdata >')
                for OutputLines in errdata.splitlines():
                    print('                               ', OutputLines)
                break
            time.sleep(sleeptime)
        retcode = chan.recv_exit_status()
        ssh_transp.close()
        print(' ')

    print(' ')
    print("Terminate instance")
    ec2c.terminate_instances(InstanceIds=[instanceCreated[0].id])
    i = 0
    wait4termination = 0
    while wait4termination == 0:
        i = i + 1
        sys.stdout.write('.')
        ec2s = boto3.resource('ec2', aws_access_key_id='AKI',
                              aws_secret_access_key='6qz',
                              region_name='us-west-2')
        instances = ec2s.instances.filter(InstanceIds=[instanceCreated[0].id])
        for instance in instances:
            # print ('wait 4 ip assignment:',  instance2.tags[0]["Value"],instance2.state["Name"])
            if instance.state["Name"] == 'terminated':
                print(' ')
                print('   server terminated in > ', i, 'th attempt.')
                wait4termination = 1
                break

    print(' ')
    print('End of CreateInstance.py')

def main(argv):
    awsInstance("bt", "3" ,"B")

if __name__ == "__main__":
    main(" ")




