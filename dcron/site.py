#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from threading import Thread

from flask import Flask
from gevent.pywsgi import WSGIServer

app = Flask('dcron')


@app.route('/')
def hello():
    return "Hello World!"


class WebServer:

    ws_thread = None

    def __init__(self, port):
        self.server = WSGIServer(('', port), app)

    def start(self):
        # self.ws_thread = Thread(target=self.server.start())
        # self.ws_thread.setDaemon(True)
        # self.ws_thread.start()
        self.server.start()

    def stop(self):
        # if self.ws_thread:
        #     self.server.stop()
        #     self.ws_thread.join()
        # self.ws_thread = None
        self.server.stop()

