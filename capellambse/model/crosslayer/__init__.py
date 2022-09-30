# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Utility classes that are used across all layers.

.. diagram:: [CDB] BaseLayer
"""
from .. import common as c
from . import cs, information


class BaseArchitectureLayer(c.GenericElement):
    """A template architecture layer."""

    _xmltag = "ownedArchitectures"

    data_package = c.DirectProxyAccessor(information.DataPkg)
    interface_package = c.DirectProxyAccessor(cs.InterfacePkg)

    all_classes = c.DeepProxyAccessor(information.Class, aslist=c.ElementList)
    all_collections = c.DeepProxyAccessor(
        information.Collection, aslist=c.ElementList
    )
    all_unions = c.DeepProxyAccessor(information.Union, aslist=c.ElementList)
    all_enumerations = c.DeepProxyAccessor(
        information.datatype.Enumeration, aslist=c.ElementList
    )
    all_complex_values = c.DeepProxyAccessor(
        information.datavalue.ComplexValue, aslist=c.ElementList
    )
    all_interfaces = c.DeepProxyAccessor(cs.Interface, aslist=c.ElementList)
