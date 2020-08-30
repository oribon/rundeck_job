#!/usr/bin/python

# (c) 2019, Ori Braunshtein 
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import time
import json
import requests
import ast
from urlparse import urljoin
from ansible.module_utils.basic import *

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'core'}

DOCUMENTATION = """
---
module: rundeck_job

author:
    - "Ori Braunshtein"

short_description: Runs a job from a Rundeck server.
                   
description:
  - This module will run a job by its name from a Rundeck server using its REST API.

options:
  rundeck_url:
    required: true
    description:
      - The url (including port) of the Rundeck server we run the job from.
      
  rundeck_token:
    required: true unless [rundeck_user + rundeck_password] are defined
    description:
        - Token to authenticate with.

  rundeck_user:
    required: true unless rundeck_token is defined
    description:
      - Username to authenticate with to the Rundeck server.

  rundeck_user_password:
    required: true unless rundeck_token is defined
    description:
      - Password for the rundeck_user.

  job_name:
    required: true
    description:
      - Name of the job to run.

  job_options:
    required: false
    description:
      - Options for the job, must be in the form of '{"var1":"value1","var2":"value2","var3":"value3"...}'.
"""

EXAMPLES = '''

- name: I fantasized about this back in Chicago.
  hosts: localhost
  vars:
    - my_job_options: '{"var1":"value1", "var2":"value2"}'
  gather_facts: no
  tasks:
    - name: Mercy, mercy me, that Murcielago.
      rundeck_job:
        rundeck_url: "http://rundeck"
        rundeck_user: "admin"
        rundeck_user_password: "admin"
        job_name: "Test"
        job_options: '{{ my_job_options }}'

'''

class Rundeck():

  def __init__(self, rundeck_url, rundeck_token=None, rundeck_user=None, rundeck_user_password=None, api_version=18, verify=False):
    self.rundeck_url = rundeck_url
    self.token = rundeck_token
    self.rundeck_user = rundeck_user
    self.rundeck_user_password = rundeck_user_password
    self.api_version = api_version
    self.verify = verify
    self.API_URL = urljoin(rundeck_url, '/api/{}'.format(api_version))
    if (not self.token):
      self.auth_cookie = self.RundeckAuthenticate()

# Authentication function, returns cookies that sould be passed in requests
  def RundeckAuthenticate(self):
    url = urljoin(self.rundeck_url, '/j_security_check')
    post_params = {'j_username': self.rundeck_user, 'j_password': self.rundeck_user_password}
    r = requests.post(url, params=post_params, verify=self.verify, allow_redirects=True, timeout=3)
    # if we werent redirected it means the login failed
    if (len(r.history) == 1):
      raise Exception ("Error - Couldn't login to rundeck server {}, user/password incorrect".format(self.rundeck_url))
    else:
      return r.history[0].cookies['JSESSIONID']

# Generic function for api requests
  def rundeck_api_request(self, request_method, url, request_params=None):
    request_cookies = None
    if (not self.token):
      request_cookies = {'JSESSIONID': self.auth_cookie}
    request_headers = {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-Rundeck-Auth-Token': self.token
    }
    r = requests.request(request_method, url, cookies=request_cookies, headers=request_headers, json=request_params, verify=self.verify)
    try:
      return r.json()
    except Exception as E:
      return r.content
      
# generic GET request
  def rundeck_api_get(self, url, params=None):
    get_result = self.rundeck_api_request('GET', url, params)
    if ("errorCode" in get_result):
      raise Exception ("Error - {}: {}".format(get_result["errorCode"],get_result["message"]))
    else:
      return get_result

# generic POST request
  def rundeck_api_post(self, url, params=None):
    post_result = self.rundeck_api_request('POST', url, params)
    if ("errorCode" in post_result):
      raise Exception ("Error - {}: {}".format(post_result["errorCode"],post_result["message"]))
    else:
      return post_result

# lists all projects
  def list_all_projects(self):
    url = '{}/projects'.format(self.API_URL)
    all_projects = self.rundeck_api_get(url)
    return all_projects

# gets project name, returns all of it jobs
  def list_project_jobs(self, project):
    url = '{}/project/{}/jobs'.format(self.API_URL, project)
    return self.rundeck_api_get(url)

# lists all jobs from all projects
  def list_all_jobs(self):
    jobs = []
    for project in self.list_all_projects():
      jobs += self.list_project_jobs(project["name"])
    return jobs

# gets job name (optional - project name), returns job details
  def get_job_by_name(self, job_name, project=None):
    jobs = []
    returned_job = None
    if (project):
      jobs = self.list_project_jobs(project)
    else:
      jobs = self.list_all_jobs()
    for job in jobs:
      if (job["name"] == job_name):
        returned_job = job
    if not (returned_job):
      raise Exception ("Error - Job {} not found: job name incorrect".format(job_name))
    else:
      return returned_job

# runs a job by its name, returns job execution details
  def run_job_by_name(self, jobname, options=None):
    job_id_to_run = self.get_job_by_name(jobname)
    url = '{}/job/{}/run'.format(self.API_URL, job_id_to_run["id"])
    job_params = {}
    job_params["options"] = options
    job_exec = self.rundeck_api_post(url,job_params)
    return job_exec

# get execution id, returns execution details
  def get_execution_by_id(self, execid):
    url = '{}/execution/{}'.format(self.API_URL, execid)
    exec_details = self.rundeck_api_get(url)
    return exec_details

# get execution id, checks its status untill it isnt running, if it isnt succeeded raises Exception
  def get_full_execution_status(self, execid):
    exec_status = (self.get_execution_by_id(execid))["status"]
    while (exec_status == "running"):
      time.sleep(3)
      exec_status = (self.get_execution_by_id(execid))["status"]
    if not (exec_status == "succeeded"):
      raise Exception ("Error - Execution's last status is: {}, check Activity tab in the rundeck server for further details".format(exec_status))
    else:
      return 0

  def get_execution_output(self, execid):
    url = '{}/execution/{}/output?format=text'.format(self.API_URL, execid)
    exec_output = self.rundeck_api_get(url)
    return exec_output

def main():
  module = AnsibleModule(
    argument_spec = dict(
      rundeck_url = dict(required=True, type='str'),
      rundeck_user = dict(no_log=False, type='str'),
      rundeck_user_password = dict(no_log=True, type='str'),
      rundeck_token = dict(required=False, type='str'),
      job_name = dict(required=True, type='str'),
      job_options = dict(required=True)
    ),
    mutually_exclusive=[
      ['rundeck_token', 'rundeck_user'],
      ['rundeck_token', 'rundeck_user_password']
    ],
    required_together=[
      ['rundeck_user','rundeck_user_password']
    ],
    required_one_of=[
      ['rundeck_token','rundeck_user']
    ],
  )

  rundeck_url = module.params['rundeck_url']
  rundeck_token = module.params['rundeck_token']
  rundeck_user = module.params['rundeck_user']
  rundeck_user_password = module.params['rundeck_user_password']
  job_name = module.params['job_name']
  job_options = ast.literal_eval(module.params['job_options'])
  try:
    # Open rundeck session
    rd_session = Rundeck(rundeck_url, rundeck_token, rundeck_user, rundeck_user_password)
    # Execute job
    exec_job = rd_session.run_job_by_name(job_name, job_options)
    # Check execution status untill it isn't "running"
    check_job_status = rd_session.get_full_execution_status(exec_job["id"])
    # Getting execution output
    exec_output = rd_session.get_execution_output(exec_job["id"])
    # End module successfully if the execution status is "succeeded"
    if (check_job_status == 0):
      module.exit_json(changed=True, msg=exec_output)
    else:
      raise Exception ("Unidentified error happened - Check if your rundeck version supports api v18 and check Activity tab in the rundeck server for further information")

  except Exception as E:
    module.fail_json(msg=str(E))

if __name__ == "__main__":
  main()