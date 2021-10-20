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
"""Functions implementing various filters that Capella supports."""
from __future__ import annotations

import collections.abc as cabc
import importlib
import pkgutil
import typing as t
import urllib.parse

from lxml import etree

import capellambse.loader
from capellambse import aird

from .. import _common as c

Phase2CompositeFilter = t.Callable[
    [c.ElementBuilder, aird.DiagramElement], None
]
CompositeFilter = t.Callable[
    [c.ElementBuilder, aird.DiagramElement], t.Optional[Phase2CompositeFilter]
]
#: Maps composite filter names to phase-1 callables
COMPOSITE_FILTERS: dict[str, CompositeFilter] = {}

GlobalFilter = t.Callable[
    [
        aird.Diagram,
        etree._Element,
        etree._Element,
        capellambse.loader.MelodyLoader,
    ],
    None,
]
#: Maps names of global filters to functions that implement them
GLOBAL_FILTERS: dict[str, GlobalFilter] = {}

_TDiagramElement = t.TypeVar("_TDiagramElement", bound=aird.DiagramElement)


def composite_filter(
    name: str,
) -> cabc.Callable[[CompositeFilter], CompositeFilter]:
    """Register a composite filter.

    Composite filters are executed in two phases.  The first phase
    occurs during each diagram element's creation.  Here the callables
    registered with this decorator are directly executed with the
    diagram under construction and the to-be-filtered element as
    arguments.

    The second phase happens after the entire diagram has been created.
    Filters that want to run in this phase should return another
    callable object during the first phase; this object will then be
    called with the same (now constructed) diagram and the element.

    Composite filters should always operate in place.  They may append
    additional elements to the diagram, but they should never remove
    any; instead they should simply change their "hidden" flag to True.
    """

    def add_comp_filter(func: CompositeFilter) -> CompositeFilter:
        COMPOSITE_FILTERS[name] = func
        return func

    return add_comp_filter


def phase2_composite_filter(
    name: str,
) -> cabc.Callable[[Phase2CompositeFilter], Phase2CompositeFilter]:
    """Register a composite filter that only needs to run in phase 2."""

    def add_comp_filter(func: Phase2CompositeFilter) -> Phase2CompositeFilter:
        def phase1dummy(
            _1: c.ElementBuilder,
            _2: aird.DiagramElement,
        ) -> Phase2CompositeFilter:
            return func

        COMPOSITE_FILTERS[name] = phase1dummy
        return func

    return add_comp_filter


def global_filter(name: str) -> cabc.Callable[[GlobalFilter], GlobalFilter]:
    """Register a global filter."""

    def add_global_filter(func: GlobalFilter) -> GlobalFilter:
        GLOBAL_FILTERS[name] = func
        return func

    return add_global_filter


def setfilters(
    seb: c.SemanticElementBuilder,
    dgobject: _TDiagramElement,
) -> _TDiagramElement:
    """Set the filters on the element.

    This is phase 1 of composite filter execution.

    Parameters
    ----------
    seb
        The element builder instance
    dgobject
        The constructed diagram element on which to set filters.

    Returns
    -------
    dgobject
        The modified ``dgobject``.  This is done for convenience; the
        object is modified in place.

    See Also
    --------
    composite_filter : Registering a composite filter.
    """
    dgobject.hidden = seb.diag_element.attrib.get("visible", "true") != "true"
    dgobject.hidelabel = False

    for flt in seb.diag_element.iterchildren("graphicalFilters"):
        flttype = flt.attrib[c.ATT_XMT]
        if flttype == "diagram:HideLabelFilter":
            dgobject.hidelabel = True
        elif flttype in {"diagram:HideFilter", "diagram:CollapseFilter"}:
            dgobject.hidden = True
        elif flttype == "diagram:AppliedCompositeFilters":
            _set_composite_filter(seb, dgobject, flt)
        else:
            c.LOGGER.warning("Ignoring unknown filter type %r", flttype)
    return dgobject


def applyfilters(
    target_diagram: aird.Diagram,
    diagram_root: etree._Element,
    melodyloader: capellambse.loader.MelodyLoader,
) -> None:
    """Apply filters on the ``target_diagram``.

    This function performs two tasks.

    Firstly it executes phase 2 of all elements' composite filters; see
    :func:`composite_filter` for more details.

    Secondly it applies the diagram's global filters.  These are always
    applied after all composite filters have run.

    Parameters
    ----------
    target_diagram
        The diagram.
    diagram_root
        The LXML element that is this diagram's root.
    melodyloader
        The MelodyLoader instance.
    """
    # Apply post-processing filters on elements
    for dgobject in target_diagram:
        try:
            filters = dgobject._compfilters  # type: ignore[union-attr]
        except AttributeError:
            continue
        assert dgobject.uuid is not None

        flttype: str
        p2flt: Phase2CompositeFilter
        for flttype, p2flt in filters:
            c.LOGGER.debug(
                "Applying post-processing filter %r to %s %r",
                flttype,
                dgobject.styleclass or dgobject.__class__.__name__,
                dgobject.uuid,
            )
            data_element = melodyloader[dgobject.uuid]
            p2flt(
                c.ElementBuilder(
                    target_diagram=target_diagram,
                    diagram_tree=diagram_root,
                    data_element=data_element,
                    melodyloader=melodyloader,
                    fragment=melodyloader.find_fragment(data_element),
                ),
                dgobject,
            )

        del dgobject._compfilters  # type: ignore[union-attr]

    # Apply global diagram filters
    for flt in diagram_root.iterchildren("activatedFilters"):
        try:
            flttype = flt.attrib[c.ATT_XMT]
        except KeyError:
            flttype = "(no filter type given)"
        if flttype != "filter:CompositeFilterDescription":
            c.LOGGER.warning("Unknown global filter type %r", flttype)
            continue

        try:
            fltname = _extract_filter_type(flt)
        except ValueError as err:
            c.LOGGER.warning("Ignoring broken global filter: %s", err)
            continue

        try:
            fltfunc = GLOBAL_FILTERS[fltname]
        except KeyError:
            c.LOGGER.warning("Unknown global filter %r", fltname)
            continue

        c.LOGGER.debug("Applying global filter %r", fltname)
        fltfunc(target_diagram, diagram_root, flt, melodyloader)


def _set_composite_filter(
    seb: c.SemanticElementBuilder,
    dgobject: aird.DiagramElement,
    flt: etree._Element,
) -> None:
    try:
        flttype = _extract_filter_type(
            next(flt.iterchildren("compositeFilterDescriptions"))
        )
    except (StopIteration, ValueError):
        c.LOGGER.warning(
            "Ignoring unusable composite filter on object %r", dgobject.uuid
        )
        return

    try:
        fltfunc = COMPOSITE_FILTERS[flttype]
    except KeyError:
        c.LOGGER.warning(
            "Unknown composite filter %r on object %r", flttype, dgobject.uuid
        )
        return

    phase2 = fltfunc(seb, dgobject)

    # Register the phase 2 callable
    if phase2 is None:
        return
    if not hasattr(dgobject, "_compfilters"):
        dgobject._compfilters = []  # type: ignore[union-attr]
    dgobject._compfilters.append((flttype, phase2))  # type: ignore[union-attr]


def _extract_filter_type(flt_elm: etree._Element) -> str:
    try:
        flttype = flt_elm.attrib["href"]
    except KeyError:
        raise ValueError("Filter element has no href") from None

    flttype = c.RE_COMPOSITE_FILTER.search(flttype)
    if not flttype or not flttype.group(1):
        raise ValueError("Filter href does not match known pattern") from None

    return urllib.parse.unquote(flttype.group(1))


# Load filter modules
for module in ("composite", "global"):
    try:
        importlib.import_module(f"{__name__}.{module}")
    except Exception as _err:  # pylint: disable=broad-except
        c.LOGGER.error(
            "Cannot load filters from %s: %s: %s",
            module,
            _err.__class__.__name__,
            _err,
        )
del module
