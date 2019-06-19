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
from datetime import datetime

from dcron.cron.crontab import CronTab, CronItem
from dcron.datagram.client import broadcast
from dcron.protocols import Packet, group
from dcron.protocols.messages import Kill, ReBalance, Run, Status
from dcron.protocols.udpserializer import UdpSerializer
from dcron.utils import get_ip, check_process, kill_proc_tree


class Processor(object):
    """
    Message processor for the system
    """

    logger = logging.getLogger(__name__)

    def __init__(self, udp_port, storage, cron=None, user=None):
        self.queue = asyncio.Queue()
        self._buffer = []
        self.udp_port = udp_port
        self.storage = storage
        if not cron:
            self.cron = CronTab(tabfile='/etc/crontab', user=False)
        else:
            self.cron = cron
        self.user = user

    def update_status(self, status_message):
        self.logger.debug("got full status message in buffer ({0}".format(status_message))
        self.storage.cluster_status.append(status_message)

    def remove_job(self, job):
        self.logger.debug("got full remove in buffer ({0}".format(job))
        if job in self.storage.cluster_jobs:
            self.logger.debug("removing existing job {0}".format(job))
            self.storage.cluster_jobs.remove(job)
            if job.assigned_to == get_ip():
                if job.pid:
                    self.logger.warning("job {0} is running, going to kill it".format(job))
                    if check_process(job.command, job.pid):
                        kill_proc_tree(job.pid)
                self.logger.info("removing existing, assigned job {0}".format(job))
                cmd = next(self.cron.find_command(job.command), None)
                if cmd:
                    self.logger.info("removing {0} from cron".format(job))
                    self.cron.remove(cmd)
                    self.cron.write()
                else:
                    self.logger.warning("defined job {0} not found in cron, but assigned to me!".format(job))

    def add_job(self, new_job):
        self.logger.debug("got full job in buffer ({0}".format(new_job))
        job = next(iter([j for j in self.storage.cluster_jobs if j == new_job]), None)
        if not job:
            if new_job.assigned_to == get_ip():
                existing_job = next(self.cron.find_command(new_job.command), None)
                if existing_job and existing_job == new_job:
                    self.logger.info("job already defined in tab, skipping it")
                else:
                    if self.user and not new_job.user:
                        new_job.user = self.user
                    if self.cron and not new_job.cron:
                        new_job.cron = self.cron
                    self.logger.info("adding job {0} to cron {1}".format(new_job, self.cron.filename))
                    self.cron.append(new_job)
                    self.cron.write()
        else:
            idx = self.storage.cluster_jobs.index(job)
            del (self.storage.cluster_jobs[idx])
        self.storage.cluster_jobs.append(new_job)

    async def run(self, run, uuid):
        self.logger.debug("got full run in buffer ({0}".format(run.job))
        job = next(iter([j for j in self.storage.cluster_jobs if j == run.job]), None)
        if job and job.assigned_to == get_ip():
            self.logger.info("am owner for job {0}".format(job))
            run.timestamp = datetime.now()
            process = await asyncio.create_subprocess_shell(run.job.command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            self.logger.info("{0} has been defined, going to execute".format(job.command))
            std_out, std_err = await process.communicate()
            exit_code = await process.wait()
            if std_err:
                self.logger.warning("error during execution of {0}: {1}".format(run.job.command, std_err))
            self.logger.info("output of {0} with code {1}: {2}".format(job.command, exit_code, std_out))
            job.append_log("{0:%b %d %H:%M:%S} localhost CRON[{1}] exit code: {2}, out: {3}, err: {4}".format(datetime.now(), process.pid, exit_code, std_out, std_err))
            broadcast(self.udp_port, UdpSerializer.dump(job))
            self.clean_buffer(uuid)

    def kill(self, kill):
        if not kill.pid:
            self.logger.warning("got kill command for {0} but PID not set".format(kill.job))
        else:
            self.logger.debug("got full kill in buffer ({0}".format(kill.job))
            if kill.job.assigned_to == get_ip() and check_process(kill.command, pid=kill.pid):
                self.logger.info("I'm owner, going to try and kill the running job {0}".format(kill.job))
                try:
                    kill_proc_tree(kill.pid)
                except ValueError:
                    self.logger.warning("got signal to kill self, that's not happening")

    def clean_buffer(self, uuid):
        """
        remove packet groups from buffer
        :param uuid: identifier for the group
        """
        self.logger.debug("removing message {0} from buffer".format(uuid))
        g = group(self._buffer)
        for p in g[uuid]:
            if p in self._buffer:
                self._buffer.remove(p)

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
                obj = UdpSerializer.load(packet_groups[uuid])
                if obj:
                    self.logger.debug("got object {0} from {1}".format(obj, uuid))
                    if isinstance(obj, Status):
                        self.update_status(obj)
                        self.clean_buffer(uuid)
                    elif isinstance(obj, ReBalance):
                        self.logger.info("re-balance received")
                        self.storage.cluster_jobs.clear()
                        self.cron.remove_all()
                        self.cron.write()
                        self._buffer.clear()
                    elif isinstance(obj, CronItem):
                        if obj.remove:
                            self.remove_job(obj)
                        else:
                            self.add_job(obj)
                        self.clean_buffer(uuid)
                    elif isinstance(obj, Run):
                        await self.run(obj, uuid)
                    elif isinstance(obj, Kill):
                        self.kill(obj)
                        self.clean_buffer(uuid)
        self.storage.prune()
        self.queue.task_done()
        if not self.queue.empty():
            await self.process()

    def put_nowait(self, packet):
        """
        put UDP packets on our queue for processing
        :param packet: UDP packet
        """
        self.queue.put_nowait(packet)
        asyncio.create_task(self.process())
