
"""
Kepler Web-View Run

"""

import json
import requests
from requests.auth import HTTPBasicAuth

class Run:

    def __init__(self, url='https://localhost:9443/kepler', username=None, 
        password=None, response=None, id=None, fields=None, debug=False):

        self._outputs = None
        self._password = password
        self._success = False
        self._url = url
        self._username = username
        self._debug = debug

        if fields is not None:
            self._fields = fields
            #print(fields)
        else:
            self._fields = {}

        if id is not None:
            self._fields['id'] = id

        if response is not None:
            
            #print("DEBUG: {}".format(response.text))

            if self._debug:
                print("DEBUG: response: {}".format(response.text))
    
            if response.text == 'Unauthorized':
                raise Exception('Wrong username or password.')
            else:
                response_json = response.json()

                if response.status_code != requests.codes.ok:
                    if 'error' in response_json:
                        raise Exception(response_json['error'])
                else:
                    self._success = True
    
                    if 'id' in response_json:
                        self._fields['id'] = response_json['id']
    
                    if 'responses' in response_json:
                        self._outputs = response_json['responses']

    def __str__(self):
        return str(self._fields)

    # get error message if failure, otherwise None
    def error(self):
        return self._get_field_in_status('runError', optional=True)

    # wait until run finished
    # returns True if success, False otherwise
    def finish(self):
        return self._success

    # get any keys_values for the run.
    def keys_values(self):

        response_json = self._make_request("{}/runs/{}?keysValues=true"
            .format(self._url, self._fields['id']))

        if 'keysValues' not in response_json:
            raise Exception('Missing keysValues in response')

        return response_json['keysValues']

    # get the run id. returns None if provenance not enabled.
    def id(self):
        return self._fields['id']
    
    # get if the run is still running.
    def is_running(self):
        return self._get_field_in_status('status') == 'running'

    # get the run status
    def status(self, outputs=False):
        
        response_json = self._make_request("{}/runs/{}?outputs={}"
            .format(self._url, self._fields['id'], str(outputs).lower()))

        for k,v in response_json.items():
            if k == 'responses':
                self._outputs = v
            else:
                self._fields[k] = v

        return response_json
   
    # get the output
    def outputs(self):
        if self._outputs is not None:
            return self._outputs
        self.status(outputs=True)
        return self._outputs

    # TODO
    #def output(self, name):
    #    pass

    # get any parameters values for the run.
    def parameters(self, all=False):

        response_json = self._make_request("{}/runs/{}?parametersValues=true"
            .format(self._url, self._fields['id']))

        if 'parametersValues' not in response_json:
            raise Exception('Missing parametersValues in response')

        kv = { };
        for k,v in response_json['parametersValues'].items():
            if all or k.count('.') == 1:
                kv[k[1:]] = v

        return kv

    # get the PROV trace of the run
    def prov(self, file_name=None, prov_format='json'):
     
        if file_name:
            return self._make_request_to_binary_file(
                "{}/runs/{}/prov?provFormat={}".format(self._url, self._fields['id'], prov_format),
                file_name)

        response_json = self._make_request("{}/runs/{}?prov=true&provFormat={}"
            .format(self._url, self._fields['id'], prov_format))

        if 'prov' not in response_json:
            raise Exception('Missing prov in response')

        if prov_format == 'json':
            return json.loads(response_json['prov'])

        return response_json['prov']

    # get an research object bundle
    def ro_bundle(self, file_name="ro_bundle.zip"):
        return self._make_request_to_binary_file("{}/runs/{}/roBundle".format(self._url, self._fields['id']), file_name)

    # get the workflow screenshot and save to a file.
    def screenshot(self, file_name='workflow.png'):
        return self._make_request_to_binary_file(
            "{}/runs/{}/screenshot".format(self._url, self._fields['id']), file_name)

    # get the start time of the workflow run.
    def start_time(self):
        return self._get_field_in_status('start')

    # get the run type, e.g., complete, running, error
    def type(self):
        return self._get_field_in_status('status')

    # get the workflow kar and save to a file.
    def workflow(self, file_name='workflow.kar'):
        return self._make_request_to_binary_file(
            "{}/runs/{}/workflow".format(self._url, self._fields['id']), file_name)

    # get the workflow name
    def workflow_name(self):
        return self._get_field_in_status('workflowName')

    ### private methods

    # get a field in the status dictionary
    def _get_field_in_status(self, field_name, optional=False):
        if field_name not in self._fields:
            self.status()
    
        if field_name not in self._fields:
            if optional:
                return None
            raise Exception('No such field: ' + field_name)

        return self._fields[field_name]

    # make a request and check response for errors
    def _make_request(self, url):

        if 'id' not in self._fields:
            raise Exception('Must specify run id.')

        response = requests.get(url,
            auth=HTTPBasicAuth(self._username, self._password),
            #FIXME verify
            verify=False)
      
        if self._debug:
            print("DEBUG: response: {}".format(response.text))
    
        if response.text == 'Unauthorized':
            raise Exception(response.text)

        if 'Content-Type' in response.headers:
            if response.headers['Content-Type'] == 'application/json':
                response_json = response.json()
                if 'error' in response_json:
                    raise Exception(response_json['error'])
                return response_json
            elif response.headers['Content-Type'] == 'application/xml':
                return response.text
       
        return response.content
    
    # make a request that returns a binary file and write file to file_name
    def _make_request_to_binary_file(self, url, file_name):

        if file_name is None:
            raise Exception('Must specify destination file name.')

        data = self._make_request(url)
        
        with open(file_name, 'wb') as f:
            f.write(data)

        return file_name
