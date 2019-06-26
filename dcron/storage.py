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

import asyncio
import logging
import json

from datetime import datetime
from dateutil import parser
from json import JSONEncoder, JSONDecoder

from os.path import join, exists

import aiofiles

from dcron.cron.cronitem import CronItem
from dcron.cron.crontab import CronTab
from dcron.protocols.messages import Status


class Storage(object):
    """
    Our storage abstraction
    """

    logger = logging.getLogger(__name__)

    def __init__(self, path_prefix=None):
        """
        our storage class
        :param path_prefix: directory where to save our storage
        """
        self.cluster_status = []
        self.cluster_jobs = []
        self.path_prefix = path_prefix
        if self.path_prefix:
            path = join(self.path_prefix, 'cluster_status.json')
            if not exists(path):
                self.logger.info("no previous cache detected on {0}".format(path))
                return
            self.logger.debug("loading cache from {0}".format(path))
            with open(path, 'r') as handle:
                self.cluster_status = json.loads(handle.readline(), cls=CronDecoder)
            path = join(self.path_prefix, 'cluster_jobs.json')
            if not exists(path):
                self.logger.info("no previous cache detected on {0}".format(path))
                return
            self.logger.debug("loading cache from {0}".format(path))
            with open(path, 'r') as handle:
                self.cluster_jobs = json.loads(handle.readline(), cls=CronDecoder)

    async def save(self):
        """
        save our cache to disk
        """
        self.logger.debug("auto-save")
        if self.path_prefix:
            path = join(self.path_prefix, 'cluster_status.json')
            self.logger.debug("saving status cache to {0}".format(path))
            async with aiofiles.open(path, 'w') as handle:
                await handle.write(json.dumps(self.cluster_status, cls=CronEncoder))
            path = join(self.path_prefix, 'cluster_jobs.json')
            self.logger.debug("saving job cache to {0}".format(path))
            async with aiofiles.open(path, 'w') as handle:
                await handle.write(json.dumps(self.cluster_jobs, cls=CronEncoder))
        else:
            self.logger.warning("no path specified for cache, cannot save")
            await asyncio.sleep(0.1)

    def prune(self):
        """
        clean up our memory when it exceeds a given amount of values
        """
        if len(self.cluster_status) >= 10000000:
            self.logger.debug("pruning memory")
            for ip in [status.ip for status in self.cluster_status]:
                states = self.cluster_status[ip]
                previous_status = None
                prune_list = []
                for index, status in enumerate(sorted(states, key=lambda x: x.time)):
                    if previous_status and previous_status.load == status.load:
                        prune_list.append(index)
                    else:
                        previous_status = status
                for index in sorted(prune_list, reverse=True):
                    self.logger.debug("pruning memory: index {0}".format(index))
                    del (self.cluster_status[index])

    def node_state(self, ip):
        """
        get state of a specific node
        :param ip: ip of the node
        :return: last known state
        """
        node_status = [status for status in self.cluster_status if status.ip == ip]
        if len(node_status) == 0:
            return None
        sorted_status = sorted(node_status, key=lambda s: parser.parse(s.time), reverse=True)
        if not sorted_status:
            return None
        return sorted_status[0]

    def cluster_state(self):
        """
        get state of all known nodes of the cluster
        :return: generator of node states
        """
        for ip in set([status.ip for status in self.cluster_status]):
            yield self.node_state(ip)


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


class CronEncoder(JSONEncoder):

    def default(self, o):
        if isinstance(o, CronItem):
            last_run = ''
            if o.last_run and isinstance(o.last_run, datetime):
                last_run = o.last_run.strftime("{} {}".format(DATE_FORMAT, TIME_FORMAT))
            return {
                '_type': 'CronItem',
                'cron': json.dumps(o.cron, cls=CronEncoder),
                'user': json.dumps(o.user),
                'enabled': o.enabled,
                'comment': o.comment,
                'command': o.command,
                'last_run': last_run,
                'pid': o.pid,
                'assigned_to': o.assigned_to,
                'log': o._log,
                'parts': str(o.parts)
            }
        elif isinstance(o, CronTab):
            return {
                '_type': 'CronTab',
                'user': o.user,
                'tab': o.in_tab,
                'tabfile': o._tabfile,
                'log': o._log
            }
        elif isinstance(o, Status):
            time = ''
            return {
                '_type': 'status',
                'ip': o.ip,
                'state': o.state,
                'load': o.system_load,
                'time': o.time
            }
        elif isinstance(o, list):
            return json.dumps(o, cls=CronEncoder)
        return JSONEncoder.default(self, o)


class CronDecoder(JSONDecoder):

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        if '_type' not in obj:
            return obj
        if obj['_type'] == 'CronItem':
            cron = json.loads(obj['cron'], cls=CronDecoder)
            user = json.loads(obj['user'])
            cron_item = CronItem(command=obj['command'], user=user, cron=cron)
            cron_item.enable(obj['enabled'])
            cron_item.comment = obj['comment']
            cron_item.assigned_to = obj['assigned_to']
            cron_item.pid = obj['pid']
            cron_item._log = obj['log']
            if obj['last_run'] != '':
                cron_item.last_run = parser.parse(obj['last_run'])
            cron_item.set_all(obj['parts'])
            return cron_item
        elif obj['_type'] == 'CronTab':
            return CronTab(user=obj['user'], tab=obj['tab'], tabfile=obj['tabfile'], log=obj['log'])
        elif obj['_type'] == 'status':
            status = Status()
            status.system_load = obj['load']
            status.state = obj['state']
            status.ip = obj['ip']
            status.time = obj['time']
            return status
        return obj

