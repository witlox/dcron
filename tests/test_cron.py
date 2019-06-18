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

from datetime import time, date
from tempfile import NamedTemporaryFile

from dcron.cron import crontab
from dcron.cron.cronitem import CronDateTimeParts

BASIC = '@hourly firstcommand\n\n'
USER = '\n*/4 * * * ...comment\n\n\n'


def test_empty_tab():
    cron = crontab.CronTab()
    assert "" == str(cron)
    assert not cron.state().attached


def test_user_tab():
    cron = crontab.CronTab(user='basic', tab=BASIC)
    assert BASIC == str(cron)
    assert cron.state().user == 'basic'


def test_cronitem():
    item = crontab.CronItem.from_line('noline')
    assert item.is_enabled()
    item.command = str('nothing')
    item.enable(False)
    assert '# * * * * * nothing' == str(item)


def test_time_object():
    item = crontab.CronItem(command='cmd')
    assert '* * * * *' == item.parts
    item.set_all(time(1, 2))
    assert '2 1 * * *' == item.parts
    assert item.is_valid()
    item.set_all(time(0, 30, 0, 0))
    assert '30 0 * * *' == item.parts
    assert item.is_valid()
    assert '30 0 * * * cmd' == str(item)


def test_date_object():
    item = crontab.CronItem(command='cmd')
    assert '* * * * *' == item.parts
    item.set_all(date(2010, 6, 7))
    assert '0 0 7 6 *' == item.parts
    assert item.is_valid()


def test_slice_validation():
    cron_slices = CronDateTimeParts
    assert cron_slices('* * * * *').is_valid()
    assert cron_slices.is_valid('* * * * *')
    assert cron_slices.is_valid('*/2 * * * *')
    assert cron_slices.is_valid('* 1,2 * * *')
    assert cron_slices.is_valid('* * 1-5 * *')
    assert cron_slices.is_valid('* * * * MON-WED')
    assert cron_slices.is_valid('@reboot')


def test_cron_item_in_tab():
    tabfile = NamedTemporaryFile()
    cron = crontab.CronTab(tabfile=tabfile.name)
    item = crontab.CronItem(command='test')
    item.set_all(time(1, 2))
    cron.append(item)
    assert 1 == len(list(cron.find_command('test')))
    cron.write()
    with open(tabfile.name, 'r') as tf:
        lines = tf.readlines()
    assert 1 == len(lines)
    assert 'test' in lines[0]
