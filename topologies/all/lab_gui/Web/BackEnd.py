#!/usr/bin/python3

# TODO: Update file structure in production to match the topo_build.yaml topology type and move these files to 'all'

import json
import tornado.websocket
from datetime import timedelta, datetime, timezone, date
from ruamel.yaml import YAML
from ConfigureTopology.ConfigureTopology import ConfigureTopology
import syslog

DEBUG = False

class BackEnd(tornado.websocket.WebSocketHandler):
    connections = set()
    status = ''

    def open(self):
        self.connections.add(self)
        self.send_to_syslog('OK', 'Connection opened from {0}'.format(self.request.remote_ip))
        self.schedule_update()

    def close(self):
        self.connections.remove(self)
        self.send_to_syslog('INFO', 'Connection closed from {0}'.format(self.request.remote_ip))

    def on_message(self, message):
        data = json.loads(message)
        self.send_to_syslog("INFO", 'Received message {0} in socket.'.format(message))
        if data['type'] == 'openMessage':
            pass
        elif data['type'] == 'serverData':
            pass
        elif data['type'] == 'clientData':
            ConfigureTopology(selected_menu=data['selectedMenu'],selected_lab=data['selectedLab'],socket=self)


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

    def schedule_update(self):
        self.timeout = tornado.ioloop.IOLoop.instance().add_timeout(timedelta(seconds=60),self.keep_alive)
          
    def keep_alive(self):
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

    def send_to_socket(self,message):
        self.status = message
        self.write_message(json.dumps({
            'type': 'serverData',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': message
        }))

