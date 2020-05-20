#!/usr/bin/python3

# TODO: Update file structure in production to match the topo_build.yaml topology type and move these files to 'all'

import os
from ruamel.yaml import YAML
import jinja2
import tornado.web
import requests

class FrontEnd(tornado.web.RequestHandler):
    def _get_menus(self):
      menu_list = [x for x in os.listdir('../menus')]
      menus_dict = {}
      for menu_item in os.listdir('../menus'):
        if menu_item != 'default.yaml':
          menus_dict[menu_item.replace('.yaml', '')] = []
          menu_file = open('../menus/{0}'.format(menu_item))
          menu_items = YAML().load(menu_file)
          for lab_item in menu_items['lab_list']:
            menus_dict[menu_item.replace('.yaml', '')].append(lab_item)

      return menus_dict

    def _get_access_info(self):
      access_file = open('/etc/ACCESS_INFO.yaml', 'r')
      access_info = YAML().load(access_file)
      access_file.close()
      return access_info

    def _get_ip_address(self):
      url = 'http://ipecho.net/plain'
      ip_address = requests.get(url=url, verify=False)
      return ip_address.text

    def _render_template(self,menu_data,access_info,ip_address):
      for item in access_info:
        print(item)
      with open('./templates/labs_socket_tornado.html', 'r') as file:
          template = file.read()
          env = jinja2.Environment(
              loader=jinja2.BaseLoader(),
              trim_blocks=True,
              lstrip_blocks=True,
              extensions=['jinja2.ext.do'])
          templategen = env.from_string(template)
          if templategen:
              web_data = templategen.render({'data': menu_data, 'access_info': access_info, 'ip_address': ip_address})
              return(web_data)
          return('<html>Error rendering template</html>')


    def get(self):
      menu_dict = self._get_menus()
      access_info = self._get_access_info()
      ip_address = self._get_ip_address()
      self.write(self._render_template(menu_dict,access_info,ip_address))