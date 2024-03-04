..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

*************************
The model loading process
*************************

.. note::

   This page documents the loading process of **|project|**; it is not
   representative for Capella (the Java-based GUI modelling tool).

Loading a model is a multi-step process. The following steps are
performed:

1. All resources (the ``path`` and all entries in the passed
   ``resources`` dict) are loaded by constructing appropriate
   :py:class:`capellambse.filehandler.FileHandler` instances. The file
   handler class is loaded from the ``capellambse.filehandler`` entry
   point group, and is selected by matching the resource URI's scheme to
   the entry point's name. Only the first matching entry point is used.

2. The ``entrypoint`` is loaded from the ``path`` resource. (The
   entrypoint may be automatically determined if not specified
   explitily; see :ref:`specifying-models` for details.)

   The ``DAnalysis`` section of the entry point is then loaded. This
   section contains metadata about the diagrams in this AIRD fragment,
   as well as references to "semantic resources", which contain the
   actual semantic model.

   The primary logic for this resides in the
   :func:`capellambse.model._xml.load` function, which is called from
   the :class:`capellambse.model.Model` constructor.

3. The first referenced ``*.afm`` file contains an additional section
   with metadata like the referenced viewpoints, which is necessary to
   load the correct classes from the metamodel. This section is now
   searched and loaded.

4. All model objects are loaded into memory from the remaining semantic
   resources. This includes optionally existing trees in the first (and
   other) ``*.afm`` files, as well as all referenced trees from other
   linked projects, such as ones brought in using REC/RPL.

   This is implemented by chaining into
   :func:`capellambse.model._obj.load_object` from the above
   ``_xml.load`` function. This function loads each XML tree, determines
   the appropriate class for the tree's root object (for the main
   fragment usually either :class:`capellambse.metamodel.core.Project`
   or :class:`capellambse.metamodel.core.Library`), and calls its
   ``_parse_xml`` method.

   The default implementation of ``_parse_xml`` is in the
   :class:`capellambse.model.ModelObject` class, which all (semantic)
   model objects should inherit from. It calls the ``from_xml`` methods
   of all of its attribute descriptors, which in turn may recurse into
   ``_parse_xml`` of other model objects to load nested child elements.

   During this stage, a set is passed around that contains information
   about unresolvable references, which is used in the next step.
   Descriptors can register for a callback by adding a tuple of
   ``("uuid", "attribute")`` to the set.

5. Now that all model elements have been instantiated, attributes and
   properties that registered for a callback in the previous step are
   revisited. This mechanism is used for example by
   :class:`capellambse.model._obj.Allocation` to resolve forward
   references, and by :class:`capellambse.model._obj.Containment` to
   re-inline fragmented children.

   The descriptors themselves must implement a ``resolve`` method, which
   is called with the model object (not just its UUID) as the only
   argument.
