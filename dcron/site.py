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

import logging
import pathlib

import jinja2

from aiohttp import web
import aiohttp_jinja2 as aiohttp_jinja2

from dcron.cron.cronitem import CronItem
from dcron.datagram.client import broadcast
from dcron.protocols.messages import Kill, Run
from dcron.protocols.udpserializer import UdpSerializer


class Site(object):
    """
    Minimalistic Web UI
    """

    logger = logging.getLogger(__name__)

    root = pathlib.Path(__file__).parent

    def __init__(self, storage, udp_port):
        self.storage = storage
        self.udp_port = udp_port
        self.app = web.Application()
        aiohttp_jinja2.setup(self.app, loader=jinja2.PackageLoader('dcron', 'templates'))
        self.app.router.add_static('/static/', path=self.root/'static', name='static')
        self.app.add_routes([web.get('/', self.get)])
        self.app.add_routes([web.get('/list_nodes', self.get_nodes)])
        self.app.add_routes([web.get('/list_jobs', self.get_jobs)])
        self.app.add_routes([web.post('/add_job', self.add_job)])
        self.app.add_routes([web.post('/remove_job', self.remove_job)])
        self.app.add_routes([web.post('/get_job_log', self.get_job_log)])
        self.app.add_routes([web.post('/kill_job', self.kill_job)])
        self.app.add_routes([web.post('/run_job', self.run_job)])

    @aiohttp_jinja2.template('index.html')
    async def get(self, request):
        return

    @aiohttp_jinja2.template('nodestable.html')
    async def get_nodes(self, request):
        return dict(nodes=sorted(self.storage.cluster_state(), key=lambda n: n.ip))

    @aiohttp_jinja2.template('jobstable.html')
    async def get_jobs(self, request):
        return dict(jobs=sorted(self.storage.cluster_jobs, key=lambda j: j.command))

    @aiohttp_jinja2.template('joblogs.html')
    async def get_job_log(self, request):
        data = await request.post()

        self.logger.debug("received log request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        cron_item = self.generate_cron_item(data)

        self.logger.debug("returning log result")

        for job in self.storage.cluster_jobs:
            if job == cron_item:
                return dict(job=job)
        return dict(job=cron_item)

    async def kill_job(self, request):
        data = await request.post()

        self.logger.debug("received kill request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        self.logger.debug("broadcasting kill result")

        broadcast(self.udp_port, UdpSerializer.dump(Kill(self.generate_cron_item(data))))

        raise web.HTTPFound('/')

    async def run_job(self, request):
        data = await request.post()

        self.logger.debug("received run request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        self.logger.debug("broadcasting run result")

        broadcast(self.udp_port, UdpSerializer.dump(Run(self.generate_cron_item(data))))

        raise web.HTTPFound('/')

    async def add_job(self, request):
        data = await request.post()

        self.logger.debug("received add request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted via form')

        self.logger.debug("broadcasting add result")

        broadcast(self.udp_port, UdpSerializer.dump(self.generate_cron_item(data)))

        raise web.HTTPFound('/')

    async def remove_job(self, request):
        data = await request.post()

        self.logger.debug("received remove request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        self.logger.debug("broadcasting remove result")

        broadcast(self.udp_port, UdpSerializer.dump(self.generate_cron_item(data, removable=True)))

        raise web.HTTPFound('/')

    def generate_cron_item(self, data, removable=False):

        cron_item = CronItem(command=data['command'])
        cron_item.remove = removable

        pattern = '{0} {1} {2} {3} {4}'.format(data['minute'], data['hour'], data['dom'], data['month'], data['dow'])

        self.logger.debug("adding pattern {0} to job".format(pattern))

        cron_item.set_all(pattern)

        return cron_item
