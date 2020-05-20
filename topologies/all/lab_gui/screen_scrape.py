from bs4 import BeautifulSoup
import requests
from ruamel.yaml import YAML
import sys
import os

def delete_old_file():
    if os.path.exists('lab_credentials.yaml'):
        os.remove('lab_credentials.yaml')

def create_credential_file():
    response = requests.get(url='http://54.176.90.209', verify=False)

    html_soup = BeautifulSoup(response.text, 'html.parser')

    user_data = html_soup.find('div', class_='container-fluid')

    credential_info = {}

    replace_tags = ['<tr>', '</tr>', '<td>', '</td>']

    for line in str(user_data).splitlines():
        if 'Lab Frontend' in line:
            for tag in replace_tags:
                line = line.replace(tag, '')
            line_split = line.split(' ')
            credential_info['lab_frontend'] = {'username': line_split[2], 'password': line_split[3]}
        elif 'CVP' in line:
            for tag in replace_tags:
                line = line.replace(tag, '')
                line_split = line.split(' ')
                credential_info['cvp'] = {'username': line_split[1], 'password': line_split[2]}
                credential_info['veos_instances'] = {'username': line_split[1], 'password': line_split[2]}
        elif 'IPAM' in line:
            for tag in replace_tags:
                line = line.replace(tag, '')
                line_split = line.split(' ')
                credential_info['ipam'] = {'username': line_split[1], 'password': line_split[2]}
        elif 'Lab VM SSH' in line:
            for tag in replace_tags:
                line = line.replace(tag, '')
                line_split = line.split(' ')
                credential_info['lab_vm'] = {'username': line_split[1], 'password': line_split[2]}

    dump_file = open('lab_credentials.yaml', 'w')
    YAML().dump(credential_info, dump_file)



def main():
    
    delete_old_file()
    create_credential_file()


if __name__ == '__main__':
    main()