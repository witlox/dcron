#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import random
import string

from dcron.serializer import *


def test_serialize_deserialize_hello_world():
    s = "hello world"
    ser = list(UdpSerializer.dump(s))
    assert len(ser) == 1
    assert s == UdpSerializer.load(ser, decoded=False)


def test_serialize_deserialize_lt_64k():
    s = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(66000))
    ser = list(UdpSerializer.dump(s))
    assert len(ser[0]) <= udp_max_size
    assert len(ser) > 1
    assert s == UdpSerializer.load(ser, decoded=False)


def test_serialize_deserialize_status_message():
    job = CronJob(0, 0, 0, 0, 0, "echo 'hello world'")
    message = StatusMessage('127.0.0.1', 10, list(job), None, list(job), None)
    ser = list(UdpSerializer.dump(message))
    assert message == UdpSerializer.load(ser, decoded=False)


def test_serialize_validate():
    s = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(180000))
    ser = list(UdpSerializer.dump(s))
    assert UdpSerializer.validate(ser, decoded=False)
    del(ser[0])
    assert not UdpSerializer.validate(ser, decoded=False)
