..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

.. _declarative-modelling:

*********************
Declarative modelling
*********************

.. versionadded:: 0.5.0
   Introduced the declarative modelling module.

|project| supports declarative modelling with the :py:mod:`capellambse.decl`
module. This requires the optional dependency ``capellambse[decl]`` to be
installed.

The YAML-based declarative modelling engine combines a few simple concepts into
a powerful, but easy to use file format. These files can then be applied to any
model supported by |project|.

Example
=======

Here is an example YAML file that declares a simple coffee machine with a
couple of functions, and functional exchanges between them:

.. literalinclude:: ../../../tests/data/decl/coffee-machine.yml
   :language: yaml
   :lines: 4-
   :lineno-start: 1
   :linenos:

CLI usage
---------

If the additional optional dependency ``capellambse[decl,cli]`` is installed,
this file can be applied from the command line. Assuming it is saved as
``coffee-machine.yml``, it can then be applied to a locally stored Capella
model like this:

.. code-block:: sh

   python -m capellambse.decl --model path/to/model.aird coffee-machine.yml

Refer to the :py:func:`capellambse.cli_helpers.loadcli` documentation to find
out the supported argument format for ``--model``.

API usage
---------

Declarative YAML can also be applied programmatically, by calling the
:py:func:`capellambse.decl.apply` function. It takes a (loaded) |project|
model, and either a path to a file or a file-like object. To pass in a string
containing YAML, wrap it in :external:class:`io.StringIO`:

.. code-block:: python
   :emphasize-lines: 5

   import io, capellambse.decl
   my_model = capellambse.MelodyModel(...)
   my_yaml = "..."

   capellambse.decl.apply(my_model, io.StringIO(my_yaml))

   my_model.save()

Format description
==================

The expected YAML follows a simple format, where a parent object (i.e. an
object that already exists in the model) is selected, and one or more of three
different operations is applied to it:

- ``extend``-ing the object on list attributes,
- ``modify``-ing the object itself, or
- ``delete``-ing one or more children.

Parents can be selected by their universally unique ID (UUID), using the
``!uuid`` YAML tag. The following query selects the root logical function in
our test model:

.. code-block:: yaml

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d

Extending objects
-----------------

The following subsections show how to create completely new objects, or
reference and move already existing ones, using examples of declarative YAML
files on
:py:class:`~capellambse.model.common.accessors.ElementListCouplingMixin`-ish
attributes. The extension of one-to-one attributes works in the same way,
adhering to the YAML syntax.

Creating new objects
^^^^^^^^^^^^^^^^^^^^

:py:class:`~capellambse.model.layers.la.LogicalFunction` objects have several
different attributes which can be modified from a declarative YAML file. For
example, it is possible to create new
sub-:py:attr:`~capellambse.model.layers.la.LogicalFunction.functions`. This
snippet creates a function with the name "brew coffee" directly below the root
function:

.. code-block:: yaml
   :emphasize-lines: 2

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     extend:
       functions:
         - name: brew coffee

Functions can be nested arbitrarily deeply, and can also receive any other
supported attributes at the same time. The "brew coffee" function for example
could further receive nested child functions, each providing an output port:

.. code-block:: yaml
   :emphasize-lines: 4-5

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     extend:
       functions:
         - name: brew coffee
           functions:
             - name: grind beans
               outputs:
                 - name: Ground Beans port
             - name: heat water
               outputs:
                 - name: Hot Water port

While objects that already exist in the base model can be referenced with
``!uuid``, this is not possible for objects declared by the YAML file, as they
will have a random UUID assigned to ensure uniqueness. For this reason, a
promise mechanic exists, which allows to "tag" any declared object with a
``promise_id``, and later reference that object with the ``!promise`` YAML tag.
These promise IDs are user defined strings. The only requirement is that two
objects cannot receive the same ID, however they can be referenced any number
of times. This example snippet demonstrates how to declare two logical
functions, which communicate through a functional exchange:

.. code-block:: yaml
   :emphasize-lines: 7,11,14-15

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     extend:
       functions:
         - name: brew coffee
           inputs:
             - name: Steam port
               promise_id: steam-input
         - name: produce steam
           outputs:
             - name: Steam port
               promise_id: steam-output
       exchanges:
         - name: Steam
           source: !promise steam-output
           target: !promise steam-input

The ``!promise`` tag (and the ``!uuid`` tag as well) can be used anywhere where
a model object is expected.

Creating new references
^^^^^^^^^^^^^^^^^^^^^^^

It is important to understand when new model objects are created and when only
references are added. The following example would create a reference in the
``.allocated_functions`` attribute of the
:py:class:`~capellambse.model.layers.la.LogicalComponent` which is also the
logical ``root_component`` (parent) to the logical ``root_function``:

.. code-block:: yaml
   :emphasize-lines: 2

   - parent: !uuid 0d2edb8f-fa34-4e73-89ec-fb9a63001440
     extend:
       allocated_functions:
         - !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d

This is caused by the type of relationship (non-
:py:class:`~capellambse.model.common.accessors.DirectProxyAccessor`) between
the parent and its ``allocated_functions``.

It is also possible to create references to promised objects, but extra caution
for declaring ``promise_id``\ s for resolving these promises successfully:

.. code-block:: yaml
   :emphasize-lines: 5,9

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     extend:
       functions:
         - name: The promised one
           promise_id: promised-fnc
   - parent: !uuid 0d2edb8f-fa34-4e73-89ec-fb9a63001440
     extend:
       functions:
         - !promise promised-fnc

The ``promise_id`` declaration can also happen after referencing it.

Moving objects
^^^^^^^^^^^^^^

The following example would move a logical function from underneath a
:py:class:`~capellambse.model.layers.la.LogicalFunctionPkg` (accessible via
``functions``) into ``functions`` of the logical ``root_function`` (parent)
since the ``functions`` attribute has a parent/children relationship (i.e. the
:py:class:`~capellambse.model.common.accessors.DirectProxyAccessor` is used).

.. code-block:: yaml

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     extend:
       functions:
         - !uuid 8833d2dc-b862-4a50-b26c-6f7e0f17faef

Modifying objects
-----------------

After selecting a parent, it is also possible to directly change its properties
without introducing new objects into the model. This happens by specifying the
attributes in the ``modify:`` key.

The following example would change the ``name`` of the root
:py:class:`~capellambse.model.layers.la.LogicalComponent` to "Coffee Machine"
(notice how we use a different UUID than before):

.. code-block:: yaml
   :emphasize-lines: 2

   - parent: !uuid 0d2edb8f-fa34-4e73-89ec-fb9a63001440
     modify:
       name: Coffee Machine

This is not limited to string attributes; it is just as well possible to change
e.g. numeric properties. This example changes the ``min_card`` property of an
:py:class:`~capellambse.model.crosslayer.information.ExchangeItemElement` to
``0`` and the ``max_card`` to infinity, effectively removing both limitations:

.. code-block:: yaml
   :emphasize-lines: 3-

   - parent: !uuid 81b87fcc-03cf-434b-ad5b-ef18266c5a3e
     modify:
       min_card: 0
       max_card: .inf

Deleting objects
----------------

Finally, with declarative modelling files, it is possible to delete objects
from the model. Depending on where the delete operation occurs, either the
target object is deleted entirely, or only the link to it is destroyed.

Currently, objects to be deleted can only be selected by their UUID.

For example, this snippet deletes the logical function named "produce Great
Wizards" from the model:

.. code-block:: yaml
   :emphasize-lines: 3

   - parent: !uuid f28ec0f8-f3b3-43a0-8af7-79f194b29a2d
     delete:
       functions:
         - !uuid 0e71a0d3-0a18-4671-bba0-71b5f88f95dd

In contrast, this snippet only removes its allocation to the "Hogwarts" root
component, but the function still exists afterwards:

.. code-block:: yaml
   :emphasize-lines: 3

   - parent: !uuid 0d2edb8f-fa34-4e73-89ec-fb9a63001440
     delete:
       allocated_functions:
         - !uuid 0e71a0d3-0a18-4671-bba0-71b5f88f95dd
