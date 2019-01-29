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
import time
from datetime import datetime

from dcron.protocols.cronjob import CronJob
from dcron.protocols.status import StatusMessage
from dcron.scheduler import Scheduler
from dcron.storage import Storage
from dcron.utils import get_ip


def test_active_nodes():
    ip = 'test'
    storage = Storage()
    storage._cluster_status = {ip: [StatusMessage(ip, 0)]}
    scheduler = Scheduler(storage, 60)
    assert len(list(scheduler.active_nodes())) == 1


def test_rebalancing():
    n1 = 'node1'
    n2 = 'node2'
    storage = Storage()
    storage._cluster_status[n1] = [StatusMessage(n1, 0)]
    storage._cluster_status[n2] = [StatusMessage(n2, 0)]
    cj1 = CronJob(1, command="echo 'hello world'")
    cj2 = CronJob(2, command="echo 'hello world'")
    storage._cluster_jobs.append(cj1)
    storage._cluster_jobs.append(cj2)
    scheduler = Scheduler(storage, 60)
    assert not scheduler.check_cluster_state()
    assert scheduler.check_cluster_state()


def test_execution():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    cron_job = CronJob(command="echo 'hello world'")
    cron_job.assigned_to = StatusMessage(ip=get_ip())
    storage = Storage()

    storage._cluster_jobs.clear()

    storage._cluster_jobs.append(cron_job)

    assert 1 == len(list(storage.cron_jobs()))

    scheduler = Scheduler(storage, 180)

    loop.run_until_complete(scheduler.check_jobs(datetime.utcnow()))

    assert 1 == len(list(storage.cron_jobs()))

    cron_job = list(storage.cron_jobs())[0]

    assert 0 == cron_job.last_exit_code
    assert b'hello world\n' == cron_job.last_std_out

    loop.close()
