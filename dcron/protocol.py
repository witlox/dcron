#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from collections import namedtuple

# MTU 1500 - take a know lower value (max UDP packet size 64K)
udp_max_size = 1024

# byte sizes of our UDP packet structure
udp_packet = {
    'uuid': 36,
    'total': 4,
    'index': 4,
    'data': 980
}

UdpPacket = namedtuple('UdpPacket', 'uuid total index data')

# example of a status message
status_message = {
    'ip': '000.000.000.000',  # should support both ipv4 & ipv6
    'load': 0,                # load indicator 0-100% will be used by the scheduler
    'running': list(),        # list of currently running CronJob
    'scheduled': list(),      # list of CronJob scheduled on this machine
    'jobs': list(),           # list of all CronJobs on cluster
    'results': dict(),        # results per CronJob
}

StatusMessage = namedtuple('StatusMessage', 'ip load running scheduled jobs results')

CronJob = namedtuple('CronJob', 'minute hour day_of_month month day_of_week command')
