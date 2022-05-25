# Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Functions implementing various filters that Capella supports."""
from __future__ import annotations

import collections.abc as cabc
import importlib
import logging
import typing as t
import urllib.parse

import markupsafe
from lxml import etree

import capellambse.loader
from capellambse import aird
from capellambse import model as _m

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
LOGGER = logging.getLogger(__name__)

XP_PLUGIN = "/plugin/org.polarsys.capella.core.sirius.analysis/description/context.odesign#/"

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


class ActiveFilters(t.MutableSet[str]):
    """A set of active filters on a :class:`diag.Diagram`.

    Enable access to set, add and remove active filters on a
    :class:`diag.Diagram`.
    """

    __slots__ = ("_model", "_target", "_diagram")
    _xml_tag = "activatedFilters"

    def __init__(
        self, model: _m.MelodyModel, diagram: _m.diagram.Diagram
    ) -> None:
        self._model = model
        self._diagram = diagram
        self._target = self._model._loader[diagram._element.uid]

    @property
    def _elements(self) -> list[etree._Element]:
        return list(self._target.iterchildren(self._xml_tag))

    @staticmethod
    def _get_filter_name(filter: etree._Element) -> str | None:
        filter_name = c.RE_COMPOSITE_FILTER.search(filter.get("href", ""))
        if filter_name is not None:
            return filter_name.group(1)
        return None

    def __contains__(self, filter: str | etree._Element) -> bool:
        if isinstance(filter, str):
            return filter in iter(self)

        filter_name = self._get_filter_name(filter)
        if filter.tag != self._xml_tag or filter_name is None:
            return False

        for flt_name in iter(self):
            if filter_name in flt_name:
                return True
        return False

    def __iter__(self) -> cabc.Iterator[str]:
        for filter in self._elements:
            if (filter_name := self._get_filter_name(filter)) is not None:
                yield filter_name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, cabc.Iterable):
            return False

        for elt in other:
            if elt not in self:
                return False

        return True

    def __len__(self) -> int:
        return len(list(self))

    def add(  # pylint: disable=arguments-renamed
        self, filter_name: str
    ) -> None:
        """Add an activated filter to the diagram.

        Writes a new <activatedFilters> XML element to the
        <diagram:DSemanticDiagram> XML element. If the `filter_name` is
        not apparent in :data:`aird.parser.GLOBAL_FILTERS` as a key it
        can not be applied when rendering. It should still be visible in
        the GUI.
        """
        if filter_name in iter(self):
            raise ValueError("This filter is already active on this diagram.")

        diag_descriptor = self._diagram._element
        history_elt = next(self._target.iterfind("filterVariableHistory"))
        viewpoint = urllib.parse.quote(diag_descriptor.viewpoint)
        assert diag_descriptor.styleclass is not None
        diagclass = urllib.parse.quote(diag_descriptor.styleclass)
        href = "/".join(
            (
                f"platform:{XP_PLUGIN}",
                f"@ownedViewpoints[name='{viewpoint}']",
                f"@ownedRepresentations[name='{diagclass}']",
                f"@filters[name='{filter_name}']",
            )
        )
        elt = c.ELEMENT.activatedFilters(
            {"href": href, c.ATT_XMT: "filter:CompositeFilterDescription"}
        )
        history_elt.addprevious(elt)
        self._diagram._force_fresh_rendering = True

    def discard(self, name: str) -> None:  # pylint: disable=arguments-renamed
        """Discard the filter with the given `name` from the diagram.

        See also
        --------
        :py:method:`self.remove`
        """
        try:
            self.remove(name)
        except KeyError:
            pass

    def remove(self, name: str) -> None:  # pylint: disable=arguments-renamed
        """Remove the filter with the given `name` from the diagram.

        Deletes <activatedFilters> XML element from the diagram element
        tree.
        """
        for filter in self._elements:
            search = self._get_filter_name(filter)
            if search is not None and name == search:
                break
        else:
            raise KeyError(f"No activated filter with name: '{name}'")

        self._target.remove(filter)  # pylint: disable=undefined-loop-variable
        self._diagram._force_fresh_rendering = True

    def clear(self) -> None:
        for elt in self._elements:
            self._target.remove(elt)
        self._diagram._force_fresh_rendering = True

    def __str__(self) -> str:  # pragma: no cover
        return "\n".join(f"* {e!s}" for e in self)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} at 0x{id(self):016X} {set(self)!r}>"

    def __html__(self) -> markupsafe.Markup:
        if not self:
            return markupsafe.Markup("<p><em>(Empty set)</em></p>")

        fragments = ['<ol start="0" style="text-align: left;">']
        fragments.extend((f"<li>{i}</li>" for i in self))
        fragments.append("</ol>")
        return markupsafe.Markup("".join(fragments))

    def _short_html_(self) -> markupsafe.Markup:
        return self.__html__()

    def _repr_html_(self) -> str:
        return self.__html__()


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
