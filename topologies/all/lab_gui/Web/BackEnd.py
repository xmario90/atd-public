#!/usr/bin/python3

# TODO: Update file structure in production to match the topo_build.yaml topology type and move these files to 'all'

import json
import tornado.websocket
from datetime import timedelta, datetime, timezone, date
from ruamel.yaml import YAML
import getopt
import sys
from rcvpapi.rcvpapi import *
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import syslog
import time
import os

DEBUG = False

class BackEnd(tornado.websocket.WebSocketHandler):
    connections = set()
    status = ''
    
    def open(self):
        self.connections.add(self)
        self.send_to_syslog('OK', 'Connection opened from {0}'.format(self.request.remote_ip))
        self.schedule_update()

    def on_message(self, message):
        data = json.loads(message)
        if data['type'] == 'openMessage':
            pass
        elif data['type'] == 'clientData':
            self.deploy_lab(data['selectedMenu'],data['selectedLab'])
        elif data['type'] == 'getStatus':
            self.send_status()

    def send_status(self):
        self.write_message(json.dumps({
            'type': 'serverData',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': self.status
        }))


    def schedule_update(self):
        self.timeout = tornado.ioloop.IOLoop.instance().add_timeout(timedelta(seconds=60),self.keepalive)
          
    def keepalive(self):
        try:
            self.write_message(json.dumps({
                'type': 'keepalive',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data': 'ping'
            }))
        finally:
            self.schedule_update()

    def on_close(self):
        tornado.ioloop.IOLoop.instance().remove_timeout(self.timeout)
  
    def check_origin(self, origin):
      return True

    def connect_to_cvp(self,access_info):
            # Adding new connection to CVP via rcvpapi
            cvp_clnt = ''
            for c_login in access_info['login_info']['cvp']['shell']:
                if c_login['user'] == 'arista':
                    while not cvp_clnt:
                        try:
                            cvp_clnt = CVPCON(access_info['nodes']['cvp'][0]['internal_ip'],c_login['user'],c_login['pw'])
                            self.send_to_syslog("OK","Connected to CVP at {0}".format(access_info['nodes']['cvp'][0]['internal_ip']))
                            return cvp_clnt
                        except:
                            self.send_to_syslog("ERROR", "CVP is currently unavailable....Retrying in 30 seconds.")
                            time.sleep(30)

    def remove_configlets(self,device,lab_configlets):
        """
        Removes all configlets except the ones defined as 'base'
        Define base configlets that are to be untouched
        """
        base_configlets = ['ATD-INFRA']
        
        configlets_to_remove = []
        configlets_to_remain = base_configlets

        configlets = self.client.getConfigletsByNetElementId(device)
        for configlet in configlets['configletList']:
            if configlet['name'] in base_configlets:
                configlets_to_remain.append(configlet['name'])
                self.send_to_syslog("INFO", "Configlet {0} is part of the base on {1} - Configlet will remain.".format(configlet['name'], device.hostname))
            elif configlet['name'] not in lab_configlets:
                configlets_to_remove.append(configlet['name'])
                self.send_to_syslog("INFO", "Configlet {0} not part of lab configlets on {1} - Removing from device".format(configlet['name'], device.hostname))
            else:
                pass
        if len(configlets_to_remain) > 0:
            device.removeConfiglets(self.client,configlets_to_remove)
            self.client.addDeviceConfiglets(device, configlets_to_remain)
            self.client.applyConfiglets(device)
        else:
            pass

    def get_device_info(self):
        eos_devices = []
        for dev in self.client.inventory:
            tmp_eos = self.client.inventory[dev]
            tmp_eos_sw = CVPSWITCH(dev, tmp_eos['ipAddress'])
            tmp_eos_sw.updateDevice(self.client)
            eos_devices.append(tmp_eos_sw)
        return(eos_devices)


    def update_topology(self,configlets):
        # Get all the devices in CVP
        devices = self.get_device_info()
        # Loop through all devices
        
        for device in devices:
            # Get the actual name of the device
            device_name = device.hostname
            
            # Define a list of configlets built off of the lab yaml file
            lab_configlets = []
            for configlet_name in configlets[self.selected_lab][device_name]:
                lab_configlets.append(configlet_name)

            # Remove unnecessary configlets
            self.remove_configlets(device, lab_configlets)

            # Apply the configlets to the device
            self.client.addDeviceConfiglets(device, lab_configlets)
            self.client.applyConfiglets(device)

        # Perform a single Save Topology by default
        self.client.saveTopology()

    def send_to_syslog(self,mstat,mtype):
        """
        Function to send output from service file to Syslog
        Parameters:
        mstat = Message Status, ie "OK", "INFO" (required)
        mtype = Message to be sent/displayed (required)
        """
        mmes = "\t" + mtype
        syslog.syslog("[{0}] {1}".format(mstat,mmes.expandtabs(7 - len(mstat))))
        if DEBUG:
            print("[{0}] {1}".format(mstat,mmes.expandtabs(7 - len(mstat))))


    def push_bare_config(self,veos_host, veos_ip, veos_config):
        """
        Pushes a bare config to the EOS device.
        """
        # Write config to tmp file
        device_config = "/tmp/" + veos_host + ".cfg"
        with open(device_config,"a") as tmp_config:
            tmp_config.write(veos_config)

        DEVREBOOT = False
        veos_ssh = paramiko.SSHClient()
        veos_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        veos_ssh.connect(hostname=veos_ip, username="root", password="", port="50001")
        scp = SCPClient(veos_ssh.get_transport())
        scp.put(device_config,remote_path="/mnt/flash/startup-config")
        scp.close()
        veos_ssh.exec_command('FastCli -c "{0}"'.format(cp_start_run))
        veos_ssh.exec_command('FastCli -c "{0}"'.format(cp_run_start))
        stdin, stdout, stderr = veos_ssh.exec_command('FastCli -c "{0}"'.format(ztp_cmds))
        ztp_out = stdout.readlines()
        if 'Active' in ztp_out[0]:
            DEVREBOOT = True
            self.send_to_syslog("INFO", "Rebooting {0}...This will take a couple minutes to come back up".format(veos_host))
            #veos_ssh.exec_command("/sbin/reboot -f > /dev/null 2>&1 &")
            veos_ssh.exec_command('FastCli -c "{0}"'.format(ztp_cancel))
        veos_ssh.close()
        return(DEVREBOOT)

    def send_to_socket(self,message):
        self.status = message
        self.write_message(json.dumps({
            'type': 'serverData',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': message
        }))

    def deploy_lab(self,selected_menu,selected_lab):

        # Check for additional commands in lab yaml file
        lab_file = open('/home/arista/menus/{0}'.format(selected_menu + '.yaml'))
        lab_info = YAML().load(lab_file)
        lab_file.close()

        additional_commands = []
        if 'additional_commands' in lab_info['lab_list'][selected_lab]:
            additional_commands = lab_info['lab_list'][selected_lab]['additional_commands']

        # Get access info for the topology
        f = open('/etc/ACCESS_INFO.yaml')
        access_info = YAML().load(f)
        f.close()

        # List of configlets
        lab_configlets = lab_info['labconfiglets']

        # Send message that deployment is beginning
        self.send_to_socket("Starting deployment for {0} - {1} lab...".format(selected_menu,selected_lab))

        # Adding new connection to CVP via rcvpapi
        cvp_clnt = ''
        for c_login in access_info['login_info']['cvp']['shell']:
            if c_login['user'] == 'arista':
                while not cvp_clnt:
                    try:
                        cvp_clnt = CVPCON(access_info['nodes']['cvp'][0]['internal_ip'],c_login['user'],c_login['pw'])
                        self.send_to_syslog("OK","Connected to CVP at {0}".format(access_info['nodes']['cvp'][0]['internal_ip']))

                    except:
                        self.send_to_syslog("ERROR", "CVP is currently unavailable....Retrying in 30 seconds.")
                        self.send_to_socket("CVP is currently unavailable....Retrying in 30 seconds.")
                        time.sleep(30)

        # Make sure option chosen is valid, then configure the topology
        self.send_to_socket("Deploying configlets for {0} - {1} lab...".format(selected_menu,selected_lab))
        self.send_to_syslog("INFO", "Setting {0} topology to {1} setup".format(access_info['topology'], selected_lab))
        self.update_topology(cvp_clnt, selected_lab, lab_configlets)
        
        # Execute all tasks generated from reset_devices()
        self.send_to_socket("Creating Change Control for for {0} - {1} lab...".format(selected_menu,selected_lab))
        cvp_clnt.getAllTasks("pending")
        tasks_to_check = cvp_clnt.tasks['pending']
        cvp_clnt.execAllTasks("pending")
        self.send_to_syslog("OK", 'Completed setting devices to topology: {}'.format(selected_lab))

        self.send_to_socket("Executing change control for {0} - {1} lab. Please wait for tasks to finish...".format(selected_menu,selected_lab))
        all_tasks_completed = False
        while not all_tasks_completed:
            tasks_running = []
            for task in tasks_to_check:
                if cvp_clnt.getTaskStatus(task['workOrderId'])['taskStatus'] != 'Completed':
                    tasks_running.append(task)
                elif cvp_clnt.getTaskStatus(task['workOrderId'])['taskStatus'] == 'Failed':
                    self.send_to_socket('Task {0} failed. Please check CVP for more information'.format(task['workOrderId']))
                else:
                    pass

            if len(tasks_running) == 0:
                
                self.send_to_socket("Tasks finished. Finalizing deployment for {0} - {1} lab...".format(selected_menu,selected_lab))

                # Execute additional commands if there are any for the lab
                for command in additional_commands:
                    os.system(command)
                    
                self.send_to_socket("Deployment for {0} - {1} lab is complete.".format(selected_menu,selected_lab))
                all_tasks_completed = True
            else:
                self.send_to_socket("{0}/{1} tasks completed. Please wait...".format(str(len(tasks_to_check) - len(tasks_running)), len(tasks_to_check)))
            
