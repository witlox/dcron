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

import psutil

from dcron.protocols.base import Serializable


class CronJob(Serializable):

    assigned_to = None
    last_start_on = None
    last_exit_code = None
    last_std_out = None
    last_std_err = None
    pid = None

    def __init__(self, minute=None, hour=None, day_of_month=None, month=None, day_of_week=None, command=None):
        """
        our serializable cronjob
        :param minute: None or int
        :param hour: None or int
        :param day_of_month: None or int
        :param month: None or int
        :param day_of_week: None or int
        :param command: None or string
        """
        if minute:
            assert 0 <= minute <= 59
        if hour:
            assert 0 <= hour <= 23
        if day_of_month:
            assert 1 <= day_of_month <= 31
        if month:
            assert 1 <= month <= 12
        if day_of_week:
            assert 0 <= day_of_week <= 6

        self.minute = minute
        self.hour = hour
        self.day_of_month = day_of_month
        self.month = month
        self.day_of_week = day_of_week
        self.command = command

    @staticmethod
    def load(data):
        obj = Serializable.load(data)
        if isinstance(obj, CronJob):
            return obj
        return None

    def __eq__(self, other):
        if not other or not isinstance(other, CronJob):
            return False
        return self.minute == other.minute and \
               self.hour == other.hour and \
               self.day_of_month == other.day_of_month and \
               self.month == other.month and \
               self.day_of_week == other.day_of_week and \
               self.command == other.command

    def overlapping(self, other):
        if not other or not isinstance(other, CronJob):
            return False
        return self.minute == other.minute and \
               self.hour == other.hour and \
               self.day_of_month == other.day_of_month and \
               self.month == other.month and \
               self.day_of_week == other.day_of_week

    def is_assigned(self):
        if self.assigned_to:
            return True
        return False

    def assign(self, node):
        self.assigned_to = node

    def should_run_now(self, now):
        if self.minute:
            if not self.minute == now.minute:
                return False
        if self.hour:
            if not self.hour == now.hour:
                return False
        if self.day_of_month:
            if not self.day_of_month == now.day:
                return False
        if self.month:
            if not self.month == now.month:
                return False
        if self.day_of_week:
            if not self.day_of_week == now.weekday():
                return False
        return True

    def is_running(self):
        return self.pid and not self.last_exit_code

    def kill(self):
        if self.is_running():
            p = psutil.Process(self.pid)
            p.kill()
            self.pid = None


class RemoveCronJob(CronJob):

    @staticmethod
    def load(data):
        obj = Serializable.load(data)
        if isinstance(obj, RemoveCronJob):
            return obj
        return None
