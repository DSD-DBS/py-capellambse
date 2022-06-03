# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Utility classes that are used across all layers.

.. diagram:: [CDB] BaseLayer
"""
from .. import common as c
from . import cs, information


class BaseArchitectureLayer(c.GenericElement):
    """A template architecture layer."""

    _xmltag = "ownedArchitectures"

    data_package = c.ProxyAccessor(information.DataPkg)
    interface_package = c.ProxyAccessor(cs.InterfacePkg)

    all_classes = c.ProxyAccessor(
        information.Class, deep=True, aslist=c.ElementList
    )
    all_collections = c.ProxyAccessor(
        information.Collection, deep=True, aslist=c.ElementList
    )
    all_unions = c.ProxyAccessor(
        information.Union, deep=True, aslist=c.ElementList
    )
    all_enumerations = c.ProxyAccessor(
        information.datatype.Enumeration, deep=True, aslist=c.ElementList
    )
    all_complex_values = c.ProxyAccessor(
        information.datavalue.ComplexValue,
        deep=True,
        aslist=c.ElementList,
        follow_abstract=False,
    )
    all_interfaces = c.ProxyAccessor(
        cs.Interface, deep=True, aslist=c.ElementList
    )
