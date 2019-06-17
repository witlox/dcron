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

from collections import OrderedDict


class OrderedVariableList(OrderedDict):
    """
    An ordered dictionary with a linked list containing the previous OrderedVariableList which this list depends.
    Duplicates in this list are weeded out in favour of the previous list in the chain.
    This is all in aid of the ENV variables list which must exist one per job in the chain.
    """

    def __init__(self, *args, **kw):
        self.job = kw.pop('job', None)
        super(OrderedVariableList, self).__init__(*args, **kw)

    @property
    def previous(self):
        """
        Returns the previous env in the list of jobs in the cron
        :return: env
        """
        if self.job is not None and self.job.cron is not None:
            index = self.job.cron.crons.index(self.job)
            if index == 0:
                return self.job.cron.env
            return self.job.cron[index-1].env
        return None

    def all(self):
        """
        Returns the full dictionary, everything from this dictionary plus all those in the chain above us.
        :return: dict plus chain
        """
        if self.job is not None:
            ret = self.previous.all().copy()
            ret.update(self)
            return ret
        return self.copy()

    def __getitem__(self, key):
        previous = self.previous
        if key in self:
            return super(OrderedVariableList, self).__getitem__(key)
        elif previous is not None:
            return previous.all()[key]
        raise KeyError("Environment Variable '%s' not found." % key)

    def __str__(self):
        ret = []
        for key, value in self.items():
            if self.previous:
                if self.previous.all().get(key, None) == value:
                    continue
            if ' ' in str(value) or value == '':
                value = '"%s"' % value
            ret.append("%s=%s" % (key, str(value)))
        ret.append('')
        return "\n".join(ret)
