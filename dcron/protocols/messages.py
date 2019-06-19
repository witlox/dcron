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

from datetime import datetime


class Kill(object):

    def __init__(self, job):
        self.job = job
        self.pid = next(job.log)['pid']


class Run(object):

    def __init__(self, job):
        self.job = job


class Toggle(object):

    def __init__(self, job):
        self.job = job


class Status(object):

    def __init__(self, ip=None, system_load=None):
        """
        our serializable Status Message
        :param ip: ip address
        :param system_load: system load (0-100%)
        """
        self.ip = ip
        self.time = datetime.utcnow()
        self.system_load = system_load
        self.state = 'running'

    def __eq__(self, other):
        if not other or not isinstance(other, Status):
            return False
        return self.ip == other.ip and self.time == other.time

    def __hash__(self):
        return hash(self.ip)


class ReBalance(object):

    def __init__(self, timestamp):
        self.timestamp = timestamp
