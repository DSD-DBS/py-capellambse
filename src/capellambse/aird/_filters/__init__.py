# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Functions implementing various filters that Capella supports."""

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import importlib
import typing as t
import urllib.parse

from lxml import etree

import capellambse.loader
from capellambse import aird, diagram, model

from .. import _common as c

Phase2CompositeFilter = t.Callable[
    [c.ElementBuilder, diagram.DiagramElement], None
]
CompositeFilter = t.Callable[
    [c.ElementBuilder, diagram.DiagramElement],
    Phase2CompositeFilter | None,
]
COMPOSITE_FILTERS: dict[str, CompositeFilter] = {}
"""Maps composite filter names to phase-1 callables."""

GlobalFilter = t.Callable[["FilterArguments", etree._Element], None]
GLOBAL_FILTERS: dict[str, GlobalFilter] = {}
"""Maps names of global filters to functions that implement them."""

PLUGIN_PATH = (
    "/plugin/org.polarsys.capella.core.sirius.analysis"
    "/description/context.odesign#/"
)

_TDiagramElement = t.TypeVar("_TDiagramElement", bound=diagram.DiagramElement)


def composite_filter(
    name: str,
) -> cabc.Callable[[CompositeFilter], CompositeFilter]:
    """Register a composite filter.

    Composite filters are executed in two phases. The first phase occurs
    during each diagram element's creation. Here the callables
    registered with this decorator are directly executed with the
    diagram under construction and the to-be-filtered element as
    arguments.

    The second phase happens after the entire diagram has been created.
    Filters that want to run in this phase should return another
    callable object during the first phase; this object will then be
    called with the same (now constructed) diagram and the element.

    Composite filters should always operate in place. They may append
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
            _2: diagram.DiagramElement,
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
        The modified ``dgobject``. This is done for convenience; the
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


@dataclasses.dataclass(frozen=True)
class FilterArguments:
    """Basic arguments for diagram-filters."""

    target_diagram: diagram.Diagram
    diagram_root: etree._Element
    melodyloader: capellambse.loader.MelodyLoader
    params: dict[str, t.Any]


def applyfilters(args: FilterArguments) -> None:
    """Apply filters on the ``target_diagram``.

    This function performs two tasks.

    Firstly it executes phase 2 of all elements' composite filters; see
    :func:`composite_filter` for more details.

    Secondly it applies the diagram's global filters. These are always
    applied after all composite filters have run.
    """
    # Apply post-processing filters on elements
    for dgobject in args.target_diagram:
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
            data_element = args.melodyloader[dgobject.uuid]
            p2flt(
                c.ElementBuilder(
                    target_diagram=args.target_diagram,
                    diagram_tree=args.diagram_root,
                    data_element=data_element,
                    melodyloader=args.melodyloader,
                    fragment=args.melodyloader.find_fragment(data_element),
                ),
                dgobject,
            )

        del dgobject._compfilters  # type: ignore[union-attr]

    # Apply global diagram filters
    for flt in args.diagram_root.iterchildren("activatedFilters"):
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
            c.LOGGER.debug("Ignoring broken global filter: %s", err)
            continue

        try:
            fltfunc = GLOBAL_FILTERS[fltname]
        except KeyError:
            c.LOGGER.debug("Ignoring unknown global filter %r", fltname)
            continue

        c.LOGGER.debug("Applying global filter %r", fltname)
        fltfunc(args, flt)


def _set_composite_filter(
    seb: c.SemanticElementBuilder,
    dgobject: diagram.DiagramElement,
    flt: etree._Element,
) -> None:
    try:
        flttype = _extract_filter_type(
            next(flt.iterchildren("compositeFilterDescriptions"))
        )
    except (StopIteration, ValueError):
        c.LOGGER.debug(
            "Ignoring unusable composite filter on object %r", dgobject.uuid
        )
        return

    try:
        fltfunc = COMPOSITE_FILTERS[flttype]
    except KeyError:
        c.LOGGER.debug(
            "Ignoring unknown composite filter %r on object %r",
            flttype,
            dgobject.uuid,
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

    compfilter = c.RE_COMPOSITE_FILTER.search(flttype)
    if not compfilter or not compfilter.group(1):
        raise ValueError("Filter href does not match known pattern") from None

    return urllib.parse.unquote(compfilter.group(1))


class ActiveFilters(t.MutableSet[str]):
    """A set of active filters on a Diagram.

    Enable access to set, add and remove active filters on a
    :class:`~capellambse.diagram.Diagram`.
    """

    __slots__ = ("_diagram", "_model", "_target")
    _xml_tag = "activatedFilters"

    def __init__(
        self,
        model: model.MelodyModel,
        diagram: model.diagram.Diagram,
    ) -> None:
        self._model = model
        self._diagram = diagram
        assert isinstance(diagram._element, etree._Element)
        self._target = self._model._loader[diagram._element.attrib["repPath"]]

    @property
    def _elements(self) -> t.Iterator[etree._Element]:
        return self._target.iterchildren(self._xml_tag)

    @staticmethod
    def _get_filter_name(filter: etree._Element) -> str | None:
        filter_name = c.RE_COMPOSITE_FILTER.search(filter.get("href", ""))
        if filter_name:
            return filter_name.group(1)
        return None

    def __contains__(self, filter: object) -> bool:
        if not isinstance(filter, str):
            return False
        return filter in iter(self)

    def __iter__(self) -> cabc.Iterator[str]:
        for filter in self._elements:
            if filter_name := self._get_filter_name(filter):
                yield filter_name

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def add(self, value: str) -> None:
        """Add an activated filter to the diagram.

        Writes a new ``<activatedFilters>`` XML element to the
        ``<diagram:DSemanticDiagram>`` XML element. If the ``value`` is
        not apparent in :any:`capellambse.aird.GLOBAL_FILTERS` as a key
        it can not be applied when rendering. It should still be visible
        in the GUI.
        """
        if value in self:
            return

        diag_descriptor = aird._build_descriptor(
            self._model._loader, self._diagram._element
        )
        viewpoint = urllib.parse.quote(diag_descriptor.viewpoint)
        assert diag_descriptor.styleclass is not None
        diagclass = urllib.parse.quote(diag_descriptor.styleclass)
        href = "/".join(
            (
                f"platform:{PLUGIN_PATH}",
                f"@ownedViewpoints[name='{viewpoint}']",
                f"@ownedRepresentations[name='{diagclass}']",
                f"@filters[name='{value}']",
            )
        )
        elt = c.ELEMENT.activatedFilters(
            {"href": href, c.ATT_XMT: "filter:CompositeFilterDescription"}
        )
        self._target.append(elt)
        self._diagram.invalidate_cache()

    def discard(self, value: str) -> None:
        """Remove the filter with the given ``value`` from the diagram.

        Deletes ``<activatedFilters>`` XML element from the diagram
        element tree.
        """
        for filter in self._elements:
            filter_name = self._get_filter_name(filter)
            if filter_name is not None and value == filter_name:
                self._target.remove(filter)
                self._diagram.invalidate_cache()
                break

    def __repr__(self) -> str:  # pragma: no cover
        return f"{set(self)!r}"


# Load filter modules
for module in ("composite", "global"):
    try:
        importlib.import_module(f"{__name__}.{module}")
    except Exception as _err:
        c.LOGGER.error(
            "Cannot load filters from %s: %s: %s",
            module,
            _err.__class__.__name__,
            _err,
        )
del module
