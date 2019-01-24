.. dcron documentation master file, created by
   sphinx-quickstart on Thu Jan 24 13:44:01 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to dcron's documentation!
=================================

The aim of dcron is to offer cron like behaviour spanning multiple machines.
The system offers a web interface to manage your jobs, and reports the health of the cluster.
Everything is self contained, so you only need to start the system to have a working setup.
We do however recommend that you run the system behind a reverse proxy, since there is no authentication mechanism.
Please check the [docs]() regarding installation, configuration and options.

Installing the package
======================
You need python 3.7 or higher to run this package. The package can be installed using ``pip install dcron``.

Running the package
===================
Our package is self contained, so you can start it by simply calling dcron.

usage: dcron [-h] [-l LOG_FILE] [-p STORAGE_PATH] [-c COMMUNICATION_PORT]
             [-w WEB_PORT] [-n NTP_SERVER] [-s NODE_STALENESS] [-v]

Distributed Cronlike Scheduler

optional arguments:
  -h, --help            show this help message and exit
  -l LOG_FILE, --log-file LOG_FILE
                        path to store logfile
  -p STORAGE_PATH, --storage-path STORAGE_PATH
                        directory where to store cache
  -c COMMUNICATION_PORT, --communication-port COMMUNICATION_PORT
                        communication port (default: 12345)
  -w WEB_PORT, --web-port WEB_PORT
                        web hosting port (default: 8080)
  -n NTP_SERVER, --ntp-server NTP_SERVER
                        NTP server to detect clock skew (default:
                        pool.ntp.org)
  -s NODE_STALENESS, --node-staleness NODE_STALENESS
                        Time in seconds of non-communication for a node to be
                        marked as stale (defailt: 180s)
  -v, --verbose         verbose logging

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
