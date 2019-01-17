#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import socket


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
