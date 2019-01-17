#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import argparse
import asyncio
import logging
import os
import selectors
from asyncio import Queue

from dcron.dgram import StatusProtocolServer, client
from dcron.protocol import StatusMessage
from dcron.serializer import UdpSerializer
from dcron.site import WebServer
from dcron.storage import Storage
from dcron.utils import get_ip


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-8.8s]  %(message)s")
logger = logging.getLogger('dcron')


def get_load():
    try:
        return os.getloadavg()[0]
    except OSError:
        logger.warning("could not get system load")
        return 0


def get_status(storage):
    our_ip = get_ip()
    previous_status = storage.node_state(our_ip)
    if not previous_status:
        cluster_status = list(storage.cluster_state())
        if len(cluster_status) == 0:
            return StatusMessage(our_ip, get_load(), None, None, None, None)
        cloned_status = cluster_status[0]
        cloned_status.ip = our_ip
        cloned_status.load = get_load()
        cloned_status.running = None
        cloned_status.scheduled = None
        return cloned_status
    previous_status.load = get_load()
    return previous_status


def main():
    parser = argparse.ArgumentParser(description='Distributed Cronlike Scheduler')

    parser.add_argument('-l', '--log-file', default=None, help='path to store logfile (none means no logfile)')
    parser.add_argument('-s', '--storage-path', default=None, help='directory where to store cache (none means /tmp)')
    parser.add_argument('-p', '--communication-port', type=int, default=12345, help='communication port')
    parser.add_argument('-w', '--web-port', type=int, default=8080, help='web hosting port')
    parser.add_argument('-m', '--at-most-once', action='store_true', default=False, help='we use at-least-once reliability by default, toggle this to use at-most-once')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose logging')

    args = parser.parse_args()

    root_logger = logging.getLogger()
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        root_logger.addHandler(file_handler)
    if args.verbose:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    if args.storage_path:
        logger.debug("got storage path {0}".format(args.storage_path))

    queue = Queue()

    with StatusProtocolServer(queue, args.communication_port) as loop:
        with Storage(loop, queue, args.storage_path) as storage:

            async def timed_broadcast():
                while True:
                    await asyncio.sleep(5)
                    packets = UdpSerializer.dump(get_status(storage))
                    for packet in packets:
                        client(args.communication_port, packet)

            logger.info("creating timed UDP broadcast message")
            broadcast_task = loop.create_task(timed_broadcast())

            # logger.info("starting web server on http://{0}:{1}/".format(get_ip(), args.web_port))
            # web_server = WebServer(args.web_port)
            # web_server.start()

            try:
                loop.run_forever()
            except:
                logger.info("interrupt received")

            logger.info("stopping web server")
            # web_server.stop()

            logger.info("terminating timed UDP broadcast")
            broadcast_task.cancel()

    logger.info("elvis has left the building")


if __name__ == "__main__":
    main()
