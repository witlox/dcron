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
from os import remove
from os.path import exists

from dcron.protocols.cronjob import CronJob
from dcron.protocols.status import StatusMessage
from dcron.storage import Storage


def test_store_status_message():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage()

    ip = '127.0.0.1'

    message = StatusMessage(ip, 10)

    packets = message.dump()
    for packet in packets:
        storage.queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(*[storage.process()]))

    assert storage.queue.qsize() == 0
    assert message == storage.node_state(ip)

    loop.close()


def test_store_cron_job_message_to_disk():
    pickle = '/tmp/cluster_status.pickle'
    if exists(pickle):
        remove(pickle)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage(path_prefix='/tmp')

    message = CronJob(command="echo 'hello world'")

    packets = message.dump()
    for packet in packets:
        storage.queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(storage.process()))

    loop.run_until_complete(asyncio.gather(storage.save()))

    assert storage.queue.qsize() == 0
    assert len(list(storage.cron_jobs())) == 1
    assert message == list(storage.cron_jobs())[0]
    assert exists(pickle)

    loop.close()


def test_store_retrieve_sorts_correctly():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage()

    ip = '127.0.0.1'

    messages = []
    for i in range(10):
        messages.append(StatusMessage(ip, 10))

    for message in messages:
        packets = message.dump()
        for packet in packets:
            storage.queue.put_nowait(packet)

    while not storage.queue.empty():
        loop.run_until_complete(asyncio.gather(storage.process()))

    assert messages[len(messages) - 1].time == storage.node_state(ip).time

    loop.close()
