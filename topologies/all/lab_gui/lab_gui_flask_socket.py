#!/usr/bin/python3
import os
import sys
import signal
import re
import json
from ruamel.yaml import YAML
from itertools import zip_longest
from flask import Flask, jsonify, request, render_template
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO, send, emit



######################################
############  Server Info  ###########
######################################

def create_app(menu_dict):

  app = Flask(__name__)
  app.config['SECRET_KEY'] = 'arista'
  Bootstrap(app)

  @app.route('/labs')
  def labs():
    return render_template('labs_socket.html',
                            title="Arista Test Drive Lab Deployment Page",
                            description="Main Page for Deploying ATD Labs.", vars=menu_dict)

  return app

def get_menus():
  menu_list = [x for x in os.listdir('../menus')]

  menus_dict = {}
  for menu_item in os.listdir('../menus'):
    if menu_item != 'default.yaml':
      print("Adding menu for {0}".format(menu_item))
      menus_dict[menu_item.replace('.yaml', '')] = []
      menu_file = open('../menus/{0}'.format(menu_item))
      menu_items = YAML().load(menu_file)
      for lab_item in menu_items['lab_list']:
        menus_dict[menu_item.replace('.yaml', '')].append(lab_item)
  return menus_dict

def create_socket(app):
  socketio = SocketIO(app)

  @socketio.on('message')
  def handle_message(message):
    print(message)
    socketio.emit('sendUpdate', message['selectedLab'])


  socketio.run(app)

if __name__ == '__main__':
  menu_dict = get_menus()
  app = create_app(menu_dict)
  create_socket(app)