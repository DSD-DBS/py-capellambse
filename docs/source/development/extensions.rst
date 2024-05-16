..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

.. _model-extensions:

***************************
  Extending the metamodel
***************************

.. warning::

   This page relates to the experimental ``capellambse.modelv2`` and
   ``capellambse.metamodel`` modules, and the process described here may change
   at any time.

|project| uses an extensible approach to defining the metamodel, which allows
us to support multiple different versions of Capella projects with a single
library installation.

Declaring a namespace
=====================

A package containing different object type definitions (i.e. classes) is called
a namespace. Each such namespace is logically represented by an instance of the
:py:class:`~capellambse.modelv2.Namespace` class. These Namespace instances are
also the interface that capellambse uses to find the correct class definitions
during model loading time.

To declare a new namespace, you first have to create an instance of the class:

.. code:: python

   # example_extension/objects.py
   from capellambse.modelv2 import *
   NS = Namespace(
       "http://example.com/extension/namespace",
       "com.example.extension",
       "com.example.extension.viewpoint",
       "1.0.0",
   )

The above declaration would result in the following XML namespace declaration:

.. code:: xml

   <O xmlns:com.example.extension="http://example.com/extension/namespace" />

In order for the capellambse runtime to find the new namespace, it needs to be
registered using Python's Entrypoints facility (not to be confused with the
model entrypoint). With a PEP-621 compatible build environment, this is done in
the following way:

.. code:: toml

   # pyproject.toml
   [project.entry-points."capellambse.namespaces"]
   example_extension = "example_extension.objects:NS"

The Entrypoint name (here "example_extension") is not currently used.

Collisions in the namespace alias names or the names of the Entrypoints are
ignored, however it is not permitted for multiple namespaces to register the
same URI. If a URI collision is detected, capellambse will raise an exception
when trying to load a model.

Defining object types
=====================

Object types are defined as regular Python classes that inherit from
:class:`capellambse.modelv2.ModelElement`. If there is a Namespace object
declared in the module using the ``NS`` name, the class will be automatically
registered with it:

.. code:: python

   # example_extension/objects.py
   from capellambse.modelv2 import *
   NS = Namespace(...)

   class CustomObject(ModelObject):
       custom_attribute = ...  # see below

If the class' namespace is defined differently, it has to be explicitly
specified using the ``ns=`` keyword argument:

.. code:: python

   OTHER_NS = Namespace(...)
   class OtherObject(ModelObject, ns=OTHER_NS): ...

These rules also apply when inheriting from any subclass of ``ModelObject``.

.. code:: python

   # example_extension/other_module.py
   from capellambse import *
   from .objects import CustomObject
   NS = Namespace(...)

   class Third(CustomObject): ... # implicitly use the `NS` above
   class Fourth(CustomObject, ns=NS): ... # explicitly pass `ns`

Don't forget that this namespace also has to be registered as a Python
Entrypoint, just like the first one:

.. code:: toml

   # pyproject.toml
   [project.entry-points."capellambse.namespaces"]
   example_extension = "example_extension.other_module:NS"

Defining attributes
===================

Object types by themselves only have very few default attributes defined,
unless they inherit from another subclass of ModelElement. This is where the
various POD and relationship descriptors come in. These descriptor classes
represent the different "plain-old-data" types and types of relationships with
other model objects.

Plain old data (POD)
--------------------

POD descriptors are used by simply instantiating them as part of a class
definition, and passing a few simple options to specify their behavior:

.. code:: python

   class CustomObject(ModelObject, ns=NS):
       foo = StringPOD(name="foo", required=True, writable=False)
       bar = FloatPOD(name="bar")
       last_seen = DateTimePOD(name="lastSeen")

Let's unpack what is happening here. The above snippet defines a class which
has — in addition to the standard attributes, like *uuid* — three new
attributes visible to Python code: *foo*, *bar* and *last_seen*. They are,
respectively, of type ``str``, ``float`` and ``datetime.datetime``.

The *foo* and *bar* attributes use the same name for the XML attribute as for
the Python side. However, because the two sides use different naming
conventions for attributes, the *lastSeen* XML attribute has been renamed to be
visible as *last_seen* to Python code.

Additionally, the *foo* attribute is marked as "not writable" or read-only.
This means that it cannot be changed again after having been set. It can only
be set once during the class' lifetime: either by loading the class from XML
with the value already set, or when constructing a new instance of the class
(with e.g. ``obj = CustomObject(bar=0.75)``), or — if it's not also marked as
"required" — at most once after the class has been instantiated with simple
attribute access (``obj.bar = 0.8``).

Finally, the *foo* attribute is also marked as "required", which has a few
implications as to how the class will behave:

- When loading the element from XML, the *foo* attribute must be present. If it
  is not, a :py:class:`~capellambse.modelv2.BrokenModelError` will be raised.

- When constructing a new instance of ``CustomObject``, the *foo* attribute
  must be passed to the constructor. Omitting it will result in a TypeError:

  .. code:: python

     my_obj = CustomObject(foo="quux") # ok
     my_obj = CustomObject() # TypeError: Missing required attribute(s) foo

- The attribute cannot be set to the default value as defined by the POD type,
  as that value wouldn't be written out to the XML. The following table shows
  these default values for the various POD types:

  ===========  =====================
  POD          Value
  ===========  =====================
  StringPOD    ``""``
  IntPOD       ``0``
  FloatPOD     ``0.0``
  BoolPOD      ``false``
  DateTimePOD  ``None``
  EnumPOD      the first enum member
  ===========  =====================

  Note that for ``EnumPOD``, the default can be changed by passing the
  ``default=`` keyword argument to the POD constructor.

Note that, when combining ``required=True`` and ``writable=False`` like this,
all restrictions from both options apply. Because *foo* has to be provided at
class instantiation time, and because it cannot be changed anymore after
instantiating the class, it's not possible to change it via simple attribute
access as described above:

.. code:: python

   my_custom_object = CustomObject(foo="quux")
   my_custom_object.foo = "baz"  # TypeError: Attribute CustomObject.foo is read-only

Model object relationships
--------------------------

The second type of descriptor handles relationships to other model objects.
These relationships can be organized into three categories:

- :py:class:`~capellambse.modelv2.Containment` builds a simple parent-child
  relation between two objects. An object can only have one parent, but it can
  have an arbitrary number of children. This relation type maps out the tree
  structure also visible in the Capella project explorer.

  In the Capella metamodel, this relation is usually referred to as
  "ownership", which is where the used XML tags get their names from (for
  example, ``ownedLogicalComponents``).

- :py:class:`~capellambse.modelv2.Association` is a weaker type of relation to
  an arbitrary other model element, without creating a parent-child relation
  between them.

  In the XML, this relation is stored as a space-separated list of UUID
  references.

- :py:class:`~capellambse.modelv2.Allocation` is a special relationship type,
  which uses an "allocation object" to express a relation similar to the
  Association relation above. These allocation objects are helper objects which
  do not have any attributes or other uses than to link two objects together.
  As such, they are also hidden by default in the Capella project explorer, and
  the Capella GUI usually treats them transparently.

  The class names of such allocation objects usually end with "Allocation".
  Objects that can also have additional attributes or that can be parents to
  further objects are not considered to be "allocation objects", and should be
  described with a Containment relationship.

All of these relationships need information about which classes are valid
targets, in order to ensure that the model stays valid and within the bounds
described by the metamodel. A valid target class is passed in as a 2-tuple of
the namespace URI and the class name. Instead of the string URI, it is also
possible to use a :py:class:`~capellambse.modelv2.Namespace` instance, which is
especially useful for relationships within the same namespace.

See the below code snippet for an example of how to use each of these
descriptors.

.. code:: python

   # example_extension/objects.py
   from __future__ import annotations

   from capellambse.modelv2 import *

   # The "DifferentObject" import is only needed at type-checking time, so we
   # can guard it behind ``TYPE_CHECKING`` to avoid circular import issues.
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from other_package import DifferentObject

   NS = Namespace(...)  # see above

   class CustomObject(ModelObject):
       # optional static type annotation ↓
       contained = Containment[CustomObject](
           "ownedCustomObjects",
           # ↓ Using a Namespace object
           (NS, "CustomObject"),
       )

       # Don't forget to enclose type annotations in quotes if they're using
       # classes that are only imported in an `if TYPE_CHECKING` block!
       # This assignment notation also needs the quotes with
       #   ``from __future__ import annotations``,
       # because from the interpreter's perspective, it's not an annotation.
       associated = Association["DifferentObject"](
           "associated",
           # ↓ Passing a namespace URI as str
           ("http://other.ext/namespace", "DifferentObject"),
       )

       # A split annotation doesn't need quotes with the future import:
       allocated: Allocation[CustomObject | DifferentObject] = Allocation(
           (NS, "CustomAllocation"),
           ("ownedCustomAllocations", "id", "target"),
           # All relationship descriptors accept multiple target classes.
           # Simply pass multiple namespace + class name tuples:
           (NS, "CustomObject"),
           ("http://other.ext/namespace", "DifferentObject"),
       )

For detailed documentation about what exactly each argument to the relationship
descriptors' constructors means, please refer to the individual descriptor
classes' documentation sections.

Versioned namespaces
====================

Most namespaces are versioned, and depending on the version used in the model,
they might have different features. For example, a newer version might have
added some new classes that older models don't yet know about, or it might have
deprecated and removed some others, or the available attributes on some of the
classes could have changed between namespace versions.

To facilitate this, a Namespace URI may contain the ``{VERSION}`` placeholder
string. When loading a model, versioned namespace templates are matched against
the actual namespaces in use to find the correct class to instantiate.

Subclasses support the ``minver`` and ``maxver`` arguments to specify which
namespace version range is supported. Both of these arguments accept either
``awesomeversion.AwesomeVersion`` objects or strings, which will be converted
automatically. ``minver`` is inclusive, while ``maxver`` is exclusive.

In addition, if the class name has a version suffix like ``_0_5_58`` (using
underscores and numbers), that suffix is removed before registering it in the
namespace. In case this automatic name transformation is undesirable, it is
also possible to explicitly specify the name to register with the ``clsname``
keyword argument, which will be used verbatim without modifications.

.. note::

   The ``__name__`` attribute of the class object will be the same as the name
   that was registered on the namespace.

The class selection algorithm works as follows:

1. Classes with a matching (registered) name are filtered by their associated
   ``minver`` and ``maxver``. If no ``minver`` was specified, it is implicitly
   considered to be "0". If no ``maxver`` was given for a class, it is treated
   as infinite.

   If no candidates remain after filtering (or if there were no classes with
   that name to begin with), an exception is raised.

2. These eligible classes are sorted by their ``minver``, so that the highest
   ``minver`` value comes first. Again, a missing ``minver`` is implicitly
   treated as "0".

3. The first entry from the resulting list of eligible candidates becomes the
   class that is used.

The following snippet demonstrate how to create multiple classes, each named
"VersionedObject":

.. code:: python

   # This class is used as fallback, as it has neither minver nor maxver.
   class VersionedObject(ModelObject): ...

   # This class will be used if the namespace version is at least 1.0.0.
   class VersionedObject_1_0(ModelObject, minver="1.0.0"): ...

   # This class is used for versions from 0.5 (inclusive) and 0.7 (exclusive).
   class VersionedObject_0_5(ModelObject, minver="0.5", maxver="0.7"): ...

   # This class is used from 0.2 onwards, except for 0.5 - 0.7 or from 1.0.0
   # onwards, where their respective classes above win out due to their higher
   # minver.
   class VersionedObject_0_2(ModelObject, minver="0.2"): ...

   # Example that explicitly passes the registered class name:
   # (This can be combined with minver, maxver and other keyword arguments)
   class VersionedObject_custom(ModelObject, clsname="VersionedObject"): ...

.. vim:set tw=79:
