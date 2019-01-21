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

from dcron.datagram.client import client
from dcron.datagram.server import StatusProtocolServer
from dcron.protocols import Packet
from dcron.protocols.status import StatusMessage
from dcron.storage import Storage


async def send_packet(port, packets):
    for packet in packets:
        client(port, packet)


def test_send_receive_broadcast():
    port = 12345

    queue = asyncio.Queue()
    with StatusProtocolServer(queue, port) as loop:

            async def packet_received():
                while queue.qsize() == 0:
                    await asyncio.sleep(0.1)

            assert queue.qsize() == 0

            packets = list(StatusMessage('127.0.0.1', 0).dump())

            assert len(packets) == 1
            assert len(packets[0]) == Packet.max_size

            loop.run_until_complete(asyncio.gather(*[packet_received(), send_packet(port, packets)]))

            assert queue.qsize() == 1


def test_send_receive_broadcast_to_storage():
    port = 12345

    storage = Storage()

    with StatusProtocolServer(storage, port) as loop:

        async def packet_received():
            while len(storage._cluster_status) == 0:
                await asyncio.sleep(0.1)

        assert len(storage._cluster_status) == 0

        packets = list(StatusMessage('127.0.0.1', 0).dump())

        assert len(packets) == 1
        assert len(packets[0]) == Packet.max_size

        loop.run_until_complete(asyncio.gather(*[packet_received(), send_packet(port, packets)]))

        assert len(storage._cluster_status) == 1
