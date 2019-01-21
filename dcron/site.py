#!/usr/bin/env python
# -*- coding: utf-8 -*-#

# MIT License
#
# Copyright (c) 2019 Pim Witlox
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pathlib

import jinja2

from aiohttp import web
import aiohttp_jinja2 as aiohttp_jinja2

from dcron.datagram.client import client
from dcron.protocols.cronjob import CronJob


class Site:

    root = pathlib.Path(__file__).parent

    def __init__(self, storage, udp_port):
        self.storage = storage
        self.udp_port = udp_port
        self.app = web.Application()
        aiohttp_jinja2.setup(self.app, loader=jinja2.PackageLoader('dcron', 'templates'))
        self.app.router.add_static('/static/', path=self.root/'static', name='static')
        self.app.add_routes([web.get('/', self.get)])
        self.app.add_routes([web.post('/job', self.add_job)])
        self.app.add_routes([web.delete('/job', self.delete_job)])

    def broadcast(self, packets):
        for packet in packets:
            client(self.udp_port, packet)

    @aiohttp_jinja2.template('index.html')
    async def get(self, request):
        return dict(nodes=self.storage.cluster_state(), jobs=self.storage.cron_jobs())

    async def add_job(self, request):
        pass

    async def delete_job(self, request):
        pass
