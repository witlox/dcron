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
from dcron.cron.cronitem import CronItem
from dcron.protocols.messages import Status
from dcron.scheduler import Scheduler
from dcron.storage import Storage


def test_active_nodes():
    ip = 'test'
    storage = Storage()
    storage.cluster_status = [Status(ip, 0)]
    scheduler = Scheduler(storage, 60)
    assert len(list(scheduler.active_nodes())) == 1


def test_rebalancing():
    n1 = 'node1'
    n2 = 'node2'
    storage = Storage()
    storage.cluster_status = [Status(n1, 0), Status(n2, 0)]
    cj1 = CronItem(command="echo 'hello world 1'")
    cj2 = CronItem(command="echo 'hello world 2'")
    storage.cluster_jobs.append(cj1)
    storage.cluster_jobs.append(cj2)
    scheduler = Scheduler(storage, 60)
    assert not scheduler.check_cluster_state()
    scheduler.re_balance()
    assert scheduler.check_cluster_state()

