#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import asyncio
import logging
import selectors
import socket

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


def client(port, data):
    """
    broadcast UDP data
    :param port: port to broadcast to
    :param data: udp packet to send
    """
    logger = logging.getLogger('udp_client')

    addr = ('255.255.255.255', port)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if hasattr(socket, 'SO_BROADCAST'):
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if udp_socket.sendto(data, addr):
        logger.debug("sent data {0} to port {1}".format(data, port))
    else:
        logger.warning("failed to send data to port {0}".format(port))

    udp_socket.close()
