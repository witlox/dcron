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
import socket


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
