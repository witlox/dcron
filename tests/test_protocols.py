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

import random
import string

from dcron.protocols import Packet
from dcron.protocols.cronjob import CronJob
from dcron.protocols.status import StatusMessage


def test_packet_encoding_and_decoding():
    data = b'hello world'
    p = Packet(1, 1, data)
    encoded = p.encode()
    assert p == Packet.decode(encoded)


def test_status_message_dumps_loads():
    sm = StatusMessage('127.0.0.1', 0)
    packets = list(sm.dump())
    assert len(packets) == 1
    assert sm == StatusMessage.load(packets)


def test_cron_job_message_dumps_loads():
    cj = CronJob(command="echo 'hello world'")
    packets = list(cj.dump())
    assert cj == CronJob.load(packets)


def test_cron_with_message_larger_then_max():
    cj = CronJob(command=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6000)))
    packets = list(cj.dump())
    assert len(packets) > 1
    assert cj == CronJob.load(packets)
