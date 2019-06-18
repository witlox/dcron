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

from dcron.cron.crontab import CronTab, CronItem
from dcron.processor import Processor
from dcron.protocols.udpserializer import UdpSerializer
from dcron.storage import Storage
from dcron.utils import get_ip


def test_message_deserialization_and_assignment():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    command = "echo 'hello world'"
    cron_job = CronItem(command=command)
    cron_job.assigned_to = get_ip()

    storage = Storage()

    tab = CronTab(tab="""* * * * * command""")
    processor = Processor(12345, storage, cron=tab)

    for packet in UdpSerializer.dump(cron_job):
        processor.queue.put_nowait(packet)

    loop.run_until_complete(processor.process())

    assert 1 == len(storage.cluster_jobs)

    assert command == storage.cluster_jobs[0].command

    assert None is not next(tab.find_command(command), None)

    loop.close()


def test_add_same_job_twice_adds_cron_once():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    command = "echo 'hello world'"
    cron_job = CronItem(command=command)
    cron_job.assigned_to = get_ip()

    storage = Storage()

    tab = CronTab(tab="""* * * * * command""")
    processor = Processor(12345, storage, cron=tab)

    for packet in UdpSerializer.dump(cron_job):
        processor.queue.put_nowait(packet)

    for packet in UdpSerializer.dump(cron_job):
        processor.queue.put_nowait(packet)

    loop.run_until_complete(processor.process())

    assert 1 == len(storage.cluster_jobs)

    assert command == storage.cluster_jobs[0].command

    assert None is not next(tab.find_command(command), None)
    assert 1 == len(list(tab.find_command(command)))

    loop.close()
