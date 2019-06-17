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
import shutil
from os import path
from os.path import exists
from tempfile import mkdtemp

from dcron.cron import crontab
from dcron.cron.cronitem import CronItem
from dcron.cron.crontab import CronTab
from dcron.processor import Processor
from dcron.protocols.messages import Status
from dcron.protocols.udpserializer import UdpSerializer
from dcron.storage import Storage


def test_store_status_message():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage()
    processor = Processor(12345, storage, cron=CronTab(tab="""* * * * * command"""))

    ip = '127.0.0.1'

    message = Status(ip, 10)

    packets = UdpSerializer.dump(message)
    for packet in packets:
        processor.queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(*[processor.process()]))

    assert processor.queue.qsize() == 0
    assert message == storage.node_state(ip)

    loop.close()


def test_store_cron_job_message_to_disk():
    tmp_dir = mkdtemp()
    ser = path.join(tmp_dir, 'cluster_jobs.json')

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage(path_prefix=tmp_dir)

    processor = Processor(12345, storage, cron=CronTab(tab="""* * * * * command"""))

    message = CronItem(command="echo 'hello world'")
    message.append_log("test log message")

    for packet in UdpSerializer.dump(message):
        processor.queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(processor.process()))

    loop.run_until_complete(asyncio.gather(storage.save()))

    assert processor.queue.qsize() == 0
    assert len(storage.cluster_jobs) == 1
    assert message == storage.cluster_jobs[0]
    assert exists(ser)

    loop.close()

    shutil.rmtree(tmp_dir)


def test_store_retrieve_sorts_correctly():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage()
    processor = Processor(12345, storage, cron=CronTab(tab="""* * * * * command"""))

    ip = '127.0.0.1'

    messages = []
    for i in range(10):
        messages.append(Status(ip, 10))

    for message in messages:
        packets = UdpSerializer.dump(message)
        for packet in packets:
            processor.queue.put_nowait(packet)

    while not processor.queue.empty():
        loop.run_until_complete(asyncio.gather(processor.process()))

    assert messages[len(messages) - 1].time == storage.node_state(ip).time

    loop.close()


def test_save_load():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tmp_dir = mkdtemp()
    storage = Storage(path_prefix=tmp_dir)

    cron = crontab.CronTab()
    item = CronItem(command="echo 'hello world'", cron=cron)
    item.set_all("2 1 * * *")
    item.append_log("test log message")

    storage.cluster_jobs.append(item)
    assert 1 == len(storage.cluster_jobs)

    loop.run_until_complete(storage.save())

    storage = Storage(path_prefix=tmp_dir)
    assert 1 == len(storage.cluster_jobs)
    shutil.rmtree(tmp_dir)
