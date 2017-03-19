"""
Based on code written by sammachin.

See https://github.com/sammachin/AlexaCHIP for the original code

"""


import cherrypy
import os
from cherrypy.process import servers
import requests
import json
import threading
import urllib

import helper

class Start(object):
    def __init__(self, config):
        self.config = config

    def index(self):
        sd = json.dumps({
            "alexa:all": {
                "productID": self.config['ProductID'],
                "productInstanceAttributes": {
                    "deviceSerialNumber": "632c65d183f6453cb3a4d94230bdac7d"
                }
            }
        })
        callback = cherrypy.url() + "code"
        payload = {
            "client_id": self.config['Client_ID'],
            "scope": "alexa:all",
            "scope_data": sd,
            "response_type": "code",
            "redirect_uri": callback
        }
        req = requests.Request('GET', "https://www.amazon.com/ap/oa", params=payload)
        p = req.prepare()
        raise cherrypy.HTTPRedirect(p.url)

    def code(self, var=None, **params):
        code = urllib.quote(cherrypy.request.params['code'])
        callback = cherrypy.url()
        payload = {
            "client_id": self.config['Client_ID'],
            "client_secret": self.config['Client_Secret'],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": callback
        }
        url = "https://api.amazon.com/auth/o2/token"
        r = requests.post(url, data=payload)
        resp = r.json()

        self.config['refresh_token'] = resp['refresh_token']
        helper.write_dict('config.dict',self.config)

        threading.Timer(1, lambda: cherrypy.engine.exit()).start()

        return "Authentication successful! Please return to the program."

    index.exposed = True
    code.exposed = True


def get_authorization():
    # Load configuration dictionary
    config = helper.read_dict('config.dict')

    cherrypy.config.update({'server.socket_host': '0.0.0.0', })
    cherrypy.config.update({'server.socket_port': int(os.environ.get('PORT', '5000')), })
    cherrypy.quickstart(Start(config))
