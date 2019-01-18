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

import argparse
import asyncio
import logging
from asyncio import Queue

from dcron.datagram.client import client
from dcron.datagram.server import StatusProtocolServer
from dcron.protocols.status import StatusMessage
from dcron.scheduler import Scheduler
from dcron.site import WebServer
from dcron.storage import Storage
from dcron.utils import get_ip, get_ntp_offset, get_load

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-8.8s]  %(message)s")
logger = logging.getLogger('dcron')


def main():
    parser = argparse.ArgumentParser(description='Distributed Cronlike Scheduler')

    parser.add_argument('-l', '--log-file', default=None, help='path to store logfile (none means no logfile)')
    parser.add_argument('-p', '--storage-path', default=None, help='directory where to store cache (none means /tmp)')
    parser.add_argument('-c', '--communication-port', type=int, default=12345, help='communication port')
    parser.add_argument('-w', '--web-port', type=int, default=8080, help='web hosting port')
    parser.add_argument('-n', '--ntp-server', default='pool.ntp.org', help='NTP server to detect clock skew')
    parser.add_argument('-s', '--node-staleness', type=int, default=180, help='Time in seconds of non-communication for a node to be marked as stale')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose logging')

    args = parser.parse_args()

    if get_ntp_offset(args.ntp_server) > 60:
        exit("your clock is not in sync with NTP")

    root_logger = logging.getLogger()
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        root_logger.addHandler(file_handler)
    if args.verbose:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    queue = Queue()

    system_tasks = []

    with StatusProtocolServer(queue, args.communication_port) as loop:

        storage = Storage(args.storage_path)

        system_tasks.append(loop.create_task(storage.processor(queue)))
        system_tasks.append(loop.create_task(storage.pruner()))

        if args.storage_path:
            logger.debug("got storage path {0}".format(args.storage_path))
            system_tasks.append(loop.create_task(storage.auto_saver()))

        with Scheduler(loop, storage, args.node_staleness):

            async def timed_broadcast():
                while True:
                    await asyncio.sleep(5)
                    packets = StatusMessage(get_ip(), get_load()).dump()
                    for packet in packets:
                        client(args.communication_port, packet)

            logger.info("creating timed UDP broadcast message")
            system_tasks.append(loop.create_task(timed_broadcast()))

            # logger.info("starting web server on http://{0}:{1}/".format(get_ip(), args.web_port))
            # web_server = WebServer(args.web_port)
            # web_server.start()

            try:
                loop.run_forever()
            except:
                logger.info("interrupt received")

            # logger.info("stopping web server")
            # web_server.stop()

            logger.info("terminating")
            for task in system_tasks:
                task.cancel()

    logger.info("elvis has left the building")


if __name__ == "__main__":
    main()