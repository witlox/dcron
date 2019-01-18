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
import asyncio
import selectors

from asyncio import DatagramProtocol


class StatusProtocol(DatagramProtocol):

    logger = logging.getLogger(__name__)

    def __init__(self, queue):
        self.logger.debug("initializing transport")
        self.queue = queue

    def connection_made(self, transport):
        self.logger.debug("connection made for server socket")
        self.transport = transport

    def datagram_received(self, data, addr):
        self.logger.debug("data received from {0}, emitting to queue".format(addr))
        self.queue.put_nowait(data)

    def error_received(self, exc):
        self.logger.error("error received: {0}".format(exc))

    def connection_lost(self, exc):
        self.logger.debug("connection closed ({0})".format(exc))


class StatusProtocolServer:

    logger = logging.getLogger(__name__)
    _udp_server_task = None

    def __init__(self, queue, port):
        """
        our UDP server socket
        :param queue: asyncio queue to emit packets to
        :param port: broadcast port to listen on
        """
        self.port = port
        self.logger.debug("initializing event loop")
        selector = selectors.SelectSelector()
        self.loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(self.loop)
        self.transport = self.loop.create_datagram_endpoint(
            lambda: StatusProtocol(queue), local_addr=('0.0.0.0', self.port)
        )

    def __enter__(self):
        """
        Start our UDP server
        :return: event loop
        """
        self.logger.info("starting UDP server socket on {0}".format(self.port))
        self._udp_server_task = self.loop.create_task(self.transport)
        return self.loop

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop our UDP server
        """
        self.logger.info("stopping UDP server")
        self.transport.close()
        self._udp_server_task.cancel()
