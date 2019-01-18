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
import asyncio

from datetime import timedelta, datetime
from itertools import combinations
from random import randint


def node_pick(node_count, pick_count):
    result = ()
    if pick_count == node_count:
        for i in range(pick_count):
            result += (i,)
    else:
        for i in range(pick_count):
            result += (randint(0, node_count),)
    return result


async def run_async(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout, stderr


class Scheduler:

    logger = logging.getLogger(__name__)

    def __init__(self, loop, storage, staleness):
        self.loop = loop
        self.storage = storage
        self.staleness = staleness

    def __enter__(self):
        self.logger.info("starting scheduler")
        self.job_check_task = self.loop.create_task(self.periodic_check_jobs())
        self.state_check_task = self.loop.create_task(self.periodic_check_cluster_state())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.state_check_task.cancel()
        self.job_check_task.cancel()

    def active_nodes(self, nodes):
        for node in nodes:
            if datetime.utcnow() - node.time < timedelta(seconds=self.staleness):
                yield node

    async def periodic_check_jobs(self, interval=60):
        """
        Periodically check if you have to start an application
        :param interval: seconds
        """
        while True:
            await asyncio.sleep(interval)
            now = datetime.utcnow()
            for job in self.storage.cron_jobs():
                if job.should_run_now(now):
                    self.logger.info("going to execute timed job: {0}".format(job.command))
                    job.last_exit_code, job.last_std_out, job.last_std_err = run_async(job.command)

    async def periodic_check_cluster_state(self, interval=30):
        """
        Periodically check cluster state, if invalid, rebalance
        :param interval: seconds
        """
        while True:
            await asyncio.sleep(interval)
            inactive_nodes = set(self.storage.cluster_state()) - set(self.active_nodes())
            for job in self.storage.cron_jobs():
                if not job.is_assigned():
                    self.logger.info("detected unassigned job ({0}), rebalancing".format(job.command))
                    self.rebalance()
                    break
                if job.is_assigned_to in inactive_nodes:
                    self.logger.info("detected job ({0}) on inactive node, rebalancing".format(job.command))
                    self.rebalance()
                    break

    def rebalance(self):
        """
        Redistribute cronjobs over the cluster
        """
        nodes = [n for n in self.active_nodes(self.storage.cluster_state())]
        jobs = list(self.storage.cron_jobs())
        overlaps = [(l, r) for (l, r) in combinations(jobs, 2) if l.overlapping(r)]

        for l, r in overlaps:
            if l in jobs:
                jobs.remove(l)
            if r in jobs:
                jobs.remove(r)
            nl, nr = node_pick(len(nodes), 2)
            if not l.is_assigned():
                self.logger.info("assigning jobs {0} to node {1}".format(l, nodes[nl]))
                l.assign(nodes[nl])
            if not r.is_assigned():
                r.assign(nodes[nr])
                self.logger.info("assigning jobs {0} to node {1}".format(r, nodes[nr]))

        for job in jobs:
            if not job.is_assigned():
                draw = node_pick(len(nodes), 1)
                self.logger.info("assigning jobs {0} to node {1}".format(job, nodes[draw]))
                job.assign(nodes[draw])
