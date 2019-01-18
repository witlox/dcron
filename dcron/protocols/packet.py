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

import struct
from uuid import uuid4


class Packet:

    max_size = 1024
    uuid_size = 36
    total_size = 4
    index_size = 4
    data_size = 980

    def __init__(self, total, index, data):
        """
        Our UDP Packet structure
        :param total: total amount of packets for an object
        :param index: current index of total
        :param data: raw byte data
        """
        self.id = str(uuid4())
        self.total = total
        self.index = index
        self.data = data

    def encode(self):
        return struct.pack('!36sLL980s', self.id.encode('utf-8'), self.total, self.index, self.data)

    @staticmethod
    def decode(packet):
        """
        decode a single UdpPacket from raw bytes
        :param packet: packet
        :return: UdpPacket or None
        """
        try:
            lid, ltot, lidx, ldat = struct.unpack('!36sLL980s', packet)
            packet = Packet(ltot, lidx, ldat)
            packet.id = lid.decode('utf-8')
            return packet
        except:
            return None

    def __eq__(self, other):
        if not other or not isinstance(other, Packet):
            return False
        return self.id == other.id
