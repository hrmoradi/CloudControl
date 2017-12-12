from __future__ import print_function
from paramiko import SSHClient
import paramiko
import time
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import random, string
import sys

def chameleonInstance(appName, vmType, Bclass):  # , imageType, nodeID):

    if vmType == "1":
        instanceType2run = "3"  # 2 vCPU 4 RAM
        numThread = "2"
    elif vmType == "2":
        instanceType2run = "5"  # 4 vCPU 8 RAM
        numThread = "4"
    elif vmType == "3":
        instanceType2run = "7"  # 8 vCPU 32 RAM
        numThread = "8"
    elif vmType == "4":
        instanceType2run = "7"  # 16 vCPU 64 RAM # we don't have that one !!! same as last one wil be created
        numThread = "16"


    commandsList = """cd ~; echo $PWD
           cd NPB3.3.1/NPB3.3-OMP/; sh run1s-OMP-p-c-C-id-appName.sh ch """ + numThread +""" """+Bclass+ """ 17.7.24 """ + appName + """ 
            #sudo shutdown -f # sudo should be granted """

    auth_username = 'hr'
    auth_password = 'hr'
    auth_url = 'https://openstack.tacc.chameleoncloud.org:5000'
    project_name = 'CH'
    region_name = 'RegionOne'

    provider = get_driver(Provider.OPENSTACK)
    conn = provider(auth_username,
                    auth_password,
                    ex_force_auth_url=auth_url,
                    ex_force_auth_version='2.0_password',
                    ex_tenant_name=project_name,
                    ex_force_service_region=region_name)

    print ('   ')
    print('Current VMs')
    # step-7
    instances = conn.list_nodes()
    for instance in instances:
        print("   ",instance)

    print ('   ')
    print('Creating new VM')
    # step-6
    keypair_name = 'ch-key'
    security_group_name = 'default'
    for security_group in conn.ex_list_security_groups():
        if security_group.name == security_group_name:
            security_group_obj = security_group
    image_id = 'b3bfccaa-b0d0-4c77-9a9f-c6f20c28fe6d'
    image_obj = conn.get_image(image_id)
    instance_name = ''.join(random.choice(string.lowercase) for i in range(10))
    flavor_obj = conn.ex_get_size(instanceType2run)
    newInstance = conn.create_node(name=instance_name,
                                   image=image_obj,
                                   size=flavor_obj,
                                   ex_keyname=keypair_name,
                                   ex_security_groups=[security_group_obj])

    print ('   ')
    print('Waiting for new VM Creation')
    vmCreated = 0
    while vmCreated == 0:
        sys.stdout.write('.')
        instances = conn.list_nodes()
        found = 0
        for instance in instances:
            if instance.name == instance_name:
                vmCreated =1
                break
    sys.stdout.write("   2nd wait API ")
    now = time.time()
    conn.wait_until_running([newInstance])
    now2 = time.time()
    passed = (now2 - now )
    for i in range(1,int(passed)):
        sys.stdout.write('.')


    print ('   ')
    print('Floating IP assignment')
    private_ip = 0
    while private_ip == 0:
        sys.stdout.write('.')
        instances = conn.list_nodes()
        for instance in instances:
            if instance.name == instance_name:
                if instance.private_ips[0] != None:
                    print('  Private IP found: {}'.format(instance.private_ips[0]))
                    private_ip = 1
                    break
        time.sleep(1)
    unused_floating_ip = None
    for floating_ip in conn.ex_list_floating_ips():
        if not floating_ip.node_id:
            unused_floating_ip = floating_ip
            break
    if not unused_floating_ip and len(conn.ex_list_floating_ip_pools()):
        pool = conn.ex_list_floating_ip_pools()[0]
        print('   Allocating new Floating IP from pool: {}'.format(pool))
        unused_floating_ip = pool.create_floating_ip()
    conn.ex_attach_floating_ip_to_node(newInstance, unused_floating_ip)
    print('   The IP assigned: {}'.format(unused_floating_ip.ip_address))


    print(' ')
    print('Checking BOOT')
    i = 0
    boot = 0
    while boot == 0:
        try:
            i = i + 1
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(unused_floating_ip.ip_address, username="hr", password="", timeout=1)
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
        ssh.connect(unused_floating_ip.ip_address, username="hr", password="")
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

    print ('   ')
    print('Terminating Created VM')
    conn.destroy_node(newInstance)
    notTerminated = 0
    while notTerminated == 0:
        sys.stdout.write('.')
        instances = conn.list_nodes()
        found =0
        for instance in instances:
            if instance.name == instance_name :
                found =1
        if found==0:
            notTerminated=1


def main(argv):
    chameleonInstance("bt", "3", "B")


if __name__ == "__main__":
    main(" ")


