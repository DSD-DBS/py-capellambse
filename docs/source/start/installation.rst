..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

************
Installation
************

.. |project| replace:: py-capellambse

This guide helps you to get |project| installed. There are a few ways to get it done:

Install from PyPI
=================

.. highlight:: bash

Installing |project| from Python Package Index via `pip <http://www.pip-installer.org/>`_ is the quickest way to get started ::

    $ pip install capellambse

Install as a package from Github
================================

If you want to have a comfortable playground with examples / jupyter notebooks / export to excel demo and test models you may clone the repository directly from github, create virtual environment and install all the extras: ::

    $ git clone https://github.com/DSD-DBS/py-capellambse.git
    $ cd py-capella-mbse
    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ pip install .
    $ pip install jupyter
    $ cd examples
    $ jupyter-notebook

Install for development
=======================

In case you'd like to contribute to the development or improve documentation, sample models or examples collection please follow the `contribution guide <https://github.com/DSD-DBS/py-capellambse/blob/master/CONTRIBUTING.md>`_
