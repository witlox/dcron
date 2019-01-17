#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import pickle
import struct
from math import ceil
from operator import itemgetter
from uuid import uuid4

from dcron.protocol import *


encoding_pattern = '!{0}sLL{1}s'.format(udp_packet['uuid'], udp_packet['data'])


class UdpSerializer(object):

    @staticmethod
    def decode(packet):
        """
        decode a single UdpPacket from raw bytes
        :param packet: packet
        :return: UdpPacket or None
        """
        try:
            return UdpPacket(*struct.unpack(encoding_pattern, packet))
        except:
            return None

    @staticmethod
    def group(data, decoded=True):
        """
        group packets by uuid
        :param data: list of raw udp_packet
        :param decoded: data is list of UdpPacket, not a bunch of bytes
        :return: dict(uuid, list(packet))
        """
        groups = {}
        for elem in data:
            if decoded:
                packet = elem
            else:
                packet = UdpPacket(*struct.unpack(encoding_pattern, elem))
            if packet.uuid not in groups.keys():
                groups[packet.uuid] = []
            groups[packet.uuid].append(packet)
        return groups

    @staticmethod
    def validate(data, decoded=True):
        """
        validate if the object is complete
        :param data: list of raw udp_packet
        :param decoded: data is list of UdpPacket, not a bunch of bytes
        :return: true or false
        """
        packets = []
        for elem in data:
            if decoded:
                packets.append(elem)
            else:
                packets.append(UdpPacket(*struct.unpack(encoding_pattern, elem)))
        if len(packets) == 0:
            return False
        expected = range(0, packets[0].total)
        given = [i.index for i in packets]
        missing = [x for x in expected if x not in given]
        if len(missing) > 0:
            return False
        return True

    @staticmethod
    def load(data, decoded=True):
        """
        construct object from udp packets
        :param data: list of raw udp_packet
        :param decoded: data is list of UdpPacket, not a bunch of bytes
        :return: the object
        """
        packets = []
        for elem in data:
            if decoded:
                packets.append(elem)
            else:
                packets.append(struct.unpack(encoding_pattern, elem))
        buffer = b''
        for packet in sorted(packets, key=itemgetter(2)):
            buffer += packet[3]
        return pickle.loads(buffer)

    @staticmethod
    def dump(obj):
        buffer = pickle.dumps(obj)
        total = ceil(len(buffer) / udp_packet['data'])
        uuid = uuid4()
        for i in range(total):
            yield struct.pack(encoding_pattern, uuid.bytes, total, i, buffer[i*udp_packet['data']:(i+1)*udp_packet['data']])
