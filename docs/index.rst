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
Please check the configuration page regarding installation, configuration and options.

Installing the package
======================
You need python 3.7 including development libraries or higher to run this package. The package can be installed using ``pip install dcron``.

Running the package
===================
Our package is self contained, so you can start it by simply calling dcron.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   configuration



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
