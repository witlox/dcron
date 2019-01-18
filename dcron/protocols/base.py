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

import pickle

from math import ceil

from dcron.protocols.packet import Packet


class Serializable:
    """
    Base class for loading and dumping objects to and from bytes
    """

    def _serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def _deserialize(serialized_object):
        return pickle.loads(serialized_object)

    @staticmethod
    def _validate(data):
        """
        validate if the object is complete
        :param data: list of (raw) udp_packet
        :return: true or false
        """
        packets = []
        for elem in data:
            p = Packet.decode(elem)
            if not p:
                p = elem
            packets.append(p)
        if len(packets) == 0:
            return False
        expected = range(0, packets[0].total)
        given = [i.index for i in packets]
        missing = [x for x in expected if x not in given]
        if len(missing) > 0:
            return False
        return True

    @staticmethod
    def load(data):
        """
        construct object from udp packets
        :param data: list of raw udp_packet
        :return: the object or None
        """
        if not Serializable._validate(data):
            return None
        packets = []
        for elem in data:
            p = Packet.decode(elem)
            if not p:
                p = elem
            packets.append(p)
        buffer = b''
        for p in sorted(packets, key=lambda x: x.index):
            buffer += p.data
        return Serializable._deserialize(buffer)

    def dump(self):
        buffer = self._serialize()
        total = ceil(len(buffer) / Packet.data_size)
        for i in range(total):
            yield Packet(total, i, buffer[i*Packet.data_size:(i+1)*Packet.data_size]).encode()
