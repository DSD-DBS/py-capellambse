..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

*************
Low-level API
*************

.. py:currentmodule:: capellambse.loader.core

The high level :py:class:`~capellambse.model.MelodyModel`-based API is largely
manually designed, and therefore sometimes does not cover all interesting
objects to a usable level. While we are constantly working on improving the
situation, it's also possible to use the low-level API based directly on the
XML files in order to temporarily work around these shortcomings. This
documentation sheds some light on the inner workings of this low-level API.

In order to effectively work with it, you need to understand the basics of XML.
It also helps to be familiar with LXML_, which is used to parse and manipulate
the XML trees in memory.

Unfortunately it's not possible to use LXML's built-in XML serializer. It
produces different whitespace in the XML tree, which confuses Capella's XML
diff-merge algorithm. This is why |project| ships with a custom serializer that
produces the same output format as Capella. It resides in the
:py:mod:`capellambse.loader.exs` module.

.. _LXML: https://lxml.de/

The MelodyLoader object
=======================

While the main object of interest for the high-level API is the
:py:class:`capellambse.model.MelodyModel` class, for the low-level API it is
the :py:class:`capellambse.loader.core.MelodyLoader`. It offers numerous
methods to search elements, resolve references, ensure model integrity during
certain modifications, and many more.

The following sections categorize and document the various methods.

The ``MelodyLoader`` closely works together with its auxiliary class
:py:class:`~capellambse.loader.core.ModelFile`. However, the ``ModelFile``
mainly plays a role while loading or saving a model from/to disk (or other data
stores), and isn't used much when interacting with an already loaded model.

.. _api-level-shift:

Shifting between API levels
===========================

High to low-level shift
-----------------------

Every model object (i.e. instance of ``GenericElement`` or one of its
subclasses) has an attribute ``_element``, which holds a reference to the
corresponding :py:class:`lxml.etree._Element` instance. The low-level API works
directly with these ``_Element`` instances.

The ``MelodyModel`` object stores a reference to the
:py:class:`~capellambse.loader.core.MelodyLoader` instance.

Low to high-level shift
-----------------------

The GenericElement class offers the
:py:meth:`~capellambse.model.common.element.GenericElement.from_model` class
method, which takes a ``MelodyModel`` instance and a low-level LXML
``_Element`` as arguments and constructs a high-level API proxy object from
them. This is the way "back up" to the high-level API.

.. note::

   Always call ``from_model`` on the base ``GenericElement`` class, not on its
   subclasses. The base class automatically searches for the correct subclass
   to instantiate, based on the ``xsi:type`` of the passed XML element. Calling
   the method on a subclass directly may inadvertently cause the wrong class to
   be picked.

.. code-block:: python

   >>> myfunc = model.search("LogicalFunction")[0]
   >>> el = myfunc._element
   >>> el
   <Element ownedFunctions at 0x7f9e3742b840>
   >>> from capellambse.model import GenericElement
   >>> high_el = GenericElement.from_model(model, el)
   >>> high_el == myfunc
   True

When working with multiple objects, it can be desirable to directly construct a
high-level :py:class:`~capellambse.model.common.element.ElementList` with them.
The ElementList constructor works similar to ``GenericElement.from_model``, but
it takes a list of elements instead of only a single one.

.. code-block:: python

   >>> mycomp = model.search("LogicalComponent")[0]
   >>> children = mycomp._element.getchildren()
   >>> len(children)
   7
   >>> mylist = ElementList(model, children)
   >>> mylist
   [0] <Constraint 'Chamber of secrets closed' (7a5b8b30-f596-43d9-b810-45ab02f4a81c)>
   [1] <ComponentExchange 'Care' (c31491db-817d-44b3-a27c-67e9cc1e06a2)>
   [2] <InterfacePkg 'Interfaces' (c8f33066-2801-4970-8aea-6aadc189b9f3)>
   [3] <Part 'Whomping Willow' (1188fc31-789b-424f-a2d4-06791873a351)>
   [4] <Part 'School' (018a8ae9-8e8e-4aea-8191-4abf844a79e3)>
   [5] <LogicalComponent 'Whomping Willow' (3bdd4fa2-5646-44a1-9fa6-80c68433ddb7)>
   [6] <LogicalComponent 'School' (a58821df-c5b4-4958-9455-0d30755be6b1)>

Moving along the XML tree
=========================

In most simple cases, you can use the standard LXML methods in order to select
parent, child and sibling elements.

.. code-block:: python

   >>> myfunc = model.search("LogicalFunction")[3]
   >>> myfunc._element.getparent()
   <Element ownedLogicalFunctions at 0x7f9e3742ad00>
   >>> myfunc._element.getchildren()
   [<Element outputs at 0x7f9e3742b9d0>]
   >>> myfunc._element.getprevious()
   <Element ownedFunctions at 0x7f9e3742b6b0>
   >>> myfunc._element.getnext()
   <Element ownedFunctions at 0x7f9e3742bca0>

These elements and lists of elements can then be fed into
``GenericElement.from_model`` or the ``ElementList`` constructor respectively
in order to :ref:`return to the high-level API <api-level-shift>`.

Capella models support fragmentation into multiple files, which results in
multiple XML trees being loaded into memory. This makes it difficult to
traverse up and down the hierarchy, because in theory every element can be a
fragment boundary – in this case, it does not have a physical parent element,
and ``getparent()`` will return ``None``. A call to ``getchildren()`` or
similar on the (logical) parent element will yield a placeholder which only
contains a reference to the real element, but does not hold any other
information.

``MelodyLoader`` provides methods to traverse upwards or downwards in the
model's XML tree, while also taking into account fragment boundaries and the
aforementioned placeholder elements.

.. class:: MelodyLoader
   :noindex:

   .. automethod:: iterancestors
      :noindex:
   .. automethod:: iterchildren_xt
      :noindex:
   .. automethod:: iterdescendants
      :noindex:
   .. automethod:: iterdescendants_xt
      :noindex:

Resolving references
====================

You will often encounter attributes that contain references to other elements.

The ``MelodyLoader`` provides the following methods to work with references:

.. class:: MelodyLoader
   :noindex:

   .. automethod:: follow_link
      :noindex:
   .. automethod:: follow_links
      :noindex:
   .. automethod:: create_link
      :noindex:

Finding elements elsewhere
==========================

The low-level API implements the fundamentals for looking up model objects or
finding them by their type. The following methods are involved in these
operations:

.. class:: MelodyLoader
   :noindex:

   .. automethod:: iterall
      :noindex:
   .. automethod:: iterall_xt
      :noindex:
   .. automethod:: xpath
      :noindex:
   .. automethod:: xpath2
      :noindex:

Manipulating objects
====================

.. warning::

   The low-level API by itself does not do any consistency or validity checks
   when modifying a model. Therefore it is very easy to break a model using it,
   which can be very hard to recover from. Proceed with caution.

As ``GenericElement`` instances are simply wrappers around the raw XML
elements, any changes to their attributes are directly reflected by changes to
the attributes or children of the underlying XML element and vice versa. This
means that no special care needs to be taken to keep the high-level and
low-level parts of the API synchronized.

In many cases, the attribute names of the high-level API match those in the
XML, with the difference that the former uses ``snake_case`` naming (as is
conventional in the Python world), while the latter uses ``camelCase`` naming.
This example shows how the name of a function is accessed and modified using
the low-level API:

.. code-block:: python

   >>> myfunc = model.search("LogicalFunction")[3]
   >>> myfunc.name
   'defend the surrounding area against Intruders'
   >>> myfunc._element.attrib["name"]
   'defend the surrounding area against Intruders'
   >>> myfunc._element.attrib["name"] = "My Function"
   >>> myfunc.name
   'My Function'

Be aware that the XML usually does not explicitly store attributes that are set
to their default value (as defined by the meta model). In addition to that, the
high-level API often offers convenience shortcuts and reverse lookups that are
not directly reflected by XML attributes. Without at the detailed definitions,
it can therefore be difficult to infer the correct attributes for the low-level
API objects.

Creating and deleting objects
=============================

.. warning::

   Creating or deleting objects through the low-level API is highly
   discouraged, as it bears a very high risk of breaking the model. It's
   unlikely that we can support you with any breakage that you encounter as a
   result of using the low-level API.

   If you need access to model elements and relations that are not yet covered
   by our high-level API, please consider contributing and extending it instead
   – it's probably easier anyway. ;)

The ID cache
------------

In order to provide instantaneous access to any model element via its UUID, the
MelodyLoader maintains a hashmap containing all UUIDs. This hashmap needs to be
updated when inserting or removing elements in the tree. The following methods
take care of that:

.. class:: MelodyLoader
   :noindex:

   .. automethod:: idcache_index
      :noindex:
   .. automethod:: idcache_remove
      :noindex:
   .. automethod:: idcache_rebuild
      :noindex:

Creating objects
----------------

Creating a new object with the low-level API is a rather complex process. The
``MelodyLoader`` does provide some basic integrity checks, but most of the
meta-model-aware logic is implemented within the high-level API.

Before creating a new object, you need to generate and reserve a UUID for it.
This is done using the ``generate_uuid`` method. ``new_uuid`` provides a
context manager around it, which automatically cleans up the model in case
anything went wrong. It also checks that the UUID was properly registered with
the ID cache (see below). It is therefore highly recommended to use
``new_uuid`` over directly calling ``generate_uuid``. Note that even when using
``new_uuid``, you still need to manually call ``idcache_index`` on the newly
inserted element.

.. class:: MelodyLoader
   :noindex:

   .. automethod:: generate_uuid
      :noindex:
   .. automethod:: new_uuid
      :noindex:

Deleting objects
----------------

Inversely to creating new ones, when deleting an object from the XML tree it
also needs to be removed from the ID cache. This is done by calling
``idcache_remove`` (see above) on the element to be removed. Afterwards, delete
the element from its parent using the standard LXML API.

Saving modifications
====================

The ``MelodyLoader`` provides the same ``save()`` method as the high-level
``MelodyModel``.

.. class:: MelodyLoader
   :noindex:

   .. automethod:: save
      :noindex:
