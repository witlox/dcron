#!/usr/bin/env python
# -*- coding: utf-8 -*-#
#

import os
import sys

from setuptools import setup

version = "0.1"

requirements = ['flask', 'gevent', 'aiofiles']

test_requirements = ["pytest", "tox"]

if sys.argv[-1] == "tag":
    os.system("git tag -a {0} -m 'version {1}'".format(version, version))
    os.system("git push origin master --tags")
    sys.exit()

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    os.system("python setup.py bdist_wheel upload")
    sys.exit()

if sys.argv[-1] == "test":
    try:
        modules = map(__import__, test_requirements)
    except ImportError as e:
        raise ImportError("{0} is not installed. Install your test requirements.".format(
            str(e).replace("No module named ", ""))
        )
    os.system('py.test')
    sys.exit()

setup(name="dcron",
      version=version,
      description="Distributed Cronlike Scheduler",
      long_description=open("README.md").read(),
      author="Pim Witlox",
      author_email="pim@witlox.io",
      url="https://github.com/witlox/dcron",
      license="GPLv3",
      entry_points={
          "console_scripts": [
              "dcron = dcron.application:main",
          ]
      },
      packages=["dcron"],
      install_requires=requirements,
      python_requires=">=3.5",
      keywords="Python, Python3",
      project_urls={
          "Documentation": "https://dcron.readthedocs.io/en/latest/",
          "Source": "https://github.com/witlox/dcron",
          "Tracker": "https://github.com/witlox/dcron/issues",
      },
      test_suite="tests",
      tests_require=test_requirements,
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: System Administrators",
                   "Natural Language :: English",
                   "Environment :: Console",
                   "License :: OSI Approved :: MIT License",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Topic :: Software Development :: Libraries",
                   "Topic :: Utilities"],
      )
