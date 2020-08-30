# rundeck_job.py
- This is an Ansible module I wrote that runs a Rundeck job by its name from a Rundeck server using its REST API

## Options
- rundeck_url:
    - required: true
    - The url (including port) of the Rundeck server we run the job from.

- rundeck_token:
    - required: true unless [rundeck_user + rundeck_password] are defined
    - Token to authenticate with

- rundeck_user:
    - required: true unless rundeck_token is defined
    - Username to authenticate with to the Rundeck server.

- rundeck_user_password:
    - required: true unless rundeck_token is defined
    - Password for the rundeck_user.

- job_name:
    - required: true
    - Name of the job to run.

- job_options:
    - required: false
    - Options for the job, **must be in the form of '{"var1":"value1","var2":"value2","var3":"value3"...}'**.

## Examples
```
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
        
- name: example play
  hosts: localhost
  vars:
    - my_job_options: '{"var1":"value1", "var2":"value2"}'
  gather_facts: no
  tasks:
    - name: running job Test
      rundeck_job:
        rundeck_url: "http://rundeck"
        rundeck_token: "zPXSRUeVQn7GsZsfLWyJDIyaOOIKz0nq"
        job_name: "Test"
        job_options: '{{ my_job_options }}'
```