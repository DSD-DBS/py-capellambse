# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Exceptions that may be raised by the PVMT module."""


class PropertyValueError(Exception):
    """Base class for all property-value related errors."""


class ScopeError(PropertyValueError):
    """Attempted to apply a PV group to an element outside its scope."""


class UndefinedKeyError(PropertyValueError, KeyError):
    """A key is attempted to be added which is not defined for the group."""


class CastingError(PropertyValueError):
    """A supplied value cannot be cast from or to the XML representation."""


class GroupNotAppliedError(PropertyValueError, KeyError):
    """The property value group has not been applied to this element."""
