..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

**********************************
Introduction to py-capellambse API
**********************************

|project| provides access to model elements using a meta-model similar to the
one of Capella. However in this meta-model we make a few simplifications. A
collection of automated tests and design reviews help us to ensure that those
simplifications don't break compatibility with original Capella models (however
coverage isn't complete yet).

As you may know the meta-model behind Capella is layered. There are many
packages involved and there is a long inheritance chain behind almost every
model element. We are simplifying that by "flattening" the lower layers.

You may see an example of how that works in the figure below:

.. image:: ../_static/img/crosslayer_intro.jpg

In the example above we see that `LogicalFunction` is a subtype of
`AbstractFunction`, just like `SystemFunction` or `OperationalActivity`.
Because of that, all of those subtypes can be `.available_in_states` or have a
layer-specific structural `owner`, like `LogicalComponent` for
`LogicalFunction`. Any layer-specific class that inherits from `Component` may
also have `state_machines`.

The API reference part of this documentation provides you with the complete (as
it is generated from the code base) list of available methods and attributes.

Layer-specific packages
=======================

The following packages enable working with model layers:

* :mod:`capellambse.metamodel.oa` - covers Operational Analysis layer.
* :mod:`capellambse.metamodel.sa` - covers System Analysis layer.
* :mod:`capellambse.metamodel.la` - covers Logical Architecture layer.
* :mod:`capellambse.metamodel.pa` - covers Physical Architecture layer.

Cross-layer packages
====================

The following packages enable all (almost) of the layer packages:

* :mod:`capellambse.metamodel.fa` - covers Functional Analysis concerns,
  defines things like AbstractFunction or FunctionalExchange
* :mod:`capellambse.metamodel.cs` - covers Composite Structure concerns,
  defines things like Component
* :mod:`capellambse.metamodel.capellacommon` - covers common concerns,
  defines things like StateMachine, State
* :mod:`capellambse.metamodel.information` - covers Information
  concerns, defines things like Class, DataPkg, ExchangeItem

Extension packages
==================

* :mod:`capellambse.extensions.reqif` - provides means for working with ReqIF
  Requirements within Capella model.
* :mod:`capellambse.extensions.pvmt` - provides means for working with object
  attributes created with PVMT package.
