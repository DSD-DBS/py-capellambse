# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Functions for parsing and interacting with diagrams in a Capella model."""
from __future__ import annotations

__all__ = [
    "DiagramDescriptor",
    "ActiveFilters",
    "enumerate_diagrams",
    "parse_diagrams",
    "parse_diagram",
]

import collections.abc as cabc
import pathlib
import typing as t
import urllib.parse

from lxml import etree

import capellambse
from capellambse import aird, helpers, loader

from . import _common as C
from . import _filters, _semantic, _visual
from ._filters import ActiveFilters

DIAGRAM_ROOTS = {
    f"{{{capellambse.NAMESPACES['sequence']}}}SequenceDDiagram",
    f"{{{capellambse.NAMESPACES['diagram']}}}DSemanticDiagram",
}
"""Representations whose root element has one of these tags are diagrams.

Other representations (e.g. data tables) will not be listed by
`enumerate_diagrams`.
"""


class DiagramDescriptor(t.NamedTuple):
    fragment: pathlib.PurePosixPath
    name: str
    styleclass: str | None
    uid: str
    viewpoint: str
    target: etree._Element


def enumerate_diagrams(
    model: loader.MelodyLoader,
) -> cabc.Iterator[DiagramDescriptor]:
    """Enumerate the diagrams in the model.

    Parameters
    ----------
    model
        The MelodyLoader instance
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
                raise ValueError("Malformed diagram reference: {uid!r}")

            diag_root = model[uid]
            if diag_root.tag not in DIAGRAM_ROOTS:
                continue

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

            target_anchors = list(descriptor[1].iterchildren("target"))
            if len(target_anchors) != 1:
                raise RuntimeError(
                    f"Expected 1 <target> anchor, found {len(target_anchors)}"
                )
            target_href = target_anchors[0].get("href")
            if not target_href:
                raise RuntimeError("<target> anchor has no href")
            target = model.follow_link(descriptor[1], target_href)

            yield DiagramDescriptor(
                fragment=descriptor[0],
                name=name,
                styleclass=styleclass,
                uid=uid[1:],
                viewpoint=descriptor[2],
                target=target,
            )
        except Exception as err:
            C.LOGGER.warning(
                "Ignoring invalid diagram %s (%r): %s", uid, name, err
            )


def parse_diagrams(
    model: loader.MelodyLoader, **params: t.Any
) -> cabc.Iterator[aird.Diagram]:
    """Parse all diagrams from the model."""
    for descriptor in enumerate_diagrams(model):
        C.LOGGER.info(
            "Extracting diagram %r of type %s",
            descriptor.name,
            descriptor.styleclass,
        )
        yield parse_diagram(model, descriptor, **params)


def parse_diagram(
    model: loader.MelodyLoader, descriptor: DiagramDescriptor, **params: t.Any
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
    dgtree = model.follow_link(
        model.trees[descriptor.fragment].root, descriptor.uid
    )
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
        _filters.applyfilters(
            _filters.FilterArguments(diagram, dgtree, model, params)
        )
    return diagram


def _element_from_xml(ebd: C.ElementBuilder) -> aird.DiagramElement:
    """Construct a single diagram element from the model XML."""
    if ebd.data_element.get("element") is not None:
        factory = _semantic.from_xml
    else:
        factory = _visual.from_xml
    return factory(ebd)
