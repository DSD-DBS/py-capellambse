************
Installation
************

.. |project| replace:: Python capella MBSE Tools

This guide helps you to install |project| onto your computer.
There are two ways for installation. They are as follows.

Install from PyPI (Recommended)
===============================

.. highlight:: bash

Installing |project| is simple with `pip <http://www.pip-installer.org/>`_::

    $ pip install pycapellambse

If PyPI is down, you can also install |project| from one of the mirrors::

    $ pip install --use-mirrors pycapellambse

Install manually
================

From GitLab
-----------

Alternatively, you may wish to download manually from GitLab where |project|
is `actively developed <https://gitlab.com/our_url_here>`_.

You can clone the public repository::

    $ git clone git@gitlab.com:our_url_here.git

Or download an appropriate zipball_.

.. _zipball:
   https://gitlab.com/our_url_here/repository/archive.zip?ref=master

Once you have a copy of the source, you can embed it in your Python package,
or install it into your site-packages::

    $ python setup.py install

From wheel
----------

As another alternative you can download a .whl file from GitLab and install
|project| via pip::

    $ pip install path-to-whl/capellambse.whl

.. _manual:
   https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
.. _github:
   https://www.github.com/our_repo_link_here

.. note::
    If you have your python distribution from anaconda open the anaconda prompt.
    If you want to install this package in your virtual environment, make sure
    that your prompt shows the activated environment in parantheses.
    Here is a manual_ for this.
