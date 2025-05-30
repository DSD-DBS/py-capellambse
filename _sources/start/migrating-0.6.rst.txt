..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

Migrating from |project| v0.5.x to v0.6.x
=========================================

This page lists the most important differences between the v0.5.x and v0.6.x
series of releases. It is aimed at helping to transition client code using the
public high-level model API, and therefore may omit internal details that
client code should not be aware of.

- The metamodel definitions are now available in ``capellambse.metamodel.*``.
  The previous definitions at ``capellambse.model.layers.*`` and
  ``capellambse.model.crosslayer.*`` have been removed.

- The model implementation (previously ``capellambse.model.common``) has been
  reorganized under the ``capellambse.model`` package. All relevant classes are
  now directly exported on ``capellambse.model`` instead of any submodules.
  Submodules are now considered private.

- The PVMT extension has been revamped to be more feature-rich and easier to
  use. Please see the new `PVMT introduction notebook`__ for more details on
  how to use it.

  __ ../examples/08 Property Values.html

- Previously deprecated names have been removed from the metamodel.

- The auditing feature has been removed. Some design flaws led to it being
  unreliable and hard to work with, and it was causing relatively high
  maintenance overhead when making changes to the model implementation.

- The format of ``MelodyModel.info`` has changed. Detailed information about
  the used resources is now provided in the ``resources`` attribute, keyed by
  resource identifier. The ``url`` of the primary resource is still made
  available on the top-level info object for convenience, but other file
  handler specific attributes are now only available in its resource info
  (``model.info.resources["\x00"]``).

- The Git file handler no longer accepts the ``shallow`` keyword argument.
  Partial clones are always used instead, which offer better performance.

Changed Model attributes
------------------------

The metamodel
~~~~~~~~~~~~~

The metamodel is now located in the ``capellambse.metamodel`` package. This
affects the following modules:

.. note::

   Note especially that the ``ctx`` module has been renamed to ``sa`` for
   consistency with other modelling layers.

.. list-table::
   :header-rows: 1

   * - Old module path
     - New module path
   * - capellambse.model.crosslayer.*
     - capellambse.metamodel.*
   * - capellambse.model.layers.*
     - capellambse.metamodel.*
   * - capellambse.model.layers.ctx
     - capellambse.metamodel.sa

Requirements extension (``capellambse.extensions.reqif``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following deprecated aliases have been removed:

.. list-table::
   :header-rows: 1

   * - Removed alias
     - Correct name
   * - EnumDataTypeDefinition
     - EnumerationDataTypeDefinition
   * - RequirementsFolder
     - Folder
   * - RequirementsIncRelation
     - CapellaIncomingRelation
   * - RequirementsIntRelation
     - InternalRelation
   * - RequirementsModule
     - CapellaModule
   * - RequirementsOutRelation
     - CapellaOutgoingRelation
   * - RequirementsTypesFolder
     - CapellaTypesFolder
   * - String constants starting with ``XT_``
     - Use :func:`~capellambse.model.build_xtype` instead
   * - The ``reqif.elements`` submodule
     - Removed, use the ``reqif`` package directly

Model implementation
~~~~~~~~~~~~~~~~~~~~

The implementation of the high-level model is now available on
``capellambse.model.*``. The previous submodule structure below
``capellambse.model.common.*`` has been dissolved.

The ``capellambse.model.diagram`` module is not affected by this change.

In addition, some classes have been renamed:

.. list-table::
   :header-rows: 1

   * - Old name
     - New name
   * - AttributeProperty
     - StringPOD
   * - HTMLAttributeProperty
     - HTMLStringPOD
   * - NumericAttributeProperty
     - IntPOD or FloatPOD
   * - BooleanAttributeProperty
     - BoolPOD
   * - DatetimeAttributeProperty
     - DatetimePOD
   * - EnumAttributeProperty
     - EnumPOD
