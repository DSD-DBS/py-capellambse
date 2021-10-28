# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Functions for parsing and interacting with diagrams in a Capella model."""
from __future__ import annotations

__all__ = [
    "DiagramDescriptor",
    "enumerate_diagrams",
    "parse_diagrams",
    "parse_diagram",
]

import collections.abc as cabc
import pathlib
import typing as t
import urllib.parse

from lxml import etree

from capellambse import aird, helpers, loader

from . import _common as C
from . import _filters, _semantic, _visual


class DiagramDescriptor(t.NamedTuple):
    fragment: pathlib.Path
    name: str
    styleclass: str | None
    uid: str
    viewpoint: str
    target: etree._Element


def enumerate_diagrams(
    model: loader.MelodyLoader,
    *,
    err_abort: bool = False,
) -> cabc.Iterator[DiagramDescriptor]:
    """Enumerate the diagrams in the model.

    Parameters
    ----------
    model
        The MelodyLoader instance
    err_abort
        Abort when encountering any error.  If False, enumerate all
        diagrams that are usable and ignore the others.
    """
    raw_views = model.xpath2(C.XP_VIEWS)
    views: list[tuple[pathlib.PurePosixPath, etree._Element, str]] = []
    if len(raw_views) == 0:
        raise ValueError("Invalid XML: No viewpoints found")

    # Extract the views' names
    for i in raw_views:
        viewname = helpers.xpath_fetch_unique(
            "./viewpoint", i[1], "viewpoint description"
        )
        assert viewname is not None
        viewname = C.RE_VIEWPOINT.search(viewname.attrib["href"])
        if viewname is not None:
            viewname = viewname.group(1)
        views.append((*i, urllib.parse.unquote(viewname or "")))

    if not views:
        raise ValueError("No viewpoints found")

    descriptors: list[tuple[pathlib.PurePosixPath, etree._Element, str]] = []
    for view in views:
        descriptors += [
            (view[0], d, view[2]) for d in C.XP_DESCRIPTORS(view[1])
        ]

    if len(descriptors) == 0:
        raise ValueError("Invalid XML: No diagrams found")

    for descriptor in descriptors:
        name = uid = None
        try:
            name = descriptor[1].attrib["name"]
            uid = descriptor[1].attrib["repPath"]
            if not uid.startswith("#"):
                raise ValueError("Invalid diagram reference: {uid!r}")

            # Extract styleclass from diagram description
            styledescription = helpers.xpath_fetch_unique(
                "./description[@href]", descriptor[1], "style description"
            )
            assert styledescription is not None
            styledescription = styledescription.attrib["href"]
            # This style description is something resembling XPath, e.g.
            #     platform:/[...]#//[...]/@ownedRepresentations[name='$$$']
            # The thing we're interested in is denoted as $$$ above.
            styleclass_match = C.RE_STYLECLASS.search(styledescription)
            if styleclass_match is None:
                styleclass: str | None = None
            else:
                styleclass = urllib.parse.unquote(styleclass_match.group(1))

            target = helpers.fragment_link(
                descriptor[0],
                t.cast(
                    str,
                    helpers.xpath_fetch_unique(
                        "./target/@href", descriptor[1], "target href"
                    ),
                ),
            )

            yield DiagramDescriptor(
                fragment=pathlib.Path(descriptor[0]),
                name=name,
                styleclass=styleclass,
                uid=uid[1:],
                viewpoint=descriptor[2],
                target=target,
            )
        except Exception:
            C.LOGGER.exception(
                "Error parsing descriptor for diagram with uid %r and name %r",
                uid,
                name,
            )
            if err_abort:
                raise


def parse_diagrams(model: loader.MelodyLoader) -> cabc.Iterator[aird.Diagram]:
    """Parse all diagrams from the model."""
    for descriptor in enumerate_diagrams(model):
        C.LOGGER.info(
            "Extracting diagram %r of type %s",
            descriptor.name,
            descriptor.styleclass,
        )
        yield parse_diagram(model, descriptor)


def parse_diagram(
    model: loader.MelodyLoader, descriptor: DiagramDescriptor
) -> aird.Diagram:
    """Parse a single diagram from the model.

    Parameters
    ----------
    descriptor
        A DiagramDescriptor as obtained from :func:`enumerate_diagrams`.
    """
    diagram = aird.Diagram(
        descriptor.name, styleclass=descriptor.styleclass, uuid=descriptor.uid
    )
    dgtree = model[f"{descriptor.fragment}#{descriptor.uid}"]
    treedata = helpers.xpath_fetch_unique(
        C.XP_ANNOTATION_ENTRIES,
        dgtree,
        "ownedAnnotationsEntries with source GMF_DIAGRAMS",
        dgtree.attrib["uid"],
    )
    assert treedata is not None

    if treedata.attrib.get("measurementUnit", "Pixel") != "Pixel":
        C.LOGGER.warning(
            "Unknown measurement unit %r",
            treedata.attrib.get("measurementUnit"),
        )

    for data_elm in treedata.iterdescendants("children", "edges"):
        try:
            elm = _element_from_xml(
                C.ElementBuilder(
                    target_diagram=diagram,
                    diagram_tree=dgtree,
                    data_element=data_elm,
                    melodyloader=model,
                    fragment=descriptor.fragment,
                )
            )
        except C.SkipObject:
            continue
        assert elm is not None
        diagram.add_element(elm, False, force=True)

    if len(diagram) == 0:
        C.LOGGER.error(
            "Deserialized diagram %r is empty", descriptor.name or diagram.name
        )
    else:
        diagram.calculate_viewport()
        _filters.applyfilters(diagram, dgtree, model)
    return diagram


def _element_from_xml(ebd: C.ElementBuilder) -> aird.DiagramElement:
    """Construct a single diagram element from the model XML."""
    if ebd.data_element.get("element") is not None:
        factory = _semantic.from_xml
    else:
        factory = _visual.from_xml
    return factory(ebd)
