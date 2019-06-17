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
import signal
import socket
import psutil

import ntplib as ntplib


def get_ntp_offset(server):
    """
    get NTP UTC time from server
    :param server: server to query
    :return: offset in seconds
    """
    c = ntplib.NTPClient()
    response = c.request(server, version=3)
    return response.offset


def get_ip():
    """
    get ip address of current machine
    :return: our ip
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def get_load():
    """
    get system load
    :return: 0-100%
    """
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0


def check_process(command, pid=None):
    """
    check for the existence of a unix process with a given command (by pid if given).
    :param command: command associated with it
    :param pid: pid that should exist
    :return: pid or None
    """
    for proc in psutil.process_iter():
        try:
            if command in ' '.join(proc.cmdline()):
                if not pid:
                    return proc.pid
                if pid and proc.pid == pid:
                    return proc.pid
        except:
            pass
    return None


def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True, timeout=None, on_terminate=None):
    """
    Kill a process tree (including grandchildren) with signal "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is called as soon as a child terminates.
    Will raise ValueError when trying to terminate self.
    :param pid: process id to terminate
    :param sig: signal used for termination (default: SIGTERM)
    :param include_parent: also kill parent process (default: True)
    :param timeout: timeout for waiting till children are terminated
    :param on_terminate: callback
    :return: tuple of processes that have been terminated and still alive
    """
    if pid == os.getpid():
        raise ValueError("won't kill myself")
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        p.send_signal(sig)
    gone, alive = psutil.wait_procs(children, timeout=timeout, callback=on_terminate)
    return gone, alive
