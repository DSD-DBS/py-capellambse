..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

.. _audit-events:

************
Audit events
************

|project| fires :external:py:func:`sys.audit` events for certain calls in the
high-level API. These events can be inspected by a callable registered with
:external:py:func:`sys.addaudithook`.

.. warning::

   System audit hooks cannot be removed once they were registered. When storing
   a reference to a model in an audit hook, make sure that the reference is
   destroyed properly to avoid unnecessary memory consumption.

Also refer to the :py:class:`capellambse.auditing.AttributeAuditor` for an
example class that records read access to all attributes in a model using the
``capellambse.getattr`` audit event.

For programmatic use, a set of all events that signify changes to the model is
available as the ``events`` class variable on the
:py:class:`~capellambse.auditing.WriteProtector`.

List of audit events fired by |project|
=======================================

The following table shows all audit events that are fired by ``capellambse``.

.. note::

   For some calls, multiple events may be fired. For example, a
   ``capellambse.create`` event is always followed by another event (such as
   ``capellambse.insert``) when adding the newly created object to the model
   tree.

+--------------------------------+--------------------------------------------+
| Event                          | Description                                |
+================================+============================================+
| ``capellambse.getattr``        | An attribute is accessed for reading.      |
|                                |                                            |
| .. versionadded:: 0.5.11       | **Arguments:**                             |
|                                |                                            |
|                                | 1. ``obj``: The object that was accessed.  |
|                                | 2. ``attr``: The attribute on that object. |
|                                | 3. ``value``: The value that is going to   |
|                                |    be returned. Use this to avoid          |
|                                |    recursive loops when inspecting the     |
|                                |    object.                                 |
|                                |                                            |
|                                | .. note::                                  |
|                                |                                            |
|                                |    This event will also be fired for       |
|                                |    internal read accesses, for example     |
|                                |    when searching the model for references |
|                                |    to another object. Currently there is   |
|                                |    no reliable way to distinguish between  |
|                                |    explicit (user) access and these        |
|                                |    internal calls.                         |
+--------------------------------+--------------------------------------------+
| ``capellambse.read_attribute`` | Deprecated alias of                        |
|                                | ``capellambse.getattr``.                   |
| .. versionadded:: pre-0.5      |                                            |
|                                |                                            |
| .. deprecated:: 0.5.11         |                                            |
|    Use the ``getattr`` event   |                                            |
|    instead.                    |                                            |
+--------------------------------+--------------------------------------------+
| ``capellambse.setattr``        | An attribute is about to be changed.       |
|                                |                                            |
| .. versionadded:: 0.5.11       | **Arguments:**                             |
|                                |                                            |
|                                | 1. ``obj``: The object being changed.      |
|                                | 2. ``attr``: The name of the attribute.    |
|                                | 3. ``value``: The new value.               |
+--------------------------------+--------------------------------------------+
| ``capellambse.delete``         | An object or a list of objects is about to |
|                                | be deleted from the model.                 |
| .. versionadded:: 0.5.11       |                                            |
|                                | This is also fired when purging left-over  |
|                                | references while deleting another object.  |
|                                |                                            |
|                                | **Arguments:**                             |
|                                |                                            |
|                                | 1. ``parent``: The current parent object.  |
|                                | 2. ``attr``: The attribute that contains   |
|                                |    the object to be deleted.               |
|                                | 3. ``index``: If a single object from a    |
|                                |    list is being deleted, contains the     |
|                                |    index of that object into the list. If  |
|                                |    the entire attribute is deleted (in the |
|                                |    case of lists: the list is emptied),    |
|                                |    contains ``None``.                      |
+--------------------------------+--------------------------------------------+
| ``capellambse.insert``         | An item is about to be inserted into a     |
|                                | coupled ``ElementList``.                   |
| .. versionadded:: 0.5.11       |                                            |
|                                | **Arguments:**                             |
|                                |                                            |
|                                | 1. ``parent``: The object being changed.   |
|                                | 2. ``attr``: The attribute that contains   |
|                                |    this list.                              |
|                                | 3. ``index``: The index into the list to   |
|                                |    insert into. May be ``len(the_list)``   |
|                                |    (or greater) to signify appending to    |
|                                |    the end.                                |
|                                | 4. ``value``: The value being inserted.    |
+--------------------------------+--------------------------------------------+
| ``capellambse.create``         | A new object was just created, but is not  |
|                                | yet part of the model.                     |
| .. versionadded:: 0.5.11       |                                            |
|                                | **Arguments:**                             |
|                                |                                            |
|                                | 1. ``parent``: The new parent object.      |
|                                | 2. ``attr``: The attribute that contains   |
|                                |    this list.                              |
|                                | 3. ``index``: The index into the list to   |
|                                |    insert into. May be ``len(the_list)``   |
|                                |    (or greater) to signify appending to    |
|                                |    the end.                                |
|                                | 4. ``value``: The newly created object.    |
+--------------------------------+--------------------------------------------+

Implementation notes
====================

Audit events are generally fired from these locations:

1. Read access events (i.e. ``capellambse.getattr``) are fired by each Accessor
   subclass, just before returning the final value from ``__get__()``.

2. Events that signify modifications to a list are fired by the overridden
   methods in ``CoupledElementListMixin`` (include ``create``), as well as by
   ``__setattr__()`` of ``GenericElement``, before passing the values on to the
   actual accessor implementation.

3. The ``capellambse.delete`` event for deleting an entire attribute (i.e. the
   case where the ``index`` argument is ``None``) is fired by the relevant
   Accessor's ``__delete__()`` method.

   Note that for lists, Accessors may instead fire individual ``delete`` events
   for each list item.

In order to prevent audit events from being fired for elements that are still
under construction, ``GenericElement`` keeps track of the construction state in
the ``_constructed`` attribute. It becomes True when construction is finished
and audit events may be fired. Accessors must not fire any audit events if the
object they're acting on has not been fully constructed.
