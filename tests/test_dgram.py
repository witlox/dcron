#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import asyncio
import selectors

from dcron.dgram import StatusProtocolServer, client
from dcron.protocol import udp_max_size, StatusMessage
from dcron.serializer import UdpSerializer
from dcron.storage import Storage


def test_send_receive_broadcast():
    port = 12345
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)

    queue = asyncio.Queue()
    with StatusProtocolServer(queue, port) as loop:
        with Storage(loop, queue) as storage:

            async def packet_received():
                while len(storage._cluster_status) == 0:
                    await asyncio.sleep(0.1)

            assert len(storage._cluster_status) == 0

            packets = list(UdpSerializer.dump(StatusMessage('127.0.0.1', 0, None, None, None, None)))

            assert len(packets) == 1
            assert len(packets[0]) == udp_max_size

            for packet in packets:
                client(port, packet)

            loop.run_until_complete(packet_received())
