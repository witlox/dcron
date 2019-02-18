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
import pathlib

import jinja2

from aiohttp import web
import aiohttp_jinja2 as aiohttp_jinja2

from dcron.datagram.client import client
from dcron.protocols.cronjob import CronJob, RemoveCronJob


class Site:

    root = pathlib.Path(__file__).parent

    def __init__(self, storage, udp_port):
        self.storage = storage
        self.udp_port = udp_port
        self.app = web.Application()
        aiohttp_jinja2.setup(self.app, loader=jinja2.PackageLoader('dcron', 'templates'))
        self.app.router.add_static('/static/', path=self.root/'static', name='static')
        self.app.add_routes([web.get('/', self.get)])
        self.app.add_routes([web.get('/nodes', self.get_nodes)])
        self.app.add_routes([web.get('/jobs', self.get_jobs)])
        self.app.add_routes([web.post('/joblog', self.get_job_log)])
        self.app.add_routes([web.post('/job', self.add_job)])
        self.app.add_routes([web.post('/remove_job', self.remove_job)])

    def broadcast(self, packets):
        for packet in packets:
            client(self.udp_port, packet)

    @aiohttp_jinja2.template('index.html')
    async def get(self, request):
        return

    @aiohttp_jinja2.template('nodestable.html')
    async def get_nodes(self, request):
        return dict(nodes=self.storage.cluster_state())

    @aiohttp_jinja2.template('jobstable.html')
    async def get_jobs(self, request):
        return dict(jobs=self.storage.cron_jobs())

    @aiohttp_jinja2.template('joblogs.html')
    async def get_job_log(self, request):
        data = await request.post()

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dayofmonth' not in data or \
                'month' not in data or \
                'dayofweek' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        minute = None
        hour = None
        day_of_month = None
        month = None
        day_of_week = None

        if data['minute'] != 'None':
            minute = int(data['minute'])
        if data['hour'] != 'None':
            minute = int(data['hour'])
        if data['dayofmonth'] != 'None':
            minute = int(data['dayofmonth'])
        if data['month'] != 'None':
            minute = int(data['month'])
        if data['dayofweek'] != 'None':
            minute = int(data['dayofweek'])

        cron_job = CronJob(minute, hour, day_of_month, month, day_of_week, data['command'])

        for job in self.storage.cron_jobs():
            if job == cron_job:
                return dict(job=job)
        return cron_job

    async def add_job(self, request):
        data = await request.post()

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dayofmonth' not in data or \
                'month' not in data or \
                'dayofweek' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted via form')

        new_job = CronJob(command=data['command'])
        if not data['minute'] == '*':
            new_job.minute = int(data['minute'])
        if not data['hour'] == '*':
            new_job.hour = int(data['hour'])
        if not data['dayofmonth'] == '*':
            new_job.day_of_month = int(data['dayofmonth'])
        if not data['month'] == '*':
            new_job.month = int(data['month'])
        if not data['dayofweek'] == '*':
            new_job.day_of_week = int(data['dayofweek'])
        self.broadcast(new_job.dump())

        raise web.HTTPFound('/')

    async def remove_job(self, request):
        data = await request.post()

        if 'command' not in data or \
                'minute' not in data or \
                'hour' not in data or \
                'dayofmonth' not in data or \
                'month' not in data or \
                'dayofweek' not in data:
            return web.Response(status=500, text='not all mandatory fields submitted')

        minute = None
        hour = None
        day_of_month = None
        month = None
        day_of_week = None

        if data['minute'] != 'None':
            minute = int(data['minute'])
        if data['hour'] != 'None':
            minute = int(data['hour'])
        if data['dayofmonth'] != 'None':
            minute = int(data['dayofmonth'])
        if data['month'] != 'None':
            minute = int(data['month'])
        if data['dayofweek'] != 'None':
            minute = int(data['dayofweek'])

        self.broadcast(RemoveCronJob(minute, hour, day_of_month, month, day_of_week, data['command']).dump())

        raise web.HTTPFound('/')
