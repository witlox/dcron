#Distributed Cronlike Scheduler [![Build Status](https://travis-ci.org/witlox/dcron.svg?branch=master)](https://travis-ci.org/witlox/dcron)

The aim of dcron is to offer [cron](https://en.wikipedia.org/wiki/Cron) like behaviour spanning multiple machines. 
The system offers a web interface to manage your jobs, and reports the health of the cluster. 
Everything is self contained, so you only need to start the system to have a working setup. 
We do however recommend that you run the system behind a reverse proxy, since there is no authentication mechanism.
Please check the [docs](https://dcron.readthedocs.io) regarding installation, configuration and options.  

## Details

- dcron requires Python 3.7+ in order to work.
- all nodes running dcron need to have the same software installed you want dcron to run
- dcron runs tasks at-most-once (according to schedule)

## Installation

```bash
pip install dcron
```

## Options

- -l or --log-file: by default we only log to stdout/stderr, specify a path and a log file will be created
- -p or --storage-path: we cache our stuff directly in memory, if you wan't your runtime configuration to be saved, specify a folder here
- -c or --communication-port: udp broadcast is used for synchronization between nodes, specify a port here (default: 12345)
- -w or --web-port: port to host the web interface (default: 8080)
- -n or --ntp-server: given that we are doing cron, we need time sync to be relatively close, if skewed, we break (default: pool.ntp.org) 
- -s or --node-staleness: after x seconds of inactivity a node is marked stale and jobs are redistributed over active nodes
- -v or --verbose: more logging