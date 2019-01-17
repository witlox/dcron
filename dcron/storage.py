#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import asyncio
import logging
import pickle
from datetime import datetime

from os.path import join, exists

import aiofiles

from dcron.serializer import UdpSerializer


class Storage:

    logger = logging.getLogger(__name__)

    _buffer = []
    _tasks = []
    _cluster_status = {}

    def __init__(self, loop, queue, path_prefix=None):
        """
        our storage class
        :param loop: asyncio event loop
        :param queue: asyncio queue to consume from
        :param path_prefix: directory where to save our storage
        """
        self._loop = loop
        self.queue = queue
        self.path_prefix = path_prefix

    def __enter__(self):
        if self.path_prefix:
            path = join(self.path_prefix, 'cluster_status.pickle')
            if not exists(path):
                self.logger.info("no previous cache detected on {0}".format(path))
                return
            self.logger.debug("loading cache from {0}".format(path))
            with open(path, 'rb') as handle:
                self._cluster_status = pickle.load(handle)
            self._tasks.append(self._loop.create_task(self._auto_saver()))
        self._tasks.append(asyncio.ensure_future(self._processor()))
        self._tasks.append(self._loop.create_task(self._pruner()))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for task in self._tasks:
            task.cancel()

    async def _auto_saver(self):
        """
        automatically save our cache, calls every 60 seconds
        """
        while True:
            await asyncio.sleep(60)
            self.logger.debug("auto-save")
            if not self.path_prefix:
                self.logger.warning("no path specified for cache, cannot save")
                return
            path = join(self.path_prefix, 'cluster_status.pickle')
            self.logger.debug("saving cache to {0}".format(path))
            async with aiofiles.open(path, 'wb') as handle:
                await pickle.dump(self._cluster_status, handle, protocol=pickle.HIGHEST_PROTOCOL)

    async def _processor(self):
        self.logger.debug("starting storage queue processor")
        while True:
            data = await self.queue.get()
            logging.debug("got {0} on UDP server processor queue".format(data))
            packet = UdpSerializer.decode(data)
            if packet:
                self._buffer.append(packet)
                packet_groups = UdpSerializer.group(self._buffer)
                for uuid in packet_groups.keys():
                    self.logger.debug("validating packet group for {0}".format(uuid))
                    if UdpSerializer.validate(packet_groups[uuid]):
                        status = UdpSerializer.load(packet_groups[uuid])
                        self.logger.debug("got full status message in buffer ({0}".format(status))
                        if status.ip not in self._cluster_status.keys():
                            self._cluster_status[status.ip] = []
                        self._cluster_status[status.ip].append((status, datetime.now()))
                        for packet in packet_groups[uuid]:
                            self.logger.debug("removing status message {0} from buffer".format(uuid))
                            self._buffer.remove(packet)
            self.queue.task_done()

    async def _pruner(self):
        """
        clear out all duplicate states, calls every 180 seconds
        """
        while True:
            await asyncio.sleep(180)
            self.logger.debug("pruning memory")
            for ip in self._cluster_status.keys():
                states = self._cluster_status[ip]
                previous_status = None
                prune_list = []
                for index, (status, timestamp) in enumerate(states):
                    if previous_status == status:
                        prune_list.append(index)
                    else:
                        previous_status = status
                for index in prune_list:
                    self.logger.debug("pruning memory: index {0}".format(index))
                    del(self._cluster_status[ip][index])

    def node_state(self, ip):
        """
        get state of a specific node
        :param ip: ip of the node
        :return: last known state
        """
        if ip not in self._cluster_status.keys():
            return None
        sorted_status = sorted(self._cluster_status[ip], key=lambda s: s[1])
        if not sorted_status:
            return None
        return sorted_status[0][0]

    def cluster_state(self):
        """
        get state of all known nodes of the cluster
        :return: generator of node states
        """
        for ip in self._cluster_status.keys():
            yield self.node_state(ip)
