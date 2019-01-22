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

    def __init__(self, storage, staleness):
        """
        Our simplistic CronJob scheduler
        :param storage: storage class
        :param staleness: amount of seconds of non-communication to declare a node as stale
        """
        self.storage = storage
        self.staleness = staleness

    def active_nodes(self):
        for node in self.storage.cluster_state():
            if datetime.utcnow() - node.time < timedelta(seconds=self.staleness):
                yield node
            else:
                node.state = 'disconnected'
                self.storage.put_nowait(node)

    async def check_jobs(self, now):
        """
        check if you have to start a CronJob
        :param now: current date time
        """
        for job in self.storage.cron_jobs():
            if job.should_run_now(now):
                self.logger.info("going to execute timed job: {0}".format(job.command))
                job.last_exit_code, job.last_std_out, job.last_std_err = await run_async(job.command)

    def check_cluster_state(self):
        """
        check cluster state, if invalid, rebalance
        :return False if rebalanced otherwise True
        """
        left = list(self.storage.cluster_state())
        right = list(self.active_nodes())
        inactive_nodes = [i for i in left + right if i not in left or i not in right]
        for job in self.storage.cron_jobs():
            if not job.is_assigned():
                self.logger.debug("detected unassigned job ({0}), rebalancing".format(job.command))
                self.rebalance()
                return False
            if job.assigned_to in inactive_nodes:
                self.logger.debug("detected job ({0}) on inactive node, rebalancing".format(job.command))
                self.rebalance()
                return False
        return True

    def rebalance(self):
        """
        Redistribute CronJobs over the cluster
        """
        nodes = [n for n in self.active_nodes()]
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
                draw = node_pick(len(nodes), 1)[0]
                self.logger.info("assigning jobs {0} to node {1}".format(job, nodes[draw]))
                job.assign(nodes[draw])
