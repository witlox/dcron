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

    queue = asyncio.Queue()

    packets = message.dump()
    for packet in packets:
        queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(*[storage.process(queue)]))

    assert queue.qsize() == 0
    assert message == storage.node_state(ip)

    loop.close()


def test_store_cron_job_message_to_disk():
    pickle = '/tmp/cluster_status.pickle'
    if exists(pickle):
        remove(pickle)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    storage = Storage(path_prefix='/tmp')

    ip = '127.0.0.1'

    message = CronJob(command="echo 'hello world'")

    queue = asyncio.Queue()

    packets = message.dump()
    for packet in packets:
        queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(*[storage.process(queue), storage.save()]))

    assert queue.qsize() == 0
    assert message == storage.node_state(ip)
    assert exists(pickle)

    loop.close()


def test_memory_pruner():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    storage = Storage()

    ip = '127.0.0.1'

    messages = [StatusMessage(ip, 10), StatusMessage(ip, 10), StatusMessage(ip, 10)]

    async def processor(s, q):
        while not q.empty():
            await s.process(q)

    for message in messages:
        for packet in message.dump():
            queue.put_nowait(packet)

    loop.run_until_complete(asyncio.gather(*[processor(storage, queue)]))

    assert len(storage._cluster_status[ip]) == 3

    storage.prune()

    assert len(storage._cluster_status[ip]) == 1

    loop.close()
