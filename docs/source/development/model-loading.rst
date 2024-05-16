..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

***************************
 The model loading process
***************************

.. warning::

   This page relates to the experimental ``capellambse.modelv2`` and
   ``capellambse.metamodel`` modules, and the process described here may change
   at any time.

.. note::

   This page documents the loading process of **|project|**; it is not
   representative for Capella (the Java-based GUI modelling tool).

Loading a model is a multi-step process. The following steps are performed:

1. All resources (the ``path`` and all entries in the passed ``resources``
   dict) are loaded by constructing appropriate
   :py:class:`capellambse.filehandler.FileHandler` instances. The file handler
   class is loaded from the ``capellambse.filehandler`` entry point group, and
   is selected by matching the resource URI's scheme to the entry point's name.
   Only the first matching entry point is used.

2. The ``entrypoint`` is loaded from the default resource, i.e. the one passed
   in through the ``path`` argument. The entrypoint may be automatically
   determined if it wasn't specified explitily; see :ref:`specifying-models`
   for more details.

   The ``DAnalysis`` section of the entry point is then loaded. This section
   contains metadata about the diagrams in this AIRD fragment, as well as
   references to "semantic resources", which contain the actual semantic model.

   The primary logic for this resides in the
   ``capellambse.model._xml.load`` function, which is called near the end
   of the :class:`capellambse.modelv2.Model` constructor.

3. The ``*.afm`` file referenced in the ``entrypoint`` contains an additional
   section with metadata like the referenced viewpoints, which is necessary to
   load the correct classes from the metamodel. This section is now searched
   and loaded.

4. All model objects are loaded into memory from the remaining semantic
   resources. This includes optionally existing trees in ``*.afm`` files, as
   well as all referenced trees from other linked projects, such as ones
   brought in using REC/RPL.

   This is implemented by chaining into
   ``capellambse.modelv2._obj.load_object`` from the above ``_xml.load``
   function. This function loads each XML tree, determines the appropriate
   class for the tree's root object (for the main fragment usually either
   :class:`~capellambse.metamodel.capellamodeller.Project` or
   :class:`~capellambse.metamodel.capellamodeller.Library`), and calls its
   ``_parse_xml`` method.

   The default implementation of ``_parse_xml`` is in the
   :class:`capellambse.modelv2.ModelObject` class, which all (semantic) model
   objects must inherit from. It calls the ``from_xml`` methods of all of its
   attribute descriptors, which in turn may recurse into ``_parse_xml`` of
   other model objects to load nested child elements. Descriptors that
   represent non-containment relations to other elements must store enough
   information from the XML to be able to resolve the references in the next
   step, as the XML element tree will not be available then anymore.

5. Now that all model elements have been instantiated, references to other
   elements are resolved. This is accomplished by walking the resulting trees
   of objects and calling the ``resolve`` methods of all descriptors, with the
   object instance as argument.

   This mechanism is used for example by
   :class:`~capellambse.modelv2.Allocation` to resolve forward references, and
   by :class:`~capellambse.modelv2.Containment` to re-inline fragmented
   children.

   The descriptors themselves must implement a ``resolve`` method, which is
   called with the model object (not just its UUID) as the only argument.

.. vim:set tw=79:
