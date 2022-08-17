# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Core functionality shared by all PVMT submodules."""

from capellambse.loader.xmltools import AttributeProperty
from capellambse.loader.xmltools import XMLDictProxy as XMLDictProxy_

NAMESPACES = dict(xsi="http://www.w3.org/2001/XMLSchema-instance")


class Generic:
    """Base class for PropertyValues, Domains etc."""

    idx = AttributeProperty("xml_element", "id", writable=False)
    # TODO Investigate potential problems with renaming things
    name = AttributeProperty("xml_element", "name")
    sid = AttributeProperty("xml_element", "sid", optional=True)

    def __init__(self, xml_element, *args, **kwargs):
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]
        self.xml_element = xml_element

    def __repr__(self):
        return '<pvmt.{} "{}"({})>'.format(
            type(self).__name__, self.name, self.idx
        )

    @classmethod
    def from_xml_element(cls, element):
        """Construct an object from the given XML element.

        This function is used to allow subclasses more control over how
        they are instantiated from existing XML elements, compared to
        creating them from scratch.
        """
        return cls(element)


class XMLDictProxy(Generic, XMLDictProxy_):  # pylint: disable=abstract-method
    """Facilitates usage of the :class:`capellambse.loader.XMLDictProxy`."""

    def __init__(self, xml_element, *args, **kwargs):
        # pylint: disable=arguments-out-of-order
        super().__init__(xml_element, xml_element, *args, **kwargs)
