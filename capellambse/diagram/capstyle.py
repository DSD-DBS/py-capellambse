# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The color palette and default style definitions used by Capella."""

from __future__ import annotations

__all__ = ["COLORS", "CSSdef", "STYLES", "RGB", "get_style"]

import logging
import typing as t

from capellambse import helpers

LOGGER = logging.getLogger(__name__)


class RGB(t.NamedTuple):
    """A color.

    Each color component (red, green, blue) is an integer in the range
    of 0..255 (inclusive). The alpha channel is a float between 0.0 and
    1.0 (inclusive). If it is 1, then the ``str()`` form does not
    include transparency information.
    """

    r: int = 0
    g: int = 0
    b: int = 0
    a: float = 1.0

    def __str__(self) -> str:
        return "#" + self.tohex()

    def tohex(self) -> str:
        assert all(0 <= n <= 255 for n in self[:3])
        assert 0.0 <= self.a <= 1.0
        if self.a >= 1.0:
            return f"{self.r:02X}{self.g:02X}{self.b:02X}"
        return f"{self.r:02X}{self.g:02X}{self.b:02X}{int(self.a * 255):02X}"

    @classmethod
    def fromcss(cls, cssstring: str | RGB) -> RGB:
        """Create an RGB from a CSS color definition.

        Examples of recognized color definitions and their equivalent
        constructor calls::

            "rgb(10, 20, 30)" -> RGB(10, 20, 30)
            "rgba(50, 60, 70, 0.5)" -> RGB(50, 60, 70, 0.5)
            "#FF00FF" -> RGB(255, 0, 255)
            "#ff00ff" -> RGB(255, 0, 255)
            "#f0f" -> RGB(255, 0, 255)
            "#FF00FF80" -> RGB(255, 0, 255, 0.5)
            "#f0fa" -> RGB(255, 0, 255, 2/3)
        """
        if isinstance(cssstring, RGB):
            return cssstring

        cssstring = cssstring.strip().lower()
        if cssstring.startswith(("rgb(", "rgba(")) and cssstring.endswith(")"):
            return cls.fromcsv(cssstring[cssstring.find("(") : -1])
        if cssstring.startswith("#"):
            return cls.fromhex(cssstring[1:])
        raise ValueError(f"Bad CSS color: {cssstring!r}")

    @classmethod
    def fromcsv(cls, csvstring: str) -> RGB:
        """Create an RGB from a ``"r, g, b[, a]"`` string."""
        split = csvstring.split(",")
        if len(split) == 4:
            alpha = float(split.pop())
        else:
            alpha = 1.0
        if len(split) == 3:
            r, g, b = (int(c) for c in split)
            return cls(r, g, b, alpha)
        raise ValueError(f"Expected 3 or 4 values: {csvstring}")

    @classmethod
    def fromhex(cls, hexstring: str) -> RGB:
        """Create an RGB from a hexadecimal string.

        The string can have 3, 4, 6 or 8 hexadecimal characters. In the
        cases of 3 and 6 characters, the alpha channel is set to 1.0
        (fully opaque) and the remaining characters are interpreted as
        the red, green and blue components.
        """
        if hexstring.startswith("#"):
            hs = hexstring[1:]
        else:
            hs = hexstring
        alpha = 1.0
        slen = len(hs)

        if slen == 4:
            hs, alpha = hs[:3], int(hs[3:], base=16) / 16
            slen = 3
        if slen == 3:
            r, g, b = (int(x * 2, base=16) for x in hs)
            return cls(r, g, b, alpha)

        if slen == 8:
            hs, alpha = hs[:6], int(hs[6:], base=16) / 255
            slen = 6
        if slen == 6:
            r, g, b = (
                int("".join(x), base=16) for x in helpers.ntuples(2, hs)
            )
            return cls(r, g, b, alpha)

        raise ValueError(
            "Invalid length of hex string, expected 3, 4, 6 or 8 characters"
        )


def get_style(diagramclass: str | None, objectclass: str) -> dict[str, t.Any]:
    r"""Fetch the default style for the given drawtype and styleclass.

    The style is returned as a dict with key-value pairs as used by CSS
    inside SVG graphics.

    All values contained in this dict are either of type :class:`str`,
    or of a class whose ``str()`` representation results in a valid CSS
    value for its respective key -- with one exception: color gradients.

    Flat colors are represented using the :class:`RGB` tuple subclass.
    Gradients are returned as a two-element list of :class:`RGB`\ s the
    first one is the color at the top of the object, the second one at
    the bottom.

    Parameters
    ----------
    diagramclass
        The style class of the diagram.
    objectclass
        A packed :class:`str` describing the element's type and style
        class in the form::

            Type.StyleClass

        The type can be: ``Box``, ``Edge``. The style class can be any
        known style class.
    """
    if "." not in objectclass:
        raise ValueError(f"Malformed objectclass: {objectclass}")

    if "symbol" in objectclass.lower():
        return {}

    obj_type: str = objectclass.split(".", 1)[0]
    return {
        **STYLES["__GLOBAL__"].get(obj_type, {}),
        **STYLES.get(diagramclass or "", {}).get(obj_type, {}),
        **STYLES["__GLOBAL__"].get(objectclass, {}),
        **STYLES.get(diagramclass or "", {}).get(objectclass, {}),
    }


#: This dict maps the color names used by Capella to RGB tuples.
COLORS: dict[str, RGB] = {
    # System palette
    "black": RGB(0, 0, 0),
    "dark_gray": RGB(69, 69, 69),
    "dark_orange": RGB(224, 133, 3),
    "dark_purple": RGB(114, 73, 110),
    "gray": RGB(136, 136, 136),
    "light_purple": RGB(217, 196, 215),
    "light_yellow": RGB(255, 245, 181),
    "red": RGB(239, 41, 41),
    "white": RGB(255, 255, 255),
    # "Migration Palette" from common.odesign
    "_CAP_Activity_Border_Orange": RGB(91, 64, 64),
    "_CAP_Activity_Orange": RGB(247, 218, 116),
    "_CAP_Activity_Orange_min": RGB(255, 255, 197),
    "_CAP_Actor_Blue": RGB(198, 230, 255),
    "_CAP_Actor_Blue_label": RGB(0, 0, 0),
    "_CAP_Actor_Blue_min": RGB(218, 253, 255),
    "_CAP_Actor_Border_Blue": RGB(74, 74, 151),
    "_CAP_Association_Color": RGB(0, 0, 0),
    "_CAP_ChoicePseudoState_Border_Gray": RGB(0, 0, 0),
    "_CAP_ChoicePseudoState_Color": RGB(168, 168, 168),
    "_CAP_Class_Border_Brown": RGB(123, 105, 79),
    "_CAP_Class_Brown": RGB(232, 224, 210),
    "_CAP_CombinedFragment_Gray": RGB(242, 242, 242),
    "_CAP_Component_Blue": RGB(150, 177, 218),
    "_CAP_Component_Blue_min": RGB(195, 230, 255),
    "_CAP_Component_Border_Blue": RGB(74, 74, 151),
    "_CAP_Component_Label_Blue": RGB(74, 74, 151),
    "_CAP_ConfigurationItem_Gray": RGB(242, 238, 225),
    "_CAP_ConfigurationItem_Gray_min": RGB(249, 248, 245),
    "_CAP_Datatype_Border_Gray": RGB(103, 103, 103),
    "_CAP_Datatype_Gray": RGB(225, 223, 215),
    "_CAP_Datatype_LightBrown": RGB(232, 224, 210),
    "_CAP_Entity_Gray": RGB(221, 221, 200),
    "_CAP_Entity_Gray_border": RGB(69, 69, 69),
    "_CAP_Entity_Gray_label": RGB(0, 0, 0),
    "_CAP_Entity_Gray_min": RGB(249, 248, 245),
    "_CAP_ExchangeItem_Pinkkish": RGB(246, 235, 235),
    "_CAP_FCD": RGB(233, 243, 222),
    "_CAP_FCinFCD_Green": RGB(148, 199, 97),
    "_CAP_InterfaceDataPackage_LightGray": RGB(250, 250, 250),
    "_CAP_Interface_Border_Reddish": RGB(124, 61, 61),
    "_CAP_Interface_Pink": RGB(240, 221, 221),
    "_CAP_Lifeline_Gray": RGB(128, 128, 128),
    "_CAP_MSM_Mode_Gray": RGB(195, 208, 208),
    "_CAP_MSM_Mode_Gray_min": RGB(234, 239, 239),
    "_CAP_MSM_State_Gray": RGB(208, 208, 208),
    "_CAP_MSM_State_Gray_min": RGB(239, 239, 239),
    "_CAP_Mode_Gray": RGB(165, 182, 180),
    "_CAP_Node_Yellow": RGB(255, 252, 183),
    "_CAP_Node_Yellow_Border": RGB(123, 105, 79),
    "_CAP_Node_Yellow_Label": RGB(0, 0, 0),
    "_CAP_Node_Yellow_min": RGB(255, 255, 220),
    "_CAP_OperationalRole_Purple": RGB(203, 174, 200),
    "_CAP_Operational_Process_Reference_Orange": RGB(250, 239, 203),
    "_CAP_PhysicalPort_Yellow": RGB(255, 244, 119),
    "_CAP_StateMode_Border_Gray": RGB(117, 117, 117),
    "_CAP_StateTransition_Color": RGB(0, 0, 0),
    "_CAP_State_Gray": RGB(228, 228, 228),
    "_CAP_Unit_LightBrown": RGB(214, 197, 171),
    "_CAP_Unset_Gray": RGB(205, 205, 205),
    "_CAP_Unset_Gray_min": RGB(234, 234, 234),
    "_CAP_Value_LightBrown": RGB(254, 253, 250),
    "_CAP_xAB_Activity_Label_Orange": RGB(91, 64, 64),
    "_CAP_xAB_Function_Border_Green": RGB(9, 92, 46),
    "_CAP_xAB_Function_Green": RGB(197, 255, 166),
    "_CAP_xAB_Function_Label_Green": RGB(9, 92, 46),
    "_CAP_xBD_ControlNode": RGB(223, 223, 223),
    "_CAP_xDFB_Function_Border_Green": RGB(77, 137, 20),
    "_CAP_xDFB_Function_Green": RGB(197, 255, 166),
    "_CAP_xDFB_Function_Green_Label": RGB(0, 0, 0),
    "_CAP_xDFB_Function_Green_min": RGB(244, 255, 224),
    "_CAP_xDF_Activity_Label_Orange": RGB(0, 0, 0),
}


#: This dict contains the default styles that Capella applies, grouped
#: by the diagram class they belong to.
#:
#: The first level of keys are the diagrams' styleclasses. The special
#: key "__GLOBAL__" applies to all diagrams.
#:
#: The second level contains the style definitions for each element that
#: can appear in the diagram. The keys work in the following way:
#:
#:     Type.Class
#:
#: * ``Type`` is the element type; one of "Box" or "Edge" (note casing!)
#: * ``Class`` is the element's styleclass, e.g. "LogicalComponent"
#:
#: The ``Class`` and the preceding dot may be absent, in which case that
#: styling applies to all elements of that ``Type`` regardless of their
#: style class.
#:
#: The order of precedence for the four possible cases is the following,
#: from most to least important:
#:
#: 1. Diagram class specific, element type and class
#: 2. __GLOBAL__, element type and class
#: 3. Diagram class specific, only element type
#: 4. __GLOBAL__, only element type
CSSdef = int | str | RGB | list[RGB] | None
STYLES: dict[str, dict[str, dict[str, CSSdef]]] = {
    "__GLOBAL__": {  # Global defaults
        "Box": {
            "fill": "none",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Box.Annotation": {
            "fill": None,
            "stroke": None,
        },
        "Box.Constraint": {  # DT_Contraint [sic]
            "fill": COLORS["light_yellow"],
            "stroke": COLORS["gray"],
            "text_fill": COLORS["black"],
        },
        "Box.Note": {
            "fill": RGB(255, 255, 203),
            "stroke": RGB(255, 204, 102),
            "text_fill": RGB(0, 0, 0),
        },
        "Box.PP": {
            "fill": COLORS["_CAP_PhysicalPort_Yellow"],
            "stroke": COLORS["_CAP_Class_Border_Brown"],
        },
        "Box.RepresentationLink": {
            "fill": RGB(255, 255, 203),
            "stroke": RGB(255, 204, 102),
            "text_fill": RGB(0, 0, 0),
        },
        "Box.Requirement": {  # ReqVP_Requirement
            "fill": COLORS["light_purple"],
            "stroke": COLORS["dark_purple"],
            "text_fill": COLORS["black"],
        },
        "Box.Text": {
            "stroke": "transparent",
        },
        "Edge": {
            "stroke-width": 1,
            "fill": None,
            "stroke": COLORS["black"],
        },
        "Edge.Connector": {
            "stroke": RGB(176, 176, 176),
            "stroke-dasharray": "1",
        },
        "Edge.Constraint": {
            "stroke": COLORS["black"],
            "stroke-dasharray": "1 3",
            "marker-end": "FineArrowMark",
            "stroke-linecap": "round",
        },
        "Edge.Note": {
            "stroke": COLORS["black"],
            "stroke-dasharray": "1 3",
        },
        "Edge.PhysicalLink": {
            "stroke": COLORS["red"],
            "stroke-width": 2,
            "text_fill": COLORS["red"],
        },
        "Edge.RequirementRelation": {  # ReqVP_IncomingRelation
            "stroke": COLORS["dark_purple"],
            "stroke-width": 2,
            "marker-end": "FineArrowMark",
            "stroke-dasharray": "5",
            "text_fill": COLORS["dark_purple"],
        },
    },
    "Class Diagram Blank": {
        "Box.Class": {  # DT_Class
            "fill": [COLORS["white"], COLORS["_CAP_Class_Brown"]],
            "rx": "10px",
            "ry": "10px",
            "stroke": COLORS["_CAP_Class_Border_Brown"],
            "text_fill": COLORS["black"],
        },
        "Box.PrimitiveClass": {
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.DataPkg": {  # DT_DataPkg
            "fill": [
                COLORS["white"],
                COLORS["_CAP_InterfaceDataPackage_LightGray"],
            ],
            "stroke": COLORS["dark_gray"],
            "text_fill": COLORS["black"],
        },
        "Box.Enumeration": {  # DT_DataType
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.BooleanType": {
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.NumericType": {
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.PhysicalQuantity": {
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.StringType": {
            "fill": COLORS["_CAP_Class_Brown"],
            "stroke": COLORS["_CAP_Datatype_Border_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.ExchangeItem": {  # DT_ExchangeItem
            "fill": COLORS["_CAP_ExchangeItem_Pinkkish"],
            "stroke": COLORS["_CAP_Interface_Border_Reddish"],
            "text_fill": COLORS["black"],
        },
        "Edge.Association": {
            "stroke": COLORS["_CAP_Association_Color"],
            "marker-end": "FineArrowMark",
        },
        "Edge.Aggregation": {
            "stroke": COLORS["_CAP_Association_Color"],
            "marker-start": "DiamondMark",
            "marker-end": "FineArrowMark",
        },
        "Edge.Composition": {
            "stroke": COLORS["_CAP_Association_Color"],
            "marker-start": "FilledDiamondMark",
            "marker-end": "FineArrowMark",
        },
        "Edge.ExchangeItemElement": {  # DT_ExchangeItemElement
            "stroke": COLORS["black"],
            "stroke-dasharray": "5",
            "text_fill": COLORS["black"],
            "marker-start": "FilledDiamondMark",
            "marker-end": "FineArrowMark",
        },
        "Edge.Generalization": {
            "stroke": COLORS["black"],
            "marker-end": "GeneralizationMark",
        },
    },
    "Contextual Capability": {
        "Edge.AbstractCapabilityExtend": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.AbstractCapabilityGeneralization": {
            "marker-end": "GeneralizationMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.AbstractCapabilityInclude": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.CapabilityExploitation": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.CapabilityInvolvement": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.MissionInvolvement": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
    },
    "Error": {},
    "Functional Chain Description": {
        "Box.Function": {
            "fill": COLORS["_CAP_xAB_Function_Green"],
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.FunctionalExchange": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.SequenceLink": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-dasharray": "5",
        },
    },
    "Logical Architecture Blank": {  # (from logical.odesign)
        **{
            key: {"fill": COLORS["white"], "stroke": COLORS["black"]}
            for key in ["Box.CP_IN", "Box.CP_OUT", "Box.CP_INOUT"]
        },
        "Box.CP_UNSET": {
            "fill": [COLORS["red"], COLORS["white"]],
        },
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.LogicalActor": {  # Logical Actors
            "fill": [COLORS["_CAP_Actor_Blue_min"], COLORS["_CAP_Actor_Blue"]],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["_CAP_Actor_Blue_label"],
        },
        "Box.LogicalComponent": {  # LAB Logical Component
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "text_fill": COLORS["_CAP_Component_Label_Blue"],
        },
        "Box.LogicalHumanActor": {  # LAB Logical Human Actor
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "text_fill": COLORS["_CAP_Component_Label_Blue"],
        },
        "Box.LogicalHumanComponent": {  # LAB Logical Human Component
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "text_fill": COLORS["_CAP_Component_Label_Blue"],
        },
        "Box.LogicalFunction": {  # LAB Logical Function
            "fill": COLORS["_CAP_xAB_Function_Green"],
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "text_fill": COLORS["_CAP_xAB_Function_Label_Green"],
        },
        "Edge.FunctionalExchange": {  # LAB DataFlow between Function
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.ComponentExchange": {  # LAB DataFlow between Logical Components
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_Component_Border_Blue"],
        },
        "Edge.FIPAllocation": {  # LAB PortAllocation
            "stroke": COLORS["dark_orange"],
            "stroke-width": 2,
            "stroke-dasharray": "5",
        },
        "Edge.FOPAllocation": {
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "stroke-dasharray": "5",
        },
    },
    "Logical Data Flow Blank": {
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.LogicalFunction": {  # LDFB_Function
            "fill": [
                COLORS["_CAP_xDFB_Function_Green_min"],
                COLORS["_CAP_xDFB_Function_Green"],
            ],
            "rx": "10px",
            "ry": "10px",
            "stroke": COLORS["_CAP_xDFB_Function_Border_Green"],
            "text_fill": COLORS["_CAP_xDFB_Function_Green_Label"],
        },
        "Edge.FunctionalExchange": {  # LDFB_Exchange
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
    },
    "Missions Capabilities Blank": {
        "Box.SystemComponent": {
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "text_fill": COLORS["black"],
        },
        "Box.SystemActor": {
            "fill": [COLORS["_CAP_Actor_Blue_min"], COLORS["_CAP_Actor_Blue"]],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["black"],
        },
        "Box.SystemHumanActor": {
            "fill": [COLORS["_CAP_Actor_Blue_min"], COLORS["_CAP_Actor_Blue"]],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["black"],
        },
        "Edge.AbstractCapabilityExtend": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.AbstractCapabilityGeneralization": {
            "marker-end": "GeneralizationMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.AbstractCapabilityInclude": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.CapabilityExploitation": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.CapabilityInvolvement": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
        "Edge.MissionInvolvement": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-width": 1,
        },
    },
    "Mode State Machine": {  # (from common.odesign)
        "Box.ChoicePseudoState": {
            "fill": COLORS["_CAP_ChoicePseudoState_Color"],
            "stroke": COLORS["_CAP_ChoicePseudoState_Border_Gray"],
        },
        "Box.ForkPseudoState": {
            "fill": COLORS["black"],
        },
        "Box.JoinPseudoState": {
            "fill": COLORS["black"],
        },
        "Box.Mode": {
            "fill": COLORS["_CAP_MSM_Mode_Gray_min"],
            "stroke": COLORS["dark_gray"],
        },
        "Box.ModeRegion": {
            "fill": [
                COLORS["_CAP_MSM_Mode_Gray_min"],
                COLORS["_CAP_MSM_Mode_Gray"],
            ],
            "stroke": COLORS["dark_gray"],
        },
        "Box.State": {
            "fill": COLORS["_CAP_MSM_State_Gray_min"],
            "stroke": COLORS["dark_gray"],
        },
        "Box.StateRegion": {
            "fill": [
                COLORS["_CAP_MSM_State_Gray_min"],
                COLORS["_CAP_MSM_State_Gray"],
            ],
            "stroke": COLORS["dark_gray"],
        },
        "Edge.StateTransition": {
            "marker-end": "FineArrowMark",
        },
    },
    "Operational Capabilities Blank": {
        "Box.Entity": {
            "fill": [
                COLORS["_CAP_Entity_Gray_min"],
                COLORS["_CAP_Entity_Gray"],
            ],
            "stroke": COLORS["_CAP_Entity_Gray_border"],
            "text_fill": COLORS["_CAP_Entity_Gray_label"],
        },
        "Box.OperationalActor": {
            "fill": [
                COLORS["_CAP_Entity_Gray_min"],
                COLORS["_CAP_Entity_Gray"],
            ],
            "stroke": COLORS["_CAP_Entity_Gray_border"],
            "text_fill": COLORS["_CAP_Entity_Gray_label"],
        },
        "Edge.AbstractCapabilityExtend": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
        },
        "Edge.AbstractCapabilityGeneralization": {
            "marker-end": "GeneralizationMark",
            "stroke": COLORS["black"],
        },
        "Edge.AbstractCapabilityInclude": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
        },
        "Edge.CommunicationMean": {
            "marker-end": "ArrowMark",
            "stroke": COLORS["gray"],
        },
        "Edge.Entity": {},
        "Edge.EntityOperationalCapabilityInvolvement": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
        },
        "Edge.OperationalActor": {},
    },
    "Operational Entity Blank": {  # "Operational Architecture Blank" in GUI
        "Box.Entity": {
            "fill": [
                COLORS["_CAP_Entity_Gray_min"],
                COLORS["_CAP_Entity_Gray"],
            ],
            "stroke": COLORS["_CAP_Entity_Gray_border"],
            "text_fill": COLORS["_CAP_Entity_Gray_label"],
        },
        "Box.OperationalActivity": {
            "fill": COLORS["_CAP_Activity_Orange"],
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
            "text_fill": COLORS["_CAP_xAB_Activity_Label_Orange"],
        },
        "Box.OperationalActor": {
            "fill": [
                COLORS["_CAP_Entity_Gray_min"],
                COLORS["_CAP_Entity_Gray"],
            ],
            "stroke": COLORS["_CAP_Entity_Gray_border"],
            "text_fill": COLORS["_CAP_Entity_Gray_label"],
        },
        "Box.Role": {
            "fill": [COLORS["white"], COLORS["_CAP_OperationalRole_Purple"]],
            "stroke": COLORS["dark_purple"],
            "text_fill": COLORS["black"],
        },
        "Edge.CommunicationMean": {
            "marker-end": "ArrowMark",
            "stroke": COLORS["dark_gray"],
        },
        "Edge.OperationalExchange": {
            "marker-end": "FilledArrowMark",
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
        },
    },
    "Operational Entity Breakdown": {
        "Box.Entity": {
            "fill": COLORS["_CAP_Entity_Gray"],
            "stroke": COLORS["_CAP_Entity_Gray_border"],
            "text_fill": COLORS["_CAP_Entity_Gray_label"],
        },
        "Edge.Entity": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["gray"],
        },
        "Edge.OperationalActor": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["gray"],
        },
        "Edge.OperationalExchange": {
            "marker-end": "ArrowMark",
            "stroke-width": 2,
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
        },
    },
    "Operational Process Description": {
        "Box.OperationalActivity": {
            "fill": COLORS["_CAP_Activity_Orange"],
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
        },
        "Edge.OperationalExchange": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
        },
        "Edge.SequenceLink": {
            "marker-end": "FineArrowMark",
            "stroke": COLORS["black"],
            "stroke-dasharray": "5",
        },
    },
    "Operational Activity Interaction Blank": {
        "Box.OperationalActivity": {
            "fill": COLORS["_CAP_Activity_Orange"],
            "rx": "10px",
            "ry": "10px",
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
            "text_fill": COLORS["_CAP_xAB_Activity_Label_Orange"],
        },
        "Box.OperationalProcess": {
            "stroke": COLORS["black"],
            "text_fill": COLORS["black"],
        },
        "Edge.OperationalExchange": {
            "marker-end": "ArrowMark",
            "stroke-width": 2,
            "stroke": COLORS["_CAP_Activity_Border_Orange"],
        },
    },
    "Physical Architecture Blank": {
        **{
            key: {"fill": COLORS["white"], "stroke": COLORS["black"]}
            for key in ["Box.CP_IN", "Box.CP_OUT", "Box.CP_INOUT"]
        },
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.PhysicalComponent": {
            "fill": [
                COLORS["_CAP_Unset_Gray_min"],
                COLORS["_CAP_Unset_Gray"],
            ],
            "stroke": COLORS["_CAP_Lifeline_Gray"],
            "text_fill": COLORS["black"],
        },
        "Box.PhysicalNodeComponent": {
            "fill": [
                COLORS["_CAP_Node_Yellow_min"],
                COLORS["_CAP_Node_Yellow"],
            ],
            "stroke": COLORS["_CAP_Node_Yellow_Border"],
            "text_fill": COLORS["_CAP_Node_Yellow_Label"],
        },
        "Box.PhysicalNodeActor": {
            "fill": [
                COLORS["_CAP_Actor_Blue_min"],
                COLORS["_CAP_Actor_Blue"],
            ],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["_CAP_Actor_Blue_label"],
        },
        "Box.PhysicalBehaviorComponent": {
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "rx": "10px",
            "ry": "10px",
            "text_fill": COLORS["black"],
            "text_font-style": "italic",
        },
        "Box.PhysicalFunction": {
            "fill": COLORS["_CAP_xAB_Function_Green"],
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.ComponentExchange": {
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_Component_Border_Blue"],
        },
        "Edge.FunctionalExchange": {
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
    },
    "Physical Data Flow Blank": {
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.PhysicalFunction": {
            "fill": COLORS["_CAP_xAB_Function_Green"],
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.FunctionalExchange": {
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
    },
    "System Architecture Blank": {
        **{
            key: {"fill": COLORS["white"], "stroke": COLORS["black"]}
            for key in ["Box.CP_IN", "Box.CP_OUT", "Box.CP_INOUT"]
        },
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.SystemActor": {
            "fill": [COLORS["_CAP_Actor_Blue_min"], COLORS["_CAP_Actor_Blue"]],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["_CAP_Actor_Blue_label"],
        },
        "Box.SystemComponent": {
            "fill": [
                COLORS["_CAP_Component_Blue_min"],
                COLORS["_CAP_Component_Blue"],
            ],
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "text_fill": COLORS["black"],
        },
        "Box.SystemHumanActor": {
            "fill": [COLORS["_CAP_Actor_Blue_min"], COLORS["_CAP_Actor_Blue"]],
            "stroke": COLORS["_CAP_Actor_Border_Blue"],
            "text_fill": COLORS["_CAP_Actor_Blue_label"],
        },
        "Box.SystemFunction": {
            "fill": COLORS["_CAP_xAB_Function_Green"],
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.ComponentExchange": {
            "stroke": COLORS["_CAP_Component_Border_Blue"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_Component_Border_Blue"],
        },
        "Edge.FunctionalExchange": {
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
        "Edge.FIPAllocation": {
            "stroke": COLORS["dark_orange"],
            "stroke-width": 2,
            "stroke-dasharray": "5",
        },
        "Edge.FOPAllocation": {
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "stroke-dasharray": "5",
        },
    },
    "System Data Flow Blank": {
        "Box.FIP": {
            "fill": COLORS["dark_orange"],
            "stroke-width": 0,
        },
        "Box.FOP": {
            "fill": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 0,
        },
        "Box.SystemFunction": {  # SDFB_Function
            "fill": [
                COLORS["_CAP_xDFB_Function_Green_min"],
                COLORS["_CAP_xDFB_Function_Green"],
            ],
            "rx": "10px",
            "ry": "10px",
            "stroke": COLORS["_CAP_xDFB_Function_Border_Green"],
            "text_fill": COLORS["_CAP_xDFB_Function_Green_Label"],
        },
        "Edge.FunctionalExchange": {  # SDFB_Exchange
            "stroke": COLORS["_CAP_xAB_Function_Border_Green"],
            "stroke-width": 2,
            "text_fill": COLORS["_CAP_xAB_Function_Border_Green"],
        },
    },
}
