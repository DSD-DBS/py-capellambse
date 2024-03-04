..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

Migrating from capellambse v0.5 to v1.0
=======================================

For all users
-------------

- Several classes and functions were renamed and/or moved or were replaced by
  other classes and functions; see :ref:`the table below <migrate-1.0-moves>`
  for details.

- The Model class (formerly MelodyModel) no longer has an *info* attribute. Use
  the relevant attributes directly on the model instance, or the information
  exposed through the *Model.metadata* attribute instead.

  Some of these attributes don't have a direct equivalent in the new API. Most
  notably, information on where the model was loaded from now needs to be
  directly obtained from the underlying file handler(s), which are available
  through the *resources* dictionary. The primary file handler (the one which
  the *entrypoint* is looked up in) has the key ``"\x00"`` (a string containing
  a single null byte), all others have the keys as given to the *resources*
  argument.

- The System Analysis layer is now consistently referred to as "sa" in the API,
  instead of a mixture between "sa" (the user-facing name) and "ctx" (the
  internal name).

- Attributes which were previously deprecated have now been removed. Please
  refer to the documentation of :mod:`capellambse.metamodel` for more
  information on which attributes are available.

- Several attributes have been renamed to better match the Capella metamodel.
  Please refer to the documentation of :mod:`capellambse.metamodel` for more
  details.

  The general naming scheme is now as follows:

  - *camelCase* in the Capella metamodel is converted to *snake_case* in
    capellambse.

  - The *owned* and *allocated* prefixes are removed, e.g. *ownedFunctions*
    becomes *functions* and *allocatedFunctionalChains* becomes
    *functional_chains*.

  - Exceptions apply for attributes where this would cause a naming conflict;
    see the individual classes' documentation for details.

- Hashing of model objects was previously deprecated and has now been removed.
  This means it is no longer possible to use model objects as keys in
  dictionaries or sets. Instead, use the *uuid* attribute, which is guaranteed
  to be unique, or the relevant attribute(s) like *name*.

- Objects that are not yet supported by capellambse are now represented by
  *Alien* instances. The presence of Aliens causes a loaded model to be unable
  to be saved back to avoid data loss and prevent corruption, and may cause
  errors or inconsistent behavior when trying to inspect them at runtime.
  Warnings will be issued if Alien objects are encountered while loading a
  model. Passing the optional argument ``xenophobia=True`` or defining the
  environment variable ``CAPELLAMBSE_XENOPHOBIA`` will cause these warnings to
  be treated as errors, making the model fail to load. It is recommended to use
  this option in CI which modifies models, in order to fail fast if saving
  would fail anyways.

  The REPL has gained a new ``--xenophobia`` option which can be used to
  enable this behavior as well.

  This behavior also applies when the loaded model uses extensions that are
  either not implemented or not installed locally. Please make sure to install
  all required extensions before loading a model.

  If you encounter Aliens in your model which are not part of an extension,
  please open an issue on GitHub.

- The *MixedElementList* class was removed. This class previously handled
  ElementList cases where elements of more than one type appeared in a single
  list. The most notable difference for end users here is that the *by_type*
  method no longer has different semantics depending on which attribute is
  queried: It will always look at the *type* attribute on the contained
  elements (discarding ones that don't have a *type*). To filter by the class
  name, use *by_xtype* instead, which will always look at the ``xsi:type``.

- The *update_diagram_cache* method on the main Model class was removed. Use
  one of these alternatives instead:

  1. The diagram cache update CLI.

     .. code:: bash

        python -m capellambse.diagram_cache -m my_model.aird

  2. One of the CI templates, documented in the *ci-templates* directory in the
     repository.

- Attributes which used to return *markupsafe.Markup* objects (most notably,
  the *description* attributes of all object types) now return HTML element
  trees instead. These trees currently cannot be modified in place; they have
  to be modified and then reassigned to the attribute, like so:

  .. code:: python

     obj = model.by_uuid("...")
     tree = obj.description
     tree.append(tree.makeelement(...))  # make changes

  If you intend to modify the HTML tree, but don't want the changes to be
  preserved when calling `model.save()` or be otherwise visible through the
  model, make a deep copy of the tree:

  .. code:: python

     from copy import deepcopy
     my_tree = deepcopy(obj.description)
     my_tree.append(my_tree.makeelement(...))
     assert obj.description != my_tree

  The objects returned by these attributes will also coalesce to *Markup* if
  used like a string. This preserves simple use in Jinja templates, like the
  following:

  .. code:: htmldjango

     <h2>Description</h2>
     {{ obj.description }}

  The actual element tree returned from the attribute will be enriched with a
  wrapping `<div class="html-content">` element. This element's *.text*
  contains the text before the first child element, if there was any. This
  additional element will not be included when coalescing the tree to a *str*
  or *Markup* object.

  Assignments to these model object attributes accept either:

  - A plain *str*
  - A *markupsafe.Markup* object, or
  - An *etree._Element*

  Plain *str* objects will be interpreted as normal text, and therefore will
  automatically be escaped in HTML contexts:

  .. code:: python

     new_value = "I <3 Capella"
     obj.description = new_value
     print(obj.description)
     # output: I &lt;3 Capella

  To pass in serialized HTML, make sure it is marked with the
  *markupsafe.Markup* class. Markup passed in this way will be loaded as HTML
  tree at assignment time and returned as normal.

  .. code:: python

     from markupsafe import Markup
     new_value = Markup("<p>Believe <small>me</small></p>")
     print(obj.description)
     # output: <p>Believe <small>me</small></p>

  When assigning an *etree._Element* instance, a copy of the tree will be
  stored in the model and used for the description. This is necessary to
  preserve the aforementioned guarantee of a single, specific root element.

  .. code:: python

     new_value = etree.Element("p")
     obj.description = new_value
     assert obj.description is not new_value

For advanced users and developers
---------------------------------

- capellambse no longer works with in-memory XML trees. This has large
  implications for anyone who used to work with the XML trees directly
  (sometimes also called the "low-level API"). XML is now only used for
  serialization and deserialization, and the loaded model now uses a custom
  data structure. The descriptors exposing the data are defined in the
  *capellambse.model._obj* module, and the metamodel classes using those
  descriptors are now defined in *capellambse.metamodel* submodules.

- The old Accessor classes were removed in favor of new, more powerful
  relationship descriptor classes. These are defined in
  :mod:`capellambse.model`, and implement the three object relationship types
  that are used in the Capella metamodel:
  :class:`~capellambse.model.Containment` (i.e. the parent-child relationship),
  :class:`~capellambse.model.Association` (which is serialized as XML
  attribute) and :class:`~capellambse.model.Allocation` (serialized as a child
  element whose only purpose is to refer to another object). Please refer to
  the documentation of these classes for more detailed information.

  Code that changes how relationships present to the user (previously by
  subclassing an *Accessor*) should now use one or more of these three classes
  (directly, without subclassing), and use the Python descriptor interface to
  make use of them. More details can be found in their individual
  documentation, as well as in other related classes, like
  :class:`~capellambse.model.Backref`, :class:`~capellambse.model.Shortcut`,
  :class:`~capellambse.model.TypeFilter` and
  :class:`~capellambse.model.Single`.

- Relationship descriptors must keep track of inserted and removed objects be
  calling the :meth:`~capellambse.model.Model._register` and
  :meth:`~capellambse.model.Model._unregister` methods as necessary; see their
  documentation for more details.

  The :class:`~capellambse.model.CoupledElementList` and
  :class:`~capellambse.model.RefList` classes provide a convenient way to
  implement this behavior.

- We now distinguish between the *Project* or *Library* object (which is a
  regular model element) and the *Model* as specified the user. A *Model* may
  contain multiple *Project* and/or *Library* instances, which are usually
  loaded from different ``*.capella`` and/or ``*.afm`` files. Previously the
  *MelodyModel* instantiated by the user would represent the top-level
  *Project* or *Library* instance, however this approach made the other
  instances unnecessarily difficult to deal with.

- The way how AIRD files (and diagrams in them) are loaded was changed. Instead
  of loading the entire AIRD file into memory, we now only load the "DAnalysis"
  section, which contains metadata about the model files and diagrams in each
  file. Diagrams themselves are only loaded once they are actually needed.

- The auditing feature using *sys.audit* and *sys.addaudithook* was removed.
  The audit events are no longer fired, and the *capellambse.auditing* module
  has been removed.

  Auditing of accessed and modified model object attributes never really worked
  to begin with, but caused a lot of headaches when maintaining and extending
  capellambse. It also had a few drawbacks that were difficult or impossible to
  work around. The most important one of these is that the *sys.audit* facility
  by design doesn't offer a way to remove a hook again when it's no longer
  needed. This means that, whenever one of the aforementioned auditor classes
  was used, the memory for that instance would be leaked - and if there's no
  proper cleanup, this might include the entire model as well.

  There are currently no plans to re-add this functionality to capellambse.

.. migrate-1.0-moves:

Overview for migrating downstream code
--------------------------------------

This table shows which classes and functions were renamed or have a new
equivalent with similar functionality.

.. list-table::
   :header-rows: 1

  * - Old class / function
    - Replacement
  * - *capellambse.loader.core*
    - Removed.
  * - *capellambse.loader.exs*
    - Moved to :mod:`capellambse.exs`.
  * - *capellambse.loader.modelinfo*
    - Partially replaced by :class:`capellambse.filehandler.abc.HandlerInfo`.
  * - *capellambse.loader.xmltools*
    - Removed, but also see the ``AttributeProperty`` related classes below.
  * - *capellambse.model.common*
    - Generally moved to :mod:`capellambse.model`; see below for details.
  * - *capellambse.model.layers*, *capellambse.model.crosslayer*
    - Moved to :mod:`capellambse.metamodel` (some submodules were renamed).
  * - *capellambse.model.common.set_accessor*,
      *capellambse.model.common.set_self_references*
    - :func:`capellambse.model.add_descriptor`
  * - *capellambse.model.common.build_xtype*
    - Removed.
  * - *capellambse.model.common.xtype_handler*
    - Removed; inherit from
      :class:`capellambse.metamodel.modellingcore.ModelElement`.
  * - *capellambse.model.MelodyModel*
    - :class:`capellambse.model.Model`
  * - *MelodyModel.info*
    - Use the needed information directly from
      :attr:`~capellambse.model.Model.metadata` and from the FileHandler
      objects at :attr:`~capellambse.model.Model.resources`.
  * - Abstract base classes from *capellambse.model.common.accessors*:
      *Accessor*, *WritableAccessor*, *PhysicalAccessor*
    - Removed.
  * - *capellambse.model.common.accessors.DeprecatedAccessor*
    - Removed, but might be readded if needed.
  * - *capellambse.model.common.accessors.RoleTagAccessor*,
      *capellambse.model.common.accessors.DirectProxyAccessor*
    - :class:`capellambse.model.Containment`
  * - *capellambse.model.common.accessors.DeepProxyAccessor*
    - Removed. Use a ``@property`` instead.
  * - *capellambse.model.common.accessors.AttrProxyAccessor*
    - :class:`capellambse.model.Association`
  * - *capellambse.model.common.accessors.PhysicalLinkEndsAccessor*
    - Removed. Use an :class:`~capellambse.model.Association` with a fixed-size
      ElementList.
  * - *capellambse.model.common.accessors.IndexAccessor*
    - Removed. Use a ``@property`` instead.
  * - *capellambse.model.common.accessors.AlternateAccessor*
    - Removed.
  * - *capellambse.model.common.accessors.ParentAccessor*
    - Removed; implicitly tracked as ``ModelElement._parent``.
  * - *capellambse.model.common.accessors.CustomAccessor*
    - Removed.
  * - *capellambse.model.common.accessors.AttributeMatcherAccessor*
    - Removed.
  * - *capellambse.model.common.accessors.ReferenceSearchingAccessor*
    - :class:`capellambse.model.Backref`
  * - *capellambse.model.common.accessors.TypecastAccessor*
    - :class:`capellambse.model.TypeFilter`
  * - *capellambse.model.common.accessors.ElementListCouplingMixin*
    - A :class:`~capellambse.model.ModelCoupler` used as storage for an
      :class:`~capellambse.model.ElementList`.
  * - *capellambse.model.common.element.attr_equal*
    - Use the ``eq`` keyword argument when inheriting from
      :class:`~capellambse.model.ModelElement`:

      .. code:: python

         class MyElement(ModelElement, eq="my_attribute"):
             pass

  * - *capellambse.model.common.element.ModelObject*,
      *capellambse.model.common.element.GenericElement*
    - :class:`capellambse.model.ModelElement` (also exposed as
      :class:`capellambse.metamodel.modellingcore.ModelElement`).

      When checking classes not covered by the loaded metamodel, use
      ``isinstance`` with :class:`~capellambse.model.Alien` instead:

      .. code:: python

         # old
         if type(obj) is GenericElement: ...
         # new
         if isinstance(obj, Alien): ...

  * - *capellambse.model.common.element.ElementList*
    - :class:`capellambse.model.ElementList`
  * - *capellambse.model.common.element.CachedElementList*
    - Removed.
  * - *capellambse.model.common.element.MixedElementList*
    - Removed.
  * - *capellambse.model.common.properties.AttributeProperty*
    - When used as descriptor: :class:`capellambse.model.StringPOD`,
      when used as ABC: :class:`capellambse.model.AbstractPOD`.
  * - *capellambse.model.common.properties.HTMLAttributeProperty*
    - :class:`capellambse.model.HTMLPOD`
  * - *capellambse.model.common.properties.NumericAttributeProperty*
    - :class:`capellambse.model.IntPOD` or
      :class:`capellambse.model.FloatPOD`
  * - *capellambse.model.common.properties.BooleanAttributeProperty*
    - :class:`capellambse.model.BoolPOD`
  * - *capellambse.model.common.properties.DatetimeAttributeProperty*
    - :class:`capellambse.model.DateTimePOD`
  * - *capellambse.model.common.properties.EnumAttributeProperty*
    - :class:`capellambse.model.EnumPOD`
