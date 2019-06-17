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

from datetime import timedelta, datetime
from random import shuffle


class Scheduler(object):
    """
    Simple Scheduler Mechanism
    """

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
                yield node

    def check_cluster_state(self):
        """
        check cluster state
        :return False if invalid otherwise True
        """
        left = list(self.storage.cluster_state())
        right = list(self.active_nodes())
        inactive_nodes = [i for i in left + right if i not in left or i not in right]
        for job in self.storage.cluster_jobs:
            if not job.assigned_to:
                self.logger.info("detected unassigned job ({0})".format(job.command))
                self.re_balance()
                return False
            if job.assigned_to in inactive_nodes:
                self.logger.warning("detected job ({0}) on inactive node".format(job.command))
                self.re_balance()
                return False
        return True

    def re_balance(self):
        """
        Redistribute CronJobs over the cluster
        """
        def partition(lst, keys):
            """
            divide a list over a given set of keys
            :param lst: list to split in roughly equals chunks
            :param keys: keys for the chunks
            :return: dictionary of keys with list chunks
            """
            shuffle(lst)
            return {keys[i]: lst[i::len(keys)] for i in range(len(keys))}
        
        def first_key_by_value(dct, jb):
            """
            find the first key in a dictionary where jb is in the values
            :param dct: dictionary to analyse
            :param jb: value to search for
            :return: key or None
            """
            for n, jbs in dct.items():
                if jb in jbs:
                    return n
            return None

        nodes = [n for n in self.active_nodes()]
        jobs = list(self.storage.cluster_jobs)

        partitions = partition(jobs, nodes)

        for job in jobs:
            node = first_key_by_value(partitions, job)
            if not node:
                self.logger.error("could not find node assignment for job {0}".format(job))
            else:
                self.logger.info("assigning job {0} to node {1}".format(job, node.ip))
                job.assigned_to = node.ip

        self.storage.cluster_jobs = jobs
