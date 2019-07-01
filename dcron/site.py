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

import json
import logging
import pathlib

import jinja2

from aiohttp import web
from dateutil import parser, tz
import aiohttp_jinja2 as aiohttp_jinja2

from dcron.cron.cronitem import CronItem
from dcron.datagram.client import broadcast
from dcron.protocols.messages import Kill, Run, Toggle
from dcron.protocols.udpserializer import UdpSerializer
from dcron.storage import CronEncoder
from dcron.utils import get_ip


class Site(object):
    """
    Minimalistic Web UI
    """

    logger = logging.getLogger(__name__)

    root = pathlib.Path(__file__).parent

    def __init__(self, storage, udp_port, cron=None, user=None, hash_key=None):
        self.cron = cron
        self.storage = storage
        self.udp_port = udp_port
        self.user = user
        self.hash_key = hash_key
        self.app = web.Application()
        aiohttp_jinja2.setup(self.app, loader=jinja2.PackageLoader('dcron', 'templates'))
        self.app.router.add_static('/static/', path=self.root/'static', name='static')
        self.app.add_routes([web.get('/', self.get),
                             web.get('/list_nodes', self.get_nodes),
                             web.get('/cron_in_sync', self.cron_in_sync),
                             web.get('/status', self.status),
                             web.get('/list_jobs', self.get_jobs),
                             web.get('/jobs', self.jobs),
                             web.post('/add_job', self.add_job),
                             web.post('/remove_job', self.remove_job),
                             web.post('/get_job_log', self.get_job_log),
                             web.post('/kill_job', self.kill_job),
                             web.post('/run_job', self.run_job),
                             web.post('/toggle_job', self.toggle_job),
                             web.get('/export', self.export_data),
                             web.post('/import', self.import_data)])

    @aiohttp_jinja2.template('index.html')
    async def get(self, request):
        return

    @aiohttp_jinja2.template('nodestable.html')
    async def get_nodes(self, request):
        nodes = []
        for node in self.storage.cluster_state():
            node.time = parser.parse(node.time).astimezone(tz.tzlocal()).strftime('%d.%m.%Y %H:%M:%S')
            nodes.append(node)
        return dict(nodes=sorted(nodes, key=lambda n: n.ip))

    async def cron_in_sync(self, request):
        for job in self.storage.cluster_jobs:
            if job.assigned_to == get_ip():
                found = next(iter([j for j in self.cron.find_command(job.command) if j == job]), None)
                if not found:
                    return web.HTTPConflict(text="stored job {0} not matched to actual cron".format(job))
        return web.HTTPOk()

    async def status(self, request):
        return web.json_response(sorted(self.storage.cluster_state(), key=lambda n: n.ip), dumps=CronEncoder().default)

    @aiohttp_jinja2.template('jobstable.html')
    async def get_jobs(self, request):
        return dict(jobs=sorted(self.storage.cluster_jobs, key=lambda j: (j.command, j.assigned_to if j.assigned_to else '*')))

    async def jobs(self, request):
        return web.json_response(sorted(self.storage.cluster_jobs, key=lambda j: (j.command, j.assigned_to if j.assigned_to else '*')), dumps=CronEncoder().default)

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

        cron_item = self.generate_cron_item(data)

        if cron_item not in self.storage.cluster_jobs:
            raise web.HTTPConflict(text='job not found on cluster')

        self.logger.debug("broadcasting kill result")

        broadcast(self.udp_port, UdpSerializer.dump(Kill(cron_item), self.hash_key))

        raise web.HTTPAccepted()

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

        cron_item = self.generate_cron_item(data)

        if cron_item not in self.storage.cluster_jobs:
            raise web.HTTPConflict(text='job not found on cluster')

        self.logger.debug("broadcasting run result")

        broadcast(self.udp_port, UdpSerializer.dump(Run(cron_item), self.hash_key))

        raise web.HTTPAccepted()

    async def toggle_job(self, request):
        data = await request.post()

        self.logger.debug("received toggle request {0}".format(data))

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dom' not in data or \
                'month' not in data or \
                'dow' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        cron_item = self.generate_cron_item(data)

        if cron_item not in self.storage.cluster_jobs:
            raise web.HTTPConflict(text='job not found on cluster')

        self.logger.debug("broadcasting run result")

        broadcast(self.udp_port, UdpSerializer.dump(Toggle(cron_item), self.hash_key))

        raise web.HTTPAccepted()

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

        cron_item = self.generate_cron_item(data)

        if 'disabled' in data:
            cron_item.enable(False)

        if cron_item in self.storage.cluster_jobs:
            raise web.HTTPConflict(text='job already exists')

        self.logger.debug("broadcasting add result")

        broadcast(self.udp_port, UdpSerializer.dump(cron_item, self.hash_key))

        raise web.HTTPCreated()

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

        cron_item = self.generate_cron_item(data, removable=True)

        if cron_item not in self.storage.cluster_jobs:
            raise web.HTTPConflict(text='job not found')

        self.logger.debug("broadcasting remove result")

        broadcast(self.udp_port, UdpSerializer.dump(cron_item, self.hash_key))

        raise web.HTTPAccepted()

    async def export_data(self, request):
        self.logger.debug("building export data")

        result = []
        for job in self.storage.cluster_jobs:
            result.append(
                {
                    'pattern': "{0} {1} {2} {3} {4}".format(job.minute, job.hour, job.dom, job.month, job.dow),
                    'command': job.command,
                    'enabled': job.enabled
                }
            )

        self.logger.debug("returning export {0}".format(result))

        return web.json_response(result)

    async def import_data(self, request):
        data = await request.post()

        if 'payload' not in data:
            return web.Response(status=500, text='no payload found')

        self.logger.debug("received import request {0}".format(data['payload']))

        try:
            imports = json.loads(data['payload'])
            for line in imports:
                if 'pattern' in line and 'command' in line and 'enabled' in line:
                    cron_item = CronItem(command=line['command'])
                    cron_item.set_all(line['pattern'])
                    cron_item.enable(line['enabled'])
                    self.logger.debug("received new job from import {0}, broadcasting it.".format(cron_item))
                    broadcast(self.udp_port, UdpSerializer.dump(cron_item, self.hash_key))
                else:
                    self.logger.error("import element invalid: {0}".format(line))
            return web.HTTPOk()
        except ValueError as e:
            self.logger.error(e)
            return web.HTTPClientError(text='invalid json received')

    def generate_cron_item(self, data, removable=False):

        cron_item = CronItem(command=data['command'])
        if self.user:
            cron_item.user = self.user
        else:
            cron_item.user = 'root'
        cron_item.remove = removable

        pattern = '{0} {1} {2} {3} {4}'.format(data['minute'], data['hour'], data['dom'], data['month'], data['dow'])

        self.logger.debug("adding pattern {0} to job".format(pattern))

        cron_item.set_all(pattern)

        return cron_item
