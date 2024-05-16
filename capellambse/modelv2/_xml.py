# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Utilities for reading and writing XML trees."""
from __future__ import annotations

import collections.abc as cabc
import logging
import pathlib
import typing as t
import urllib.parse

import ordered_set
from lxml import etree

from capellambse import filehandler, helpers

from . import _obj

if t.TYPE_CHECKING:
    from . import _model

LOGGER = logging.getLogger(__name__)

_NS_SIRIUS = "http://www.eclipse.org/sirius/1.1.0"
_NS_XMI = "http://www.omg.org/XMI"

_TAG_DANALYSIS = f"{{{_NS_SIRIUS}}}DAnalysis"
_TAG_XMI = f"{{{_NS_XMI}}}XMI"

_SEMANTIC_RESOURCES = frozenset({".afm", ".capella", ".capellafragment"})


class MissingResourceLocationError(KeyError):
    """Raised when a model needs an additional resource location."""


def load(model: _model.Model, entrypoint: pathlib.PurePosixPath) -> None:
    """Load the model from XML."""
    if entrypoint.suffix != ".aird":
        raise ValueError(f"Entrypoint must be an .aird file, not {entrypoint}")

    # TODO store the referenced_analysis somewhere
    _, semantic_resources = _load_aird(
        model.resources, _obj.ResourceName("\x00", entrypoint)
    )

    lazy_attributes = ordered_set.OrderedSet[tuple[str, str]]()
    loaded_resources: set[_obj.ResourceName] = set()

    for res in semantic_resources:
        if res.filename.suffix in (".afm"):
            _load_semantic(model, res, lazy_attributes)
            # pylint: disable-next=modified-iterating-list
            semantic_resources.remove(res)
            break

    while semantic_resources:
        res = semantic_resources.pop()
        if (
            res.filename.suffix in _SEMANTIC_RESOURCES
            and res not in loaded_resources
        ):
            _load_semantic(model, res, lazy_attributes)
        else:
            # TODO store the referenced_analysis somewhere
            _, new_resources = _load_aird(model.resources, res)
            semantic_resources.extend(new_resources)
        loaded_resources.add(res)

    deferred: list[tuple[_obj.ModelElement, _obj.RelationshipDescriptor]] = []
    objs = list(model.trees)
    while objs:
        obj = objs.pop()
        for attr in dir(type(obj)):
            desc = getattr(type(obj), attr, None)
            if isinstance(desc, _obj.Containment):
                desc.resolve(obj)
            elif isinstance(desc, _obj.RelationshipDescriptor):
                deferred.append((obj, desc))
    for obj, desc in deferred:
        desc.resolve(obj)


def _load_aird(
    resources: cabc.Mapping[str, filehandler.FileHandler],
    resname: _obj.ResourceName,
) -> tuple[list[etree._Element], list[_obj.ResourceName]]:
    referenced_analysis: list[etree._Element] = []
    semantic_resources: list[_obj.ResourceName] = []
    reslabel, filename = resname
    with resources[reslabel].open(filename) as f:
        parser = etree.iterparse(f, events=("start", "end"))
        try:
            analysis = _find_analysis(parser)
        except ValueError as err:
            raise ValueError(
                f"Error parsing {reslabel}/{filename}: {err}"
            ) from None

    for i in analysis.iter("semanticResources"):
        if i.text:
            name = urllib.parse.unquote(i.text)
            path = helpers.normalize_pure_path(name, base=filename.parent)
            newres = _obj.ResourceName(resname.resource_label, path)
            semantic_resources.append(newres)

    return referenced_analysis, semantic_resources


def _load_semantic(
    model: _model.Model,
    resname: _obj.ResourceName,
    lazy_attributes: cabc.MutableSet[tuple[str, str]],
) -> None:
    LOGGER.debug("Loading resource %s", resname)
    try:
        resource = model.resources[resname.resource_label]
    except KeyError:
        raise MissingResourceLocationError(resname.resource_label) from None
    with resource.open(resname.filename) as f:
        tree = etree.parse(f)
        root = tree.getroot()

    xmi_version = root.attrib.pop(f"{{{_NS_XMI}}}version", "2.0")
    if xmi_version != "2.0":
        raise ValueError(f"Unsupported XMI version: {xmi_version}")

    if root.tag == _TAG_XMI:
        elems: cabc.Iterable[etree._Element] = root.iterchildren()
    else:
        elems = [root]

    for i in elems:
        obj = _obj.load_object(model, i, lazy_attributes)
        obj._fragment = resname
        model.trees.append(obj)


def _find_analysis(parser: etree.iterparse) -> etree._Element:
    _, root = next(parser, (None, None))
    if root is None:
        raise ValueError("File is empty")
    if root.tag == _TAG_DANALYSIS:
        return root

    for action, elem in parser:
        if action != "end":
            continue

        if elem.tag == _TAG_DANALYSIS:
            return elem

        if elem.getparent() is root:
            root.remove(elem)

    raise ValueError("No DAnalysis found")


def _get_ns_label(elem: etree._Element, ns: str) -> str:
    for k, v in elem.nsmap.items():
        if k and v == ns:
            return k
    raise ValueError(f"Namespace {ns!r} not found in {elem.nsmap}")


def wrap_xmi(
    *roots: etree._Element, capella_version: str
) -> etree._ElementTree:
    """Wrap the given elements in XMI.

    This function wraps the given root elements in a single ``xmi:XMI``
    parent for serialization within the same fragment. This element is
    then made the root of a new document tree, and an XML comment
    containing the compatible Capella version added before the actual
    root.

    If only one root element is given, that element is used directly and
    not wrapped in a further ``xmi:XMI`` element.

    Parameters
    ----------
    roots
        The root element(s) to wrap.
    capella_version
        The Capella version to annotate, for example "6.0.0".

    Returns
    -------
    etree._Document
        An LXML document containing the wrapped root elements.

    Raises
    ------
    ValueError
        If no root elements were given.
    """
    if not roots:
        raise ValueError("No root elements to wrap in XMI")

    if len(roots) == 1:
        root = roots[0]
    else:
        root = etree.Element(
            _TAG_XMI, {f"{{{_NS_XMI}}}version": "2.0"}, nsmap={"xmi": _NS_XMI}
        )
    root.addprevious(etree.Comment(f"Capella_Version_{capella_version}"))

    return etree.ElementTree(root)
