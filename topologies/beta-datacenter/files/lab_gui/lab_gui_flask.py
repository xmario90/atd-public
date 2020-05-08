#!/usr/bin/python3
import os
import sys
import signal
import re
import json
from ruamel.yaml import YAML
from itertools import zip_longest
from flask import Flask, jsonify, request, render_template
from flask_restful import Resource, Api
from flask_bootstrap import Bootstrap
from flask_cors import CORS



######################################
############  Server Info  ###########
######################################

def create_app(menu_dict):


  ######################################
  ############## API Data  #############
  ######################################

  class RunCommand(Resource):
    def post(self):
      input_var = json.loads(request.data)
      print('You sent {0}'.format(input_var))
      return str(input_var['selectedLab'])

  app = Flask(__name__)
  Bootstrap(app)
  CORS(app)

  @app.route('/labs')
  def labs():
    return render_template('labs.html',
                            title="Arista Test Drive Lab Deployment Page",
                            description="Main Page for Deploying ATD Labs.", vars=menu_dict)



  ##### API Calls #####
  api = Api(app)   
  api.add_resource(RunCommand, '/runscript')               
  
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

if __name__ == '__main__':
  menu_dict = get_menus()
  create_app(menu_dict).run(debug=True)