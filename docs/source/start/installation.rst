..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

************
Installation
************

.. image:: https://img.shields.io/pypi/pyversions/capellambse
   :target: https://pypi.org/project/capellambse/
   :alt: PyPI - Python Version

This guide helps you to get |project| installed. There are a few ways to get it
done:

Install from PyPI
=================

Installing |project| from Python Package Index via pip__ is the quickest way to
get started.

__ http://www.pip-installer.org/

.. code:: bash

   pip install capellambse

Windows
=======

If you intend to use |project|'s PNG export functionality, you need a working
installation of cairosvg__. Unfortunately, the Windows wheels on PyPI do not
ship with all necessary libraries. However, they can be manually installed with
the `GTK for Windows Runtime Environment Installer`__.

__ https://pypi.org/project/CairoSVG/
__ https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

This should give you a fully functioning |project|.

Install as a package from Github
================================

If you want to have a comfortable playground with examples / Jupyter notebooks
/ export to excel demo and test models you may clone the repository directly
from Github, create a virtual environment and install all the extras:

.. code-block:: bash

   git clone https://github.com/DSD-DBS/py-capellambse.git
   cd py-capellambse
   python3 -m venv .venv
   source .venv/bin/activate
   pip install .
   pip install jupyter
   cd examples
   jupyter-notebook

Install for development
=======================

In case you'd like to contribute to the development or improve documentation,
sample models or examples collection please follow the `contribution guide`__.

__ https://github.com/DSD-DBS/py-capellambse/blob/master/CONTRIBUTING.md
