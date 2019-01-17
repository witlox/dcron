#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import asyncio
from os.path import exists

from dcron.serializer import *
from dcron.storage import Storage


def test_store_status_message():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    with Storage(loop, queue) as storage:
        job = CronJob(0, 0, 0, 0, 0, "echo 'hello world'")
        ip = '127.0.0.1'

        async def message_stored():
            while not storage.node_state(ip):
                await asyncio.sleep(0.1)

        message = StatusMessage(ip, 10, list(job), None, list(job), None)
        queue.put_nowait(UdpSerializer.dump(message))
        loop.run_until_complete(message_stored())
        result = storage.node_state(ip)
        assert message == result

    loop.close()


def test_store_to_disk_status_message():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    with Storage(loop, queue, path_prefix='/tmp') as storage:
        job = CronJob(0, 0, 0, 0, 0, "echo 'hello world'")
        ip = '127.0.0.1'

        async def message_stored():
            while not storage.node_state(ip):
                await asyncio.sleep(0.1)

        message = StatusMessage(ip, 10, list(job), None, list(job), None)
        queue.put_nowait(UdpSerializer.dump(message))
        loop.run_until_complete(message_stored())
        result = storage.node_state(ip)
        assert message == result
        assert exists('/tmp/cluster_status.pickle')

    loop.close()
