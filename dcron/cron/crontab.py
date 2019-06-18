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

import os
import pwd
import shlex
import types
import tempfile
import subprocess

from collections import OrderedDict
from enum import Enum

from dcron.cron.utils import items_regex, cron_cmd
from dcron.cron.cronitem import CronItem, CronDateTimeParts
from dcron.cron.orderedvariablelist import OrderedVariableList


class TabType(Enum):
    SYSTEM = 1
    USER = 2


class TabState(object):
    tab_type = None
    user = None
    file_name = None
    mine = False
    attached = False


class CronTab(object):
    """
    CronTab abstraction
    """

    def __init__(self, user=None, tab=None, tabfile=None, log=None):
        """
        CronTab object which can access any time based cron using the standard.
        :param user: Set the user of the crontab (default: None)
          * 'user' = Load from $username's crontab (instead of tab or tabfile)
          * None   = Don't load anything from any user crontab.
          * True   = Load from current $USER's crontab (unix only)
          * False  = This is a system crontab, each command has a username
        :param tab: Use a string variable as the crontab instead of installed crontab
        :param tabfile: Use a file for the crontab instead of installed crontab
        :param log: Filename for logfile instead of /var/log/syslog
        """
        self.lines = None
        self.crons = None
        self.filename = None
        self.env = None
        self._parked_env = OrderedDict()
        self.root = os.getuid() == 0
        self._user = user
        self.in_tab = tab
        self._tabfile = tabfile
        self.read(tabfile)
        self._log = log

    @property
    def user(self):
        """
        Return user's username of this CronTab if applicable
        """
        if self._user is True:
            return pwd.getpwuid(os.getuid())[0]
        return self._user

    @property
    def user_opt(self):
        """
        Returns the user option for the CronTab commandline
        """
        if self._user and self._user is not True:
            if self._user != pwd.getpwuid(os.getuid())[0]:
                return {'u': self._user}
        return {}

    def __setattr__(self, name, value):
        """
        Catch setting crons and lines directly
        """
        if name == 'lines' and value:
            for line in value:
                self.append(CronItem.from_line(line, cron=self), line, read=True)
        elif name == 'crons' and value:
            raise AttributeError("You can NOT set crons attribute directly")
        else:
            super(CronTab, self).__setattr__(name, value)

    @staticmethod
    def _open_pipe(cmd, *args, **flags):
        """
        Runs a program and orders the arguments for compatibility.
        keyword args are flags and always appear /before/ arguments for bsd
        """
        cmd_args = tuple(shlex.split(cmd))
        env = flags.pop('env', None)
        for (key, value) in flags.items():
            if len(key) == 1:
                cmd_args += ("-%s" % key),
                if value is not None:
                    cmd_args += str(value),
            else:
                cmd_args += ("--%s=%s" % (key, value)),
        args = tuple(arg for arg in (cmd_args + tuple(args)) if arg)
        return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    def read(self, filename=None):
        """
        Read in the CronTab from the system into the object, called automatically when listing or using the object.
        """
        self.crons = []
        self.lines = []
        self.env = OrderedVariableList()
        lines = []

        if self.in_tab is not None:
            lines = self.in_tab.split('\n')

        elif filename:
            self.filename = filename
            with open(filename, 'r') as fhl:
                lines = fhl.readlines()

        elif self.user:
            (out, err) = self._open_pipe(cron_cmd, l='', **self.user_opt).communicate()
            if err and 'no crontab for' in str(err):
                pass
            elif err:
                raise IOError("Read crontab {0}: {1}".format(self.user, err))
            lines = out.decode('utf-8').split("\n")

        self.lines = lines

    def append(self, item, line='', read=False):
        """
        Append a CronItem object to this CronTab
        """
        if item.is_valid():
            item.env.update(self._parked_env)
            self._parked_env = OrderedDict()
            if read and not item.comment and self.lines and self.lines[-1] and self.lines[-1][0] == '#':
                item.set_comment(self.lines.pop()[1:].strip())
            self.crons.append(item)
            self.lines.append(item)
        elif '=' in line:
            if ' ' not in line or line.index('=') < line.index(' '):
                (name, value) = line.split('=', 1)
                value = value.strip()
                for quot in "\"'":
                    if value[0] == quot and value[-1] == quot:
                        value = value.strip(quot)
                        break
                self._parked_env[name.strip()] = value
        else:
            if not self.crons and self._parked_env:
                self.env.update(self._parked_env)
                self._parked_env = OrderedDict()
            self.lines.append(line.replace('\n', ''))

    def write(self, filename=None, user=None, errors=False):
        """
        Write the CronTab to it's source or a given filename.
        """
        if filename:
            self.filename = filename
        elif user is not None:
            self.filename = None
            self.in_tab = None
            self._user = user

        # Add to either the crontab or the internal tab.
        if self.in_tab is not None:
            self.in_tab = self.render()
            # And that's it if we never saved to a file
            if not self.filename:
                return

        if self.filename:
            file_handle = open(self.filename, 'wb')
        else:
            filed, path = tempfile.mkstemp()
            file_handle = os.fdopen(filed, 'wb')

        file_handle.write(self.render(errors=errors).encode('utf-8'))
        file_handle.close()

        if not self.filename:
            path = "/var/spool/cron/crontabs/{0}".format(self.user)
            if self.user:
                proc = self._open_pipe(cron_cmd, path, **self.user_opt)
                # This could do with being cleaned up quite a bit
                proc.wait()
                proc.stdout.close()
                proc.stderr.close()
                os.unlink(path)
            else:
                os.unlink(path)
                raise IOError("Please specify user or filename to write.")

    def attach(self, filename):
        """
        Attach file to path
        """
        self.filename = filename

    def write_to_user(self, user=True):
        """
        Write the CronTab to a user (or root) instead of a file.
        """
        return self.write(user=user)

    def render(self, errors=False):
        """
        Render this CronTab as it would be in the CronTab.
        :param errors: Should we not comment out invalid entries
        """
        crons = []
        for line in self.lines:
            if isinstance(line, (str, str)):
                if line.strip().startswith('#') or not line.strip():
                    crons.append(line)
                elif not errors:
                    crons.append('# DISABLED LINE\n# ' + line)
                else:
                    raise ValueError("Invalid line: %s" % line)
            elif isinstance(line, CronItem):
                if not line.is_valid() and not errors:
                    line.enabled = False
                crons.append(str(line))

        # Environment variables are attached to cron lines so order will
        # always work no matter how you add lines in the middle of the stack.
        result = str(self.env) + u'\n'.join(crons)
        if result and result[-1] not in (u'\n', u'\r'):
            result += u'\n'
        return result

    def new(self, command='', comment='', user=None):
        """
        Create a new cron with a command and comment.
        :return: the new CronItem object.
        """
        if not user and self.user is False:
            raise ValueError("User is required for system crontabs.")
        item = CronItem(command, comment, user=user, cron=self)
        self.append(item)
        return item

    def find_command(self, command):
        """
        Return an iter of jobs matching any part of the command.
        """
        for job in list(self.crons):
            if isinstance(command, type(items_regex)):
                if command.findall(job.command):
                    yield job
            elif command in job.command:
                yield job

    def find_comment(self, comment):
        """
        Return an iter of jobs that match the comment field exactly.
        """
        for job in list(self.crons):
            if isinstance(comment, type(items_regex)):
                if comment.findall(job.comment):
                    yield job
            elif comment == job.comment:
                yield job

    def find_time(self, *args):
        """
        Return an iter of jobs that match this time pattern
        """
        for job in list(self.crons):
            if job.slices == CronDateTimeParts(*args):
                yield job

    @property
    def commands(self):
        """
        Return a generator of all unqiue commands used in this crontab
        """
        returned = []
        for cron in self.crons:
            if cron.command not in returned:
                yield cron.command
                returned.append(cron.command)

    @property
    def comments(self):
        """
        Return a generator of all unique comments/Id used in this crontab
        """
        returned = []
        for cron in self.crons:
            if cron.comment and cron.comment not in returned:
                yield cron.comment
                returned.append(cron.comment)

    def remove_all(self, *args, **kwargs):
        """
        Removes all crons using the stated command OR that have the stated comment OR removes everything if no arguments specified.
           command - Remove all with this command
           comment - Remove all with this comment or ID
           time    - Remove all with this time code
        """
        if args:
            raise AttributeError("Invalid use: remove_all(command='cmd')")
        if 'command' in kwargs:
            return self.remove(*self.find_command(kwargs['command']))
        elif 'comment' in kwargs:
            return self.remove(*self.find_comment(kwargs['comment']))
        elif 'time' in kwargs:
            return self.remove(*self.find_time(kwargs['time']))
        return self.remove(*self.crons[:])

    def remove(self, *items):
        """
        Remove a selected cron from the crontab.
        """
        result = 0
        for item in items:
            if isinstance(item, (list, tuple, types.GeneratorType)):
                for subitem in item:
                    result += self._remove(subitem)
            elif isinstance(item, CronItem):
                result += self._remove(item)
            else:
                raise TypeError("You may only remove CronItem objects, please use remove_all() to specify by name, id, etc.")
        return result

    def _remove(self, item):
        """
        Internal removal of an item
        """
        # Manage siblings when items are deleted
        for sibling in self.lines[self.lines.index(item)+1:]:
            if isinstance(sibling, CronItem):
                env = sibling.env
                sibling.env = item.env
                sibling.env.update(env)
                sibling.env.job = sibling
                break
            elif sibling == '':
                self.lines.remove(sibling)
            else:
                break

        self.crons.remove(item)
        self.lines.remove(item)
        return 1

    def state(self):
        """
        current state of the CrontTab
        """
        if self._user:
            tab_type = TabType.USER
        else:
            tab_type = TabType.SYSTEM

        state = TabState()
        state.tab_type = tab_type
        state.user = self.user
        if self.user and not self.user_opt:
            state.mine = True
        if self.user or self.filename:
            state.attached = True
        return state

    def __iter__(self):
        """
        Return generator so we can track jobs after removal
        """
        for job in list(self.crons.__iter__()):
            yield job

    def __getitem__(self, i):
        return self.crons[i]

    def __len__(self):
        return len(self.crons)

    def __str__(self):
        return self.render()

