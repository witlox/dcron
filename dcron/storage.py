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
import pickle

from os.path import join, exists

import aiofiles

from dcron.protocols import Packet, group
from dcron.protocols.cronjob import CronJob
from dcron.protocols.status import StatusMessage


class Storage:

    logger = logging.getLogger(__name__)

    queue = asyncio.Queue()

    _buffer = []

    _cluster_status = {}
    _cluster_jobs = []

    def __init__(self, path_prefix=None):
        """
        our storage class
        :param path_prefix: directory where to save our storage
        """
        self.path_prefix = path_prefix
        if self.path_prefix:
            path = join(self.path_prefix, 'cluster_status.pickle')
            if not exists(path):
                self.logger.info("no previous cache detected on {0}".format(path))
                return
            self.logger.debug("loading cache from {0}".format(path))
            with open(path, 'rb') as handle:
                self._cluster_status = pickle.load(handle)

    async def save(self):
        """
        save our cache to disk
        """
        self.logger.debug("auto-save")
        if not self.path_prefix:
            self.logger.warning("no path specified for cache, cannot save")
            return
        path = join(self.path_prefix, 'cluster_status.pickle')
        self.logger.debug("saving cache to {0}".format(path))
        async with aiofiles.open(path, 'wb') as handle:
            await handle.write(pickle.dumps(self._cluster_status))

    async def process(self):
        """
        processor for our queue
        """
        data = await self.queue.get()
        logging.debug("got {0} on processor queue".format(data))
        packet = Packet.decode(data)
        if packet:
            self._buffer.append(packet)
            packet_groups = group(self._buffer)
            for uuid in packet_groups.keys():
                self.logger.debug("identifying packet group for {0}".format(uuid))
                if StatusMessage.load(packet_groups[uuid]):
                    status_message = StatusMessage.load(packet_groups[uuid])
                    self.logger.debug("got full status message in buffer ({0}".format(status_message))
                    if status_message.ip not in self._cluster_status.keys():
                        self._cluster_status[status_message.ip] = []
                    self._cluster_status[status_message.ip].append(status_message)
                    for packet in packet_groups[uuid]:
                        self.logger.debug("removing status message {0} from buffer".format(uuid))
                        self._buffer.remove(packet)
                elif CronJob.load(packet_groups[uuid]):
                    cron_job = CronJob.load(packet_groups[uuid])
                    self.logger.debug("got full cronjob in buffer ({0}".format(cron_job))
                    if cron_job not in self._cluster_jobs:
                        self._cluster_jobs.append(cron_job)
                    for packet in packet_groups[uuid]:
                        self.logger.debug("removing status message {0} from buffer".format(uuid))
                        self._buffer.remove(packet)
        self.logger.debug("pruning memory")
        for ip in self._cluster_status.keys():
            states = self._cluster_status[ip]
            previous_status = None
            prune_list = []
            for index, status in enumerate(sorted(states, key=lambda x: x.time)):
                if previous_status and previous_status.load == status.load:
                    prune_list.append(index)
                else:
                    previous_status = status
            for index in sorted(prune_list, reverse=True):
                self.logger.debug("pruning memory: index {0}".format(index))
                del (self._cluster_status[ip][index])
        self.queue.task_done()

    def put_nowait(self, packet):
        """
        put UDP packets on our queue for processing
        :param packet: UDP packet
        """
        self.queue.put_nowait(packet)
        asyncio.create_task(self.process())

    def node_state(self, ip):
        """
        get state of a specific node
        :param ip: ip of the node
        :return: last known state
        """
        if ip not in self._cluster_status.keys():
            return None
        sorted_status = sorted(self._cluster_status[ip], key=lambda s: s.time)
        if not sorted_status:
            return None
        return sorted_status[0]

    def cluster_state(self):
        """
        get state of all known nodes of the cluster
        :return: generator of node states
        """
        for ip in self._cluster_status.keys():
            yield self.node_state(ip)

    def cron_jobs(self):
        """
        get scheduled for the cluster
        :return: generator of cron jobs
        """
        for cron_job in self._cluster_jobs:
            yield cron_job
