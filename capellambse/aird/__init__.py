# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Functions for parsing and interacting with diagrams in a Capella model."""
from __future__ import annotations

__all__ = [
    "DiagramDescriptor",
    "ActiveFilters",
    "enumerate_diagrams",
    "parse_diagrams",
    "parse_diagram",
    "iter_visible",
]

import collections.abc as cabc
import logging
import pathlib
import typing as t
import urllib.parse

from lxml import etree

import capellambse._namespaces as _n
from capellambse import diagram, helpers, loader

from . import _common as C
from . import _filters, _semantic, _visual
from ._filters import ActiveFilters

DIAGRAM_ROOTS = {
    f"{{{_n.NAMESPACES['sequence']}}}SequenceDDiagram",
    f"{{{_n.NAMESPACES['diagram']}}}DSemanticDiagram",
}
"""Representations whose root element has one of these tags are diagrams.

Other representations (e.g. data tables) will not be listed by
`enumerate_diagrams`.
"""


class DiagramDescriptor(t.NamedTuple):
    fragment: pathlib.PurePosixPath
    name: str
    styleclass: str | None
    descriptor: etree._Element
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
    views: list[tuple[pathlib.PurePosixPath, etree._Element, str]] = []
    for i in model.xpath2(C.XP_VIEWS):
        viewname = helpers.xpath_fetch_unique(
            "./viewpoint", i[1], "viewpoint description"
        )
        assert viewname is not None
        viewname = C.RE_VIEWPOINT.search(viewname.attrib["href"])
        if viewname is not None:
            viewname = viewname.group(1)
        views.append((*i, urllib.parse.unquote(viewname or "")))

    if not views:
        C.LOGGER.debug("No viewpoints found in the model")
        return

    descriptors: list[tuple[pathlib.PurePosixPath, etree._Element, str]] = []
    for view in views:
        descriptors += [
            (view[0], d, view[2]) for d in C.XP_DESCRIPTORS(view[1])
        ]

    for descriptor in descriptors:
        name = uid = None
        try:
            name = descriptor[1].attrib["name"]
            uid = descriptor[1].attrib["repPath"]
            if not uid.startswith("#"):
                raise ValueError(f"Malformed diagram reference: {uid!r}")

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
                descriptor=descriptor[1],
            )
        except Exception as err:
            C.LOGGER.warning(
                "Ignoring invalid diagram %s (%r): %s", uid, name, err
            )


def parse_diagrams(
    model: loader.MelodyLoader, **params: t.Any
) -> cabc.Iterator[diagram.Diagram]:
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
) -> diagram.Diagram:
    """Parse a single diagram from the model.

    Parameters
    ----------
    model
        A loaded model.
    descriptor
        A DiagramDescriptor as obtained from :func:`enumerate_diagrams`.
    """
    diag = diagram.Diagram(
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
                    target_diagram=diag,
                    diagram_tree=dgtree,
                    data_element=data_elm,
                    melodyloader=model,
                    fragment=descriptor.fragment,
                )
            )
        except C.SkipObject:
            continue
        assert elm is not None
        diag.add_element(elm, False, force=True)

    if len(diag) == 0:
        C.LOGGER.error(
            "Deserialized diagram %r is empty", descriptor.name or diag.name
        )
    else:
        diag.calculate_viewport()
        _filters.applyfilters(
            _filters.FilterArguments(diag, dgtree, model, params)
        )
    return diag


def _element_from_xml(ebd: C.ElementBuilder) -> diagram.DiagramElement:
    """Construct a single diagram element from the model XML."""
    element = ebd.data_element.get("element")
    tag = ebd.melodyloader[element].tag if element else None
    if element is not None and tag != "ownedRepresentationDescriptors":
        factory = _semantic.from_xml
    else:
        factory = _visual.from_xml
    return factory(ebd)


def iter_visible(
    model: loader.MelodyLoader, descriptor: DiagramDescriptor
) -> cabc.Iterator[etree._Element]:
    r"""Iterate over all semantic elements that are visible in a diagram.

    This is a much faster alternative to calling :func:`parse_diagram`
    and iterating over the diagram elements, if you only need to know
    which semantic elements are visible, but are not otherwise
    interested in the layout of the diagram.

    Parameters
    ----------
    model
        A loaded model.
    descriptor
        A DiagramDescriptor as obtained from :func:`enumerate_diagrams`.

    Raises
    ------
    ValueError
        If the corresponding data or style element can't be found in the
        ``*.aird`` file.

    Yields
    ------
    etree._Element
        A semantic element from the ``*.capella`` file.
    """
    diag_element = model.follow_link(
        model.trees[descriptor.fragment].root, descriptor.uid
    )
    style_data = helpers.xpath_fetch_unique(
        C.XP_ANNOTATION_ENTRIES,
        diag_element,
        "ownedAnnotationsEntries with source GMF_DIAGRAMS",
        diag_element.attrib["uid"],
    )
    port_tag = "ownedBorderedNodes"
    visited: set[str] = set()
    for elt in diag_element.iterdescendants("ownedDiagramElements", port_tag):
        style_element = helpers.xpath_fetch_unique(
            f".//*[@element='{elt.attrib['uid']}']",
            style_data,
            "style description",
        )
        if style_element.get("visible", "true") != "true":
            continue

        # Component Ports have their visible attribute on a child element
        if elt.tag == port_tag:
            try:
                real_se = next(style_element.iterchildren("children"))
            except StopIteration:
                pass

            if real_se.get("visible", "true") != "true":
                continue

        try:
            target = next(elt.iterdescendants("target"))
        except StopIteration:
            C.LOGGER.warning(
                "No semantic element found for %r",
                elt.get("name", elt.attrib["uid"]),
            )
            continue

        try:
            elem = model.follow_link(target, target.attrib["href"])
        except KeyError:
            C.LOGGER.debug(
                "Semantic element has been deleted, ignoring: %s",
                target.attrib["href"],
            )
            continue

        fragment = model.find_fragment(elem)
        if (
            model.trees[fragment].fragment_type == loader.FragmentType.SEMANTIC
            and elem.attrib["id"] not in visited
        ):
            yield elem
            visited.add(elem.attrib["id"])


if not t.TYPE_CHECKING:

    def __getattr__(key: str) -> t.Any:
        if key == "diagram":
            obj = diagram
        else:
            try:
                obj = getattr(diagram, key)
            except NameError:
                try:
                    obj = importlib.import_module(f"capellambse.diagram.{key}")
                except ImportError:
                    raise NameError(f"No name {key} in {__name__}") from None
        import warnings

        warnings.warn(
            (
                f"{__name__}.{key} is deprecated,"
                " import it from capellambse.diagram instead"
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
