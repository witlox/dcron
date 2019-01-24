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
import time

from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime

from aiohttp.web_runner import AppRunner, TCPSite

from dcron.datagram.client import client
from dcron.datagram.server import StatusProtocolServer
from dcron.protocols.rebalance import Rebalance
from dcron.protocols.status import StatusMessage
from dcron.scheduler import Scheduler
from dcron.site import Site
from dcron.storage import Storage
from dcron.utils import get_ip, get_ntp_offset, get_load

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-8.8s]  %(message)s")
logger = logging.getLogger('dcron')


def main():
    parser = argparse.ArgumentParser(description='Distributed Cronlike Scheduler')

    parser.add_argument('-l', '--log-file', default=None, help='path to store logfile')
    parser.add_argument('-p', '--storage-path', default=None, help='directory where to store cache')
    parser.add_argument('-c', '--communication-port', type=int, default=12345, help='communication port (default: 12345)')
    parser.add_argument('-w', '--web-port', type=int, default=8080, help='web hosting port (default: 8080)')
    parser.add_argument('-n', '--ntp-server', default='pool.ntp.org', help='NTP server to detect clock skew (default: pool.ntp.org)')
    parser.add_argument('-s', '--node-staleness', type=int, default=180, help='Time in seconds of non-communication for a node to be marked as stale (defailt: 180s)')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose logging')

    args = parser.parse_args()

    if get_ntp_offset(args.ntp_server) > 60:
        exit("your clock is not in sync (check system NTP settings)")

    root_logger = logging.getLogger()
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        root_logger.addHandler(file_handler)
    if args.verbose:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)

    pool = ThreadPoolExecutor(4)

    storage = Storage(args.storage_path)

    with StatusProtocolServer(storage, args.communication_port) as loop:

        running = True

        scheduler = Scheduler(storage, args.node_staleness)

        def timed_broadcast():
            while running:
                time.sleep(5)
                packets = StatusMessage(get_ip(), get_load()).dump()
                for packet in packets:
                    client(args.communication_port, packet)
                for job in storage.cron_jobs():
                    for packet in job.dump():
                        client(args.communication_port, packet)

        def timed_schedule():
            while running:
                time.sleep(60)
                if not scheduler.check_cluster_state():
                    logger.info("rebalanced cluster")
                    jobs = storage.cron_jobs().copy()
                    for packet in Rebalance().dump():
                        client(args.communication_port, packet)
                    for job in jobs:
                        for packet in job.dump():
                            client(args.communication_port, packet)

        async def scheduled_broadcast():
            await loop.run_in_executor(pool, timed_broadcast)

        async def scheduled_rebalance():
            await loop.run_in_executor(pool, timed_schedule)

        async def scheduled_schedule():
            while running:
                await scheduler.check_jobs(datetime.utcnow())
                await asyncio.sleep(15)

        loop.create_task(scheduled_broadcast())
        loop.create_task(scheduled_rebalance())
        loop.create_task(scheduled_schedule())

        logger.info("starting web application server on http://{0}:{1}/".format(get_ip(), args.web_port))

        s = Site(storage, args.communication_port)
        runner = AppRunner(s.app)
        loop.run_until_complete(runner.setup())
        site_instance = TCPSite(runner, port=args.web_port)
        loop.run_until_complete(site_instance.start())

        try:
            loop.run_forever()
        except:
            logger.info("interrupt received")

        logger.info("stopping web application")
        loop.run_until_complete(site_instance.stop())

        running = False

        if args.storage_path:
            loop.create_task(storage.save())

        logger.debug("waiting for background tasks to finish")
        pending_tasks = [task for task in asyncio.Task.all_tasks() if not task.done()]
        loop.run_until_complete(asyncio.gather(*pending_tasks))

    logger.info("elvis has left the building")


if __name__ == "__main__":
    main()
