..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

*****************************
Welcome to the documentation!
*****************************

Python Capella MBSE Tools
=========================

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Black

**Date**: |today| **Version**: |Version|

Description
-----------

This library was designed to enable and support Model Based System Engineering
using Polarsys' Capella_ with Python. Common usage for this API:

* parsing .aird files
* easy access to model elements and objects
* property-value access and manipulation
* diagram access and export as SVG

Additionally and as a core idea it provides an interface for the underlying
database of the Capella model.

Since v0.5, it also supports a simple, but powerful :ref:`declarative modelling
language <declarative-modelling>`, which is based on the API for the semantic
model.

If you want a quickstart at how to use this package, head right into the
:ref:`how-tos section <howtos>`.

.. toctree::
   :caption: Start
   :maxdepth: 1
   :titlesonly:

   start/installation
   start/intro-to-api
   start/declarative
   start/audit-events

.. toctree::
   :caption: Tutorials
   :titlesonly:

   howtos/howtos

.. toctree::
   :caption: API reference
   :maxdepth: 4

   code/modules

.. toctree::
   :caption: Integration with other tools
   :maxdepth: 2

   tools/sphinx-extension.rst

.. toctree::
   :caption: Development
   :maxdepth: 2

   development/low-level-api
   development/how-to-explore-capella-mm
   development/developing-docs
   development/repl

.. _Capella: https://www.eclipse.org/capella/
