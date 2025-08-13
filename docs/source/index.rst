..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
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

.. code:: python

   >>> import capellambse
   >>> model = capellambse.MelodyModel("git+https://github.com/dbinfrago/coffee-machine.git")
   >>> model.search("SystemFunction").by_name("make coffee")
   <SystemFunction 'make coffee' (8b0d19df-7446-4c3a-98e7-4a739c974059)>
   .available_in_states = [0] <State 'Ready for request' (15e28744-1a3b-41ce-a2ee-28fb33ed3bda)>
   .context_diagram = <Diagram 'Context of make coffee'>
   .inputs = [0] <FunctionInputPort 'FIP 1' (9a409efc-75bc-44b5-8888-8abefebc69d0)>
             [1] <FunctionInputPort 'FIP 1' (fac29291-c465-4130-a95b-8dbdd8a9a5cf)>
   .is_leaf = True
   .kind = <FunctionKind.FUNCTION: 'FUNCTION'>
   .layer = <SystemAnalysis 'System Analysis' (fe55c3c2-28d3-4d80-b54d-aae12cdc6bc6)>
   .name = 'make coffee'
   .outputs = [0] <FunctionOutputPort 'FOP 1' (2bd6785b-08ff-4108-b6f0-c8fd94ab08c0)>
              [1] <FunctionOutputPort 'FOP 2' (1dc12e9d-14f6-494f-9dfc-867635951e91)>
              [2] <FunctionOutputPort 'FOP 3' (c87688f6-adc7-45e2-b254-8f22e85fec4b)>
   .parent = <SystemFunction 'Root System Function' (eff8d0b0-84df-431e-aec8-66150a0b1365)>
   .pvmt = <Property Value Management for <SystemFunction 'make coffee' (8b0d19df-7446-4c3a-98e7-4a739c974059)>>
   .realization_view = <Diagram 'Realization view of make coffee'>
   .uuid = '8b0d19df-7446-4c3a-98e7-4a739c974059'
   .visible_on_diagrams = [0] <Diagram '[ES] make coffee'>
                          [1] <Diagram '[ES] make coffee (refined)'>
                          [2] <Diagram '[SDFB] make coffee'>
                          [3] <Diagram '[SAB] make coffee'>
   .xtype = 'org.polarsys.capella.core.data.ctx:SystemFunction'

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
   start/specifying-models
   start/envvars
   start/intro-to-api
   start/declarative
   start/migrating-0.6

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
