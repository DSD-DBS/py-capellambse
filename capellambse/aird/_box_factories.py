# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Factory functions for different types of Boxes."""
from __future__ import annotations

import collections
import functools
import itertools
import re
import typing as t

import markupsafe

from capellambse import diagram, helpers

from . import _common as C
from . import _filters, _styling

_T = t.TypeVar("_T", bound=diagram.Box)


@t.overload
def generic_factory(
    seb: C.SemanticElementBuilder, *, minsize: diagram.Vector2D = ...
) -> diagram.Box:
    ...


@t.overload
def generic_factory(
    seb: C.SemanticElementBuilder,
    *,
    boxtype: type[_T] | functools.partial[_T],
    minsize: diagram.Vector2D = ...,
) -> _T:
    ...


def generic_factory(
    seb: C.SemanticElementBuilder,
    *,
    boxtype: type[diagram.Box]
    | type[_T]
    | functools.partial[_T] = diagram.Box,
    minsize: diagram.Vector2D = diagram.Vector2D(148, 69),
) -> _T:
    """Construct a Box from the diagram XML."""
    if seb.diag_element.getparent() is not seb.diagram_tree:
        parent_uid = seb.diag_element.getparent().attrib.get("uid")
    else:
        parent_uid = None

    if parent_uid is None:
        parent = None
        refpos = diagram.Vector2D(0, 0)
    else:
        try:
            # reference position (top left of parent box)
            parent = seb.target_diagram[parent_uid]
            refpos = parent.bounds.pos
        except KeyError:
            C.LOGGER.error(
                "Parent not in diagram, cannot draw box with uid %r",
                seb.data_element.attrib["element"],
            )
            raise C.SkipObject() from None
    assert parent is None or isinstance(parent, diagram.Box)

    try:
        layout = next(seb.data_element.iterchildren("layoutConstraint")).attrib
        ostyle = next(seb.diag_element.iterchildren("ownedStyle"))
    except StopIteration:
        C.LOGGER.error(
            "Cannot find style or layout for %r",
            seb.data_element.attrib["element"],
        )
        raise C.SkipObject() from None

    box_is_port = seb.diag_element.tag == "ownedBorderedNodes"
    box_is_symbol = ostyle.get("workspacePath") is not None

    pos = refpos + (int(layout.get("x", 0)), int(layout.get("y", 0)))
    if box_is_port:
        size = C.PORT_SIZE
    else:
        size = diagram.Vector2D(
            int(layout.get("width", 0)), int(layout.get("height", 0))
        )
        style_type = ostyle.attrib[C.ATT_XMT].split(":")[-1]
        if style_type == "FlatContainerStyle":
            # Remove drop shadows
            size -= (2 if size.x >= 2 else 0, 2 if size.y >= 2 else 0)
    styleoverrides = _styling.apply_style_overrides(
        seb.target_diagram.styleclass, f"Box.{seb.styleclass}", ostyle
    )

    label = seb.melodyobjs[0].attrib.get("name")
    pos += (
        int(seb.diag_element.attrib.get("width", (5, -1)[box_is_port])),
        int(seb.diag_element.attrib.get("height", (5, -1)[box_is_port])),
    )

    if box_is_port and parent is not None:
        parent.add_context(seb.data_element.attrib["element"])

    if label:
        if box_is_port:
            label = _make_portlabel(pos, size, label, seb)
        elif box_is_symbol:
            label = _make_free_floating_label(pos, size, label, seb)
    box = boxtype(
        pos,
        size,
        label=label,
        collapsed=_is_collapsed(seb),
        port=box_is_port,
        uuid=seb.data_element.attrib["element"],
        styleclass=seb.styleclass,
        # <https://github.com/python/mypy/issues/8136#issuecomment-565387901>
        styleoverrides=styleoverrides,  # type: ignore[arg-type]
        minsize=minsize,
    )
    if box_is_symbol:
        box.JSON_TYPE = "symbol"
        box.minsize = (30, 30)
    _filters.setfilters(seb, box)
    box.parent = parent
    return t.cast(_T, box)


def generic_stacked_factory(seb: C.SemanticElementBuilder) -> C.StackingBox:
    """Construct a Box whose children stack."""
    child_layout = (
        seb.diag_element.get("childrenPresentation") or "VerticalStack"
    )
    return generic_factory(
        seb,
        boxtype=functools.partial(
            C.StackingBox, features=[], stacking_mode=child_layout
        ),
    )


def class_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create a Class.

    Classes contain multiple `Property` sub-elements.  These aren't
    actual boxes, but should instead be shown as part of the Class'
    regular label text.
    """
    box = generic_factory(seb, minsize=diagram.Vector2D(93, 43))

    if seb.melodyobjs[0].attrib.get("abstract", "false") == "true":
        box.styleoverrides["text_font-style"] = "italic"

    features = collections.defaultdict[str, list[str]](list)
    for feature in seb.melodyobjs[0].iterchildren("ownedFeatures"):
        feat_name = feature.attrib["name"]
        feat_type = feature.attrib[C.ATT_XST].split(":")[-1]

        abstract_type = feature.attrib.get("abstractType")
        if abstract_type is not None:
            abstract_type = seb.melodyloader.follow_link(
                seb.melodyobjs[0], abstract_type
            )

        if feat_type == "Property":
            if feature.attrib.get("aggregationKind") is not None:
                continue

            if feature.attrib.get("isDerived") is not None:
                feat_name = f"/{feat_name}"

            if abstract_type is not None:
                feat_name += f" : {abstract_type.attrib['name']}"
        elif feat_type == "Service":
            params = []
            ret = []
            throw = []

            for param in feature.iterchildren("ownedParameters"):
                param_type = param.attrib[C.ATT_XST].split(":")[-1]
                if param_type != "Parameter":
                    C.LOGGER.warning(
                        "Unknown parameter type %r for service %r",
                        param_type,
                        feat_name,
                    )
                    continue
                param_name = param.attrib["name"]
                param_abstrtype = param.attrib.get("abstractType")
                if param_abstrtype is not None:
                    param_abstrtype = seb.melodyloader.follow_link(
                        seb.melodyobjs[0], param_abstrtype
                    )
                    param_name += f":{param_abstrtype.attrib['name']}"
                param_dir = param.attrib.get("direction", "IN")
                if param_dir == "RETURN":
                    ret.append(param_name)
                elif param_dir == "EXCEPTION":
                    throw.append(param_name)
                else:
                    params.append(f"{param_dir} {param_name}")

            feat_name += f"({', '.join(params)})"
            if ret or throw:
                feat_name += " : "
            if ret:
                feat_name += f" returns {', '.join(ret)}"
            if throw:
                feat_name += f" throws {', '.join(throw)}"
        else:
            C.LOGGER.warning("Unknown feature type %r", feat_type)
        features[feat_type].append(feat_name)

    box.features = sum(features.values(), list[str]())
    return box


def component_port_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    box = generic_factory(seb)
    try:
        box.styleclass = "CP_" + (seb.melodyobjs[0].attrib["orientation"])
    except KeyError:
        box.styleclass = "CP_UNSET"

    return box


def constraint_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create the box for a Constraint.

    Constraints are comprised of two parts: A Box and some Edges.  The
    Box' label must be extracted from the semantic object, because it
    isn't always easily accessible for the ``generic_factory``.

    See Also
    --------
    capellambse.aird._edge_factories.constraint_factory :
        The accompanying edge factory.
    """
    box = generic_factory(seb)
    label = C.get_spec_text(seb) or seb.melodyobjs[0].attrib.get("name")
    if isinstance(label, markupsafe.Markup):
        box.label = label.striptags()
    else:
        box.label = label
    return box


def control_node_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    r"""Differentiate ``ControlNode``\ s based on their KIND."""
    assert seb.styleclass is not None
    kind = seb.melodyobjs[0].get("kind", "OR")
    seb.styleclass = "".join((kind.capitalize(), seb.styleclass))
    return generic_factory(seb)


def enumeration_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create an Enumeration.

    These work similar to Classes, but use different element tags.
    """
    box = generic_factory(seb)
    box.features = []

    for lit_elm in seb.melodyobjs[0].iterchildren("ownedLiterals"):
        lit_type = lit_elm.attrib[C.ATT_XST]
        if lit_type.split(":")[-1] != "EnumerationLiteral":
            C.LOGGER.warning(
                "Unknown enumeration literal type %r, skipping", lit_type
            )
            continue
        box.features.append(lit_elm.attrib["name"])

    return box


def part_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Resolve the ``Part`` meta-styleclass and creates its Box."""
    dgel_type = seb.diag_element.attrib[C.ATT_XMT]
    if dgel_type in {"diagram:DNodeContainer", "diagram:DNode"}:
        # resolve abstractType reference
        abstract_obj = seb.melodyobjs[0]
        abstract_type = abstract_obj.attrib.get("abstractType")
        if abstract_type is not None:
            abstract_obj = seb.melodyloader.follow_link(
                seb.melodyobjs[0], abstract_type
            )

        seb.styleclass = abstract_obj.attrib[C.ATT_XST].split(":")[-1]
        assert seb.styleclass is not None
        if seb.styleclass.endswith("Component"):
            seb.styleclass = "".join(
                (
                    seb.styleclass[: -len("Component")],
                    "Human" * (abstract_obj.get("human") == "true"),
                    ("Component", "Actor")[
                        abstract_obj.get("actor") == "true"
                    ],
                )
            )

        return generic_factory(seb)

    C.LOGGER.error("Unhandled Part type: %r; skipping", dgel_type)
    raise C.SkipObject()


def requirements_box_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create a Requirement.

    Requirements' text is split in two parts, which have to be joined
    together again for display in diagrams.
    """
    # Only handle the top-level <ownedDiagramElements>,
    # not the nested <ownedElements>.
    if seb.diag_element.tag != "ownedDiagramElements":
        raise C.SkipObject()

    try:
        targetlink = next(seb.diag_element.iterchildren("target"))
        targethref = targetlink.attrib["href"]
    except (StopIteration, KeyError):
        raise C.SkipObject() from None

    seb.melodyobjs[0] = seb.melodyloader.follow_link(targetlink, targethref)
    text = [
        string
        for suffix in ("LongName", "Name", "ChapterName")
        if (string := seb.melodyobjs[0].get("ReqIF" + suffix, ""))
    ]
    if "ReqIFText" in seb.melodyobjs[0].attrib:
        text.append(helpers.repair_html(seb.melodyobjs[0].attrib["ReqIFText"]))

    box = generic_factory(seb, minsize=diagram.Vector2D(0, 0))
    box.features = [f"- {i}" for i in text if i is not None]
    if not (box.label or box.features):
        sdata_element = seb.data_element.attrib["element"]
        raise ValueError(f"Requirements text is empty for {sdata_element!r}")
    return box


def region_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    r"""Perform special handling for ``Region``\ s.

    *   Adjust the styleclass of Regions to ``StateRegion`` or
        ``ModeRegion``, depending on what the parent box is
    *   Fix the Region's label text
    *   Set the Region's specific minimum / default size (because
        they're different from the usual values)
    """
    try:
        parent = seb.target_diagram[seb.diag_element.getparent().attrib["uid"]]
    except KeyError:
        pass
    else:
        seb.styleclass = f'{parent.styleclass or ""}Region'

    box = generic_factory(seb)
    if box.label is None:
        pass
    elif isinstance(box.label, str):
        box.label = f"[{box.label}]"
    else:
        box.label.label = f"[{box.label.label}]"
    box.minsize = (27, 21)
    box.size = diagram.Vector2D(box._size.x or 55, box._size.y or 41)
    return box


def statemode_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create a State or Mode.

    Unlike other elements, these have their immediate children rendered
    as stacked boxes.  The child boxes themselves can in turn have more
    children either in floating or stacked form.

    Additionally, States and Modes can have associated activities.
    These are displayed after the label, separated by a horizontal line.
    """
    xmt = seb.diag_element.get(C.ATT_XMT)
    if xmt == "diagram:DNodeContainer":
        return generic_stacked_factory(seb)
    if xmt == "diagram:DNodeList":
        return statemode_activities_factory(seb)
    C.LOGGER.warning("Unknown State/Mode xmi:type %r", xmt)
    raise C.SkipObject()


def statemode_activities_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Attach the activities to a State or Mode as features."""
    parent_id = seb.diag_element.getparent().attrib["uid"]
    try:
        parent = seb.target_diagram[parent_id]
    except KeyError:
        C.LOGGER.error("Cannot find a box with UID %r in diagram", parent_id)
        raise C.SkipObject() from None
    assert isinstance(parent, diagram.Box)

    entry: list[str] = []
    do: list[str] = []
    exit: list[str] = []
    for elm in seb.diag_element.iterchildren("ownedElements"):
        elm_id = elm.get("uid")
        try:
            target = next(elm.iterchildren("target")).attrib
            target = " ".join((target[C.ATT_XMT], target["href"]))
            target = seb.melodyloader[target]
            mapping = next(elm.iterchildren("actualMapping")).attrib["href"]
        except (KeyError, StopIteration):
            C.LOGGER.error("No usable target or mapping for %r", elm_id)
            continue

        mapping = re.search(
            "@subNodeMappings\\[name=(?P<q>[\"'])(?P<n>.*?)(?P=q)\\]$", mapping
        )
        if mapping is not None:
            mapping = mapping.group("n")
        try:
            act_list = {
                "MSM_DoActivity": do,
                "MSM_Entry": entry,
                "MSM_Exit": exit,
            }[mapping]
        except KeyError:
            C.LOGGER.error("Unknown activity mapping type %r", mapping)
            continue
        act_list.append(target.get("name"))

    parent.features = list(
        itertools.chain(
            (f" entry / {i}" for i in entry),
            (f" do / {i}" for i in do),
            (f" exit / {i}" for i in exit),
        )
    )
    raise C.SkipObject()


def fcif_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create a FunctionalChainInvolvementFunction.

    These are special boxes that point to another element via their
    ``involved`` attribute.  As there's no relevant information stored
    in the original target attribute, we can simply use the "involved"
    element for constructing the actual box.
    """
    seb.melodyobjs[0] = seb.melodyloader.follow_link(
        seb.melodyobjs[0], seb.melodyobjs[0].get("involved")
    )
    xtype = helpers.xtype_of(seb.melodyobjs[0])
    assert xtype is not None
    if xtype.endswith("Function"):
        seb.styleclass = "Function"
    else:
        seb.styleclass = xtype.split(":")[-1]
    return generic_factory(seb)


def pseudo_symbol_factory(seb: C.SemanticElementBuilder) -> diagram.Box:
    """Create a [Fork|Choice]PseudoState.

    These are boxes that behave like symbols. Capella doesn't store the
    usual workspacePath attribute that references the used image for
    symbols.
    """
    style = next(seb.diag_element.iterchildren("ownedStyle"))
    style.attrib["workspacePath"] = ""
    box = generic_factory(seb)
    box.JSON_TYPE = "box_symbol"
    return box


def _make_portlabel(
    ppos: diagram.Vector2D,
    psize: diagram.Vector2D,
    text: str,
    seb: C.SemanticElementBuilder,
) -> diagram.Box:
    snapsides = {"5001": (1, 0), "5010": (0, 1)}
    try:
        child_elm = next(
            i
            for i in seb.data_element.iterchildren("children")
            if i.get("type") in snapsides
        )
        loc_elm = next(
            i
            for i in child_elm.iterchildren("layoutConstraint")
            if i.get(C.ATT_XMT) == "notation:Location"
        )
    except StopIteration:
        snapside = diagram.Vector2D(1, 0)
    else:
        snapside = (
            diagram.Vector2D(
                int(loc_elm.get("x", "0")), int(loc_elm.get("y", "0"))
            )
            @ snapsides[child_elm.get("type")]
        )
        if snapside == (0, 0):
            snapside = diagram.Vector2D(1, 0)
        else:
            snapside //= snapside.length
    return _make_snapped_floating_label(ppos, psize, text, snapside)


def _make_free_floating_label(
    ppos: diagram.Vector2D,
    psize: diagram.Vector2D,
    text: str,
    seb: C.SemanticElementBuilder,
) -> diagram.Box:
    """Try to construct the label from the real location found in aird file."""
    try:
        child_elm = next(
            i
            for i in seb.data_element.iterchildren("children")
            if i.get("type") == "5002"
        )
        loc_elm = next(
            i
            for i in child_elm.iterchildren("layoutConstraint")
            if i.get(C.ATT_XMT) == "notation:Location"
        )
    except StopIteration:
        return _make_snapped_floating_label(
            ppos, psize, text, diagram.Vector2D(0, -1)
        )
    pos = ppos + (float(loc_elm.get("x", "0")), float(loc_elm.get("y", "0")))
    return diagram.Box(pos, (0, 0), label=text, styleclass="BoxAnnotation")


def _make_snapped_floating_label(
    ppos: diagram.Vector2D,
    psize: diagram.Vector2D,
    text: str,
    snapside: diagram.Vector2D,
) -> diagram.Box:
    if not isinstance(snapside.x, int) or not isinstance(snapside.y, int):
        raise TypeError("snapside must be an int-vector")
    if not (-1 <= snapside.x <= 1 and -1 <= snapside.y <= 1):
        raise ValueError("snapside values must be in interval [-1, 1]")
    if snapside.x and snapside.y:
        raise ValueError("snapside can only have one non-zero value")
    if snapside.x == snapside.y == 0:
        raise ValueError("snapside must have one non-zero value")
    labelbox = diagram.Box(
        (0, 0), (0, 0), label=text, styleclass="BoxAnnotation"
    )
    lsize = labelbox.size
    labelbox.pos = (
        (
            (lambda: ppos.x - (lsize.x - psize.x) / 2),
            (lambda: ppos.x + psize.x + diagram.Box.PORT_OVERHANG),
            (lambda: ppos.x - lsize.x - diagram.Box.PORT_OVERHANG),
        )[snapside.x](),
        (
            (lambda: ppos.y - (lsize.y - psize.y) / 2),
            (lambda: ppos.y + psize.y + diagram.Box.PORT_OVERHANG),
            (lambda: ppos.y - lsize.y - diagram.Box.PORT_OVERHANG),
        )[snapside.y](),
    )
    return labelbox


def _is_collapsed(seb: C.SemanticElementBuilder) -> bool:
    for data_container in seb.data_element.iterchildren():
        if data_container.get("type") == "7002":
            break
    else:
        return False

    for collapsed_container in data_container.iterchildren():
        if collapsed_container.get(C.ATT_XMT) == "notation:DrawerStyle":
            break
    else:
        return False

    return collapsed_container.get("collapsed") == "true"
