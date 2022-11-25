# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import collections.abc as cabc
import typing as t

from svgwrite import container, gradients, path, shapes, text

from . import decorations
from . import style as style_

Gradient = t.Union[gradients.LinearGradient, gradients.RadialGradient]


@decorations.deco_factories
def port_symbol(id_: str = "PortSymbol") -> container.Symbol:
    port = _make_port_box(id_)
    port.add(path.Path(d="M5 1L1 9h8z", fill="#fff"))
    return port


@decorations.deco_factories
def component_port_symbol(
    id_: str = "ComponentPortSymbol",
) -> container.Symbol:
    port = _make_port_box(id_)
    port.add(path.Path(d="M 2,2 5,7 8,2"))
    return port


def _make_port_box(id_: str) -> container.Symbol:
    port = container.Symbol(id=id_, viewBox="0 0 10 10")
    port.add(path.Path(d="M0 0h10v10H0z"))
    return port


def _make_edge_symbol(
    id_: str, grad_colors: tuple[str, str], middle_color: str
) -> container.Symbol:
    """Return svg symbol for edges."""
    symb = container.Symbol(id=id_, viewBox="0 0 40 30")
    grad_id = id_ + "-gradient"
    symb.add(
        _make_lgradient(
            grad_id,
            stop_colors=grad_colors,
            start=(0, 0),
            end=(1, 1),
        )
    )
    symb.add(
        _make_lgradient(
            grad_id + "reverse",
            stop_colors=grad_colors[::-1],
            start=(0, 0),
            end=(1, 1),
        )
    )

    grp = container.Group(style="stroke:#000;stroke-width:2;")
    grp.add(
        path.Path(
            d="M 36.190065,5.0377724 V 24.962228 H 26.17482 V 5.0377724 Z",
            style=f'fill: url(#{grad_id + "reverse"})',
        )
    )
    grp.add(
        path.Path(
            d=(
                "m 14.372107,10 h 12.622435 c 0.926189,0.585267"
                " 1.836022,1.274509 2.268178,5 -0.208657,2.812473"
                " -0.954601,4.503809 -2.273297,5 H 14.296948"
            ),
            style=f"fill: {middle_color}",
        )
    )
    grp.add(
        path.Path(
            d=(
                "M 3.9464908,5.0048246 V 24.995175 H 10.87518 C"
                " 12.433713,24.159139 15.158267,20.291241 15.313795,15"
                " 15.498614,11.583142 14.059659,6.6240913 10.87518,5.0048246 c"
                " -2.2179509,0 -4.5908341,0 -6.9286892,0 z"
            ),
            style=f"fill: url(#{grad_id})",
        )
    )
    symb.add(grp)
    return symb


@decorations.deco_factories
def functional_exchange_symbol(
    id_: str = "FunctionalExchangeSymbol",
) -> container.Symbol:
    return _make_edge_symbol(
        id_, grad_colors=("#4F7C45", "#BCDDB4"), middle_color="#61c34c"
    )


@decorations.deco_factories
def component_exchange_symbol(
    id_: str = "ComponentExchangeSymbol",
) -> container.Symbol:
    return _make_edge_symbol(
        id_, grad_colors=("#8FA5B6", "#E0E9F3"), middle_color="#A3BCD0"
    )


@decorations.deco_factories
def physical_link_symbol(id_: str = "PhysicalLinkSymbol") -> container.Symbol:
    return _make_edge_symbol(
        id_, grad_colors=("#DFDF00", "#E8E809"), middle_color="#F60A0A"
    )


@decorations.deco_factories
def operational_exchange_symbol(
    id_: str = "OperationalExchangeSymbol",
) -> container.Symbol:
    return _make_edge_symbol(
        id_, grad_colors=("#DF943C", "#FFF1E0"), middle_color="#EF8D1C"
    )


def _make_lgradient(
    id_,
    *,
    start=(0, 0),
    end=(0, 1),
    translate=None,
    stop_colors=("white", "black"),
    stop_opacity=(1, 1),
    offsets=None,
    **kw,
) -> Gradient:
    if len(start) != 2 or len(end) != 2:
        raise ValueError(
            "Exactly two values each for start and end are needed"
        )
    if translate is not None and len(translate) != 2:
        raise ValueError("Need two values for translation")

    if offsets is None:
        # Uniformly distribute offsets between 0..1
        offsets = [i / (len(stop_colors) - 1) for i in range(len(stop_colors))]
    elif len(stop_colors) != len(offsets):
        raise ValueError("Lengths of stop_colors and offsets differ")

    if translate:
        transformations = _get_transformation(translate)
        kw["gradientTransform"] = f"translate({transformations})"

    grad = gradients.LinearGradient(id_=id_, start=start, end=end, **kw)
    for offset, stop_col, stop_op in zip(offsets, stop_colors, stop_opacity):
        grad.add_stop_color(offset=offset, color=stop_col, opacity=stop_op)
    return grad


def _get_transformation(numbers: cabc.Iterable[int | float]) -> str:
    return " ".join(map(str, numbers))


def _make_rgradient(
    id_,
    *,
    center=(0, 0),
    r=1,
    focal=(0, 0),
    transform=None,
    stop_colors=("white", "black"),
    offsets=("0", "1"),
    **kw,
) -> Gradient:
    if transform is not None:
        transformations = _get_transformation(transform)
        kw["gradientTransform"] = f"matrix({transformations})"

    grad = gradients.RadialGradient(
        id_=id_,
        center=center,
        r=r,
        focal=focal,
        gradientUnits="userSpaceOnUse",
        **kw,
    )
    for offset, stop_color in zip(offsets, stop_colors):
        grad.add_stop_color(offset=offset, color=stop_color)
    return grad


def _make_marker(
    ref_pts: tuple[float, float],
    size: tuple[float, float],
    *,
    id_: str,
    d: str,
    style: style_.Styling,
    **kwargs: t.Any,
) -> container.Marker:
    marker = container.Marker(
        insert=ref_pts,
        size=size,
        id_=id_,
        orient="auto",
        markerUnits="userSpaceOnUse",
    )
    style._marker = True
    marker.add(path.Path(d=d, style=str(style), **kwargs))
    return marker


def _make_ls_symbol(id_: str) -> container.Symbol:
    symb = container.Symbol(
        id=id_, viewBox="0 0 79 79", style="stroke: #000; stroke-width: 2;"
    )
    symb.add(_make_lgradient("ls-blue", stop_colors=("#c3e4ff", "#98b0dd")))
    symb.add(
        path.Path(
            d="M18 237h46v43H18z",
            transform="translate(0 -218)",
            style="fill: url(#ls-blue)",
        )
    )
    symb.add(
        path.Path(
            d="M12 247h11v8H12z",
            transform="translate(0 -218)",
            style="fill: url(#ls-blue)",
        )
    )
    symb.add(
        path.Path(
            d="M12 261h11v8H12z",
            transform="translate(0 -218)",
            style="fill: url(#ls-blue)",
        )
    )
    return symb


@decorations.deco_factories
def entity_symbol(id_: str = "EntitySymbol") -> container.Symbol:
    symb = _make_ls_symbol(id_=id_)
    symb.add(
        path.Path(
            d=(
                "m 41.658466,55.581913 q 0,1.062616 -0.693953,1.734883"
                " -0.672267,0.672267 -1.734883,0.672267 h -9.498483 q"
                " -1.062615,0 -1.734883,-0.672267 -0.672267,-0.672267"
                " -0.672267,-1.734883 V 26.457569 q 0,-1.062615"
                " 0.672267,-1.734882 0.672268,-0.672267 1.734883,-0.672267 h"
                " 9.498483 q 1.062616,0 1.734883,0.672267 0.693953,0.672267"
                " 0.693953,1.734882 z M 38.644107,55.321681 V 26.717802 h"
                " -8.305751 v 28.603879 z"
            ),
            style="fill:black;",
        )
    )
    symb.add(
        path.Path(
            d=(
                "M 58.248283,57.989063 H 47.101662 V 24.05042 h 11.016505 v"
                " 2.667382 H 50.11602 v 12.664644 h 5.091614 l"
                " 0.09145,2.616665 -5.183068,0.09409 v 13.228481 h 8.132263 z"
            ),
            style="fill:black;",
        )
    )
    return symb


@decorations.deco_factories
def logical_component_symbol(
    id_: str = "LogicalComponentSymbol",
) -> container.Symbol:
    symb = _make_ls_symbol(id_=id_)
    letter = container.Group(transform="scale(0.90705135,1.1024734)")
    letter.add(
        path.Path(
            d=(
                "m 37.427456,20.821353 h 4.221475 V 50.90971 H 37.427456 Z M"
                " 39.538194,46.89517 H 56.75519 v 4.01454 H 39.538194 Z"
            ),
            style="fill: #000;",
        )
    )
    symb.add(letter)
    return symb


@decorations.deco_factories
def logical_human_actor_symbol(
    id_: str = "LogicalHumanActorSymbol",
) -> container.Symbol:
    symb = container.Symbol(
        id=id_, viewBox="0 0 79 79", style="stroke: #000; stroke-width: 2;"
    )
    symb.add(
        container.Use(
            href="#StickFigureSymbol",
            transform=(
                "matrix(0.81762456,0,0,0.81762456,-2.5207584,0.47091696)"
            ),
        )
    )
    return symb


@decorations.deco_factories
def stick_figure_symbol(
    id_: str = "StickFigureSymbol",
    transform: tuple[float, ...] | None = None,
    **kw,
) -> container.Symbol:
    """Generate StickFigure svg symbol."""
    if transform is not None:
        transformations = _get_transformation(transform)
        kw["transform"] = f"matrix({transformations})"

    symb = container.Symbol(
        id=id_,
        viewBox="362.861 210.892 75 75",
        style="stroke: #000; stroke-width: 2;",
        **kw,
    )
    grp = container.Group(
        transform="matrix(1.0611338,0,0,1.0611338,-24.47665,-12.241673)",
        style="stroke-width: 2.4944; stroke: #000;",
    )
    grp.add(
        shapes.Line(
            (400.362, 232.586), (400.362, 257.534), style="fill: none;"
        )
    )
    grp.add(
        shapes.Line(
            (400.83401, 254.299), (388.423, 275.009), style="fill: none;"
        )
    )
    grp.add(
        shapes.Line(
            (400.25201, 254.46001), (413.97, 274.987), style="fill: none;"
        )
    )
    grp.add(
        shapes.Line(
            (385.634, 244.569), (415.703, 244.49699), style="fill: none;"
        )
    )
    grp.add(
        _make_rgradient(
            "head",
            center=(43.766102, 87.902298),
            r=4.4296999,
            transform=[1.9728, 0, 0, -2.039, 314.1896, 402.5936],
            stop_colors=("#FDFCFA", "#8B9BA7"),
            offsets=(0, 1),
        )
    )
    grp.add(
        shapes.Ellipse(
            center=(400.53201, 223.35899),
            r=(9.2180004, 8.5080004),
            style="fill:url(#head)",
        )
    )
    symb.add(grp)
    return symb


@decorations.deco_factories
def logical_actor_symbol(id_: str = "LogicalActorSymbol") -> container.Symbol:
    symb = _make_ls_symbol(id_=id_)
    letters = container.Group(
        transform="scale(0.83010896,1.2046611)", style="fill: #000;"
    )
    letters.add(  # Upper-Case L
        path.Path(
            d=(
                "m 31.063676,19.942628 h 3.754427 v 26.759494 h -3.754427 "
                "z m 1.877213,23.189107 h 15.312173 v 3.570387 H 32.940889 Z"
            ),
        )
    )
    letters.add(  # Upper-Case A
        path.Path(
            d=(
                "m 60.32612,19.942628 h 3.202306 l 9.864572,26.759494 H"
                " 69.344107 L 61.927273,25.114167 54.51044,46.702122 H"
                " 50.461548 Z M 55.007349,37.260842 H 69.08645 v 3.570387 H"
                " 55.007349 Z"
            ),
        )
    )
    symb.add(letters)
    return symb


@decorations.deco_factories
def logical_human_component_symbol(
    id_: str = "LogicalHumanComponentSymbol",
) -> container.Symbol:
    symb = _make_ls_symbol(id_=id_)
    symb.add(
        container.Use(
            href="#StickFigureSymbol",
            transform="matrix(0.62,0,0,0.62,23.82,16.51)",
        )
    )
    return symb


@decorations.deco_factories
def final_state_symbol(id_="FinalStateSymbol"):
    symb = container.Symbol(id_=id_, viewBox="-1 -1 28 28")
    symb.add(
        shapes.Ellipse(
            center=(13, 13),
            r=(13, 13),
            fill="rgb(255, 255, 255)",
            stroke="rgb(0, 0, 0)",
            stroke_width=0.5,
        )
    )
    symb.add(shapes.Ellipse(center=(13, 13), r=(9, 9), fill="rgb(0, 0, 0)"))
    return symb


@decorations.deco_factories
def initial_pseudo_state_symbol(id_="InitialPseudoStateSymbol"):
    symb = container.Symbol(id_=id_, viewBox="0 0 26.458333 26.458334")
    symb.add(
        _make_rgradient(
            id_=id_ + "_RG",
            center=(17.2, 283.23),
            r=8.5,
            focal=(17.2, 283.23),
            transform=[
                1.14887,
                1.12434,
                -0.90541,
                0.93377,
                253.31643,
                -3.725107,
            ],
        )
    )
    symb.add(
        shapes.Ellipse(
            center=(13.25, 283.77),
            r=(13.25, 13.25),
            fill=f"url(#{id_ + '_RG'})",
            transform="translate(0 -270.54165)",
        )
    )
    return symb


@decorations.deco_factories
def logical_function_symbol(
    id_: str = "LogicalFunctionSymbol",
) -> container.Symbol:
    return function_symbol(id_, label="LF")


@decorations.deco_factories
def system_function_symbol(
    id_: str = "SystemFunctionSymbol",
) -> container.Symbol:
    return function_symbol(id_, label="SF")


@decorations.deco_factories
def physical_function_symbol(
    id_: str = "PhysicalFunctionSymbol",
) -> container.Symbol:
    return function_symbol(id_, label="PF")


@decorations.deco_factories
def operational_activity_symbol(
    id_: str = "OperationalActivitySymbol",
) -> container.Symbol:
    return function_symbol(id_, ("#f4901d", "white"), "OA")


@decorations.deco_factories
def function_symbol(
    id_: str = "FunctionSymbol",
    colors: tuple[str, str] = ("#6CB35B", "#ffffff"),
    label: str = "F",
) -> container.Symbol:
    grad = _make_lgradient("green", stop_colors=colors, end=(1, 0))
    symb = _make_function_symbol(id_, gradient=grad)
    symb.add(
        text.Text(
            text=label,
            insert=(42.2, 38),
            text_anchor="middle",
            style=(
                'font-family: "Segoe UI"; font-size: 12pt; font-weight: '
                "bold; fill: black; stroke: none;"
            ),
        )
    )
    return symb


def _make_function_symbol(
    id_: str = "FunctionSymbol",
    colors: tuple[str, str] = ("#f0f8ee", "#7dc56c"),
    gradient: Gradient = None,
) -> container.Symbol:
    center = (42.2, 32)
    symb = container.Symbol(id=id_, viewBox="0 0 79 79")
    gradient = gradient or _make_rgradient(
        "b",
        center=center,
        r=22.6,
        focal=center,
        inherit="#a",
        stop_colors=colors,
        transform=[1, 0, 0, 0.7, 0, 11.3],
    )
    symb.add(gradient)
    symb.add(
        shapes.Ellipse(
            center=center,
            r=(22.5, 15.5),
            style=(
                f"fill: url(#{gradient.get_id()}); stroke: #000;"
                " stroke-width: 2;"
            ),
        )
    )
    return symb


@decorations.deco_factories
def operational_capability_symbol(id_="OperationalCapabilitySymbol"):
    symb = _brown_oval(id_)
    grp = container.Group(
        transform="matrix(0.99781353,0,0,0.74596554,0.47471941,4.4891996)"
    )
    letters = container.Group(
        transform="matrix(1.1032581,0,0,0.63735306,-10.659712,-9.548313)",
        style="fill: black; stroke: none;",
    )
    letters.add(
        path.Path(
            d=(
                "m 22.557488,35.882454 q -2.845659,0 -4.527185,2.121309"
                " -1.668591,2.12131 -1.668591,5.781862 0,3.647618"
                " 1.668591,5.768927 1.681526,2.12131 4.527185,2.12131"
                " 2.845659,0 4.501315,-2.12131 1.668591,-2.121309"
                " 1.668591,-5.768927 0,-3.660552 -1.668591,-5.781862"
                " -1.655656,-2.121309 -4.501315,-2.121309 z m 0,-2.12131 q"
                " 4.061532,0 6.493277,2.729246 2.431745,2.716311"
                " 2.431745,7.295235 0,4.56599 -2.431745,7.295236"
                " -2.431745,2.716311 -6.493277,2.716311 -4.074466,0"
                " -6.519146,-2.716311 -2.431745,-2.716311 -2.431745,-7.295236"
                " 0,-4.578924 2.431745,-7.295235 2.44468,-2.729246"
                " 6.519146,-2.729246 z"
            ),
        )
    )
    letters.add(
        path.Path(
            d=(
                "m 50.031033,35.597888 v 2.755115 q -1.319351,-1.228807"
                " -2.81979,-1.836743 -1.487504,-0.607937 -3.169029,-0.607937"
                " -3.311313,0 -5.070448,2.030766 -1.759134,2.017831"
                " -1.759134,5.846536 0,3.815771 1.759134,5.846536"
                " 1.759135,2.017831 5.070448,2.017831 1.681525,0"
                " 3.169029,-0.607936 1.500439,-0.607936 2.81979,-1.836744 v"
                " 2.729246 q -1.371091,0.931307 -2.910334,1.39696"
                " -1.526308,0.465654 -3.233703,0.465654 -4.384902,0"
                " -6.907191,-2.677507 -2.522289,-2.690441 -2.522289,-7.33404"
                " 0,-4.656533 2.522289,-7.334039 2.522289,-2.690442"
                " 6.907191,-2.690442 1.733265,0 3.259573,0.465654"
                " 1.539243,0.452718 2.884464,1.37109 z"
            ),
        )
    )
    grp.add(letters)
    symb.add(grp)
    return symb


def _control_node_symbol(id_="ControlNode"):
    symb = container.Symbol(id=id_, viewBox="-1 -1 52 52")
    symb.add(
        shapes.Circle(
            center=(25, 25),
            r=25,
            style="stroke:black;stroke-width:2px;fill: white;",
        )
    )
    return symb


@decorations.deco_factories
def and_control_node_symbol(id_="AndControlNodeSymbol"):
    symb = _control_node_symbol(id_=id_)
    letters = container.Group(
        transform="matrix(1.5022395,0,0,2.1293615,-5.360383,-20.771755)",
        style="fill:black;",
    )
    letters.add(
        path.Path(
            d=(
                "m 16.278054,24.790231 h -1.09037 l -0.754473,-2.144565 h"
                " -3.327952 l -0.754473,2.144565 H 9.3120927 L"
                " 12.112946,17.095634 H 13.4772 Z m -2.160068,-3.023062"
                " -1.348751,-3.777535 -1.353918,3.777535 z"
            )
        )
    )
    letters.add(
        path.Path(
            d=(
                "m 23.316361,24.790231 h -1.266068 l -3.648345,-6.883279 v"
                " 6.883279 h -0.956011 v -7.694597 h 1.586461 l"
                " 3.327952,6.283835 v -6.283835 h 0.956011 z"
            )
        )
    )
    letters.add(
        path.Path(
            d=(
                "m 31.863616,20.950684 q 0,1.049028 -0.459919,1.901687"
                " -0.454751,0.852658 -1.214392,1.322912 -0.527098,0.325561"
                " -1.178219,0.470254 -0.645953,0.144694 -1.705317,0.144694 h"
                " -1.943028 v -7.694597 h 1.922358 q 1.126542,0"
                " 1.787998,0.165365 0.666624,0.160196 1.126543,0.444415"
                " 0.785479,0.490925 1.224728,1.30741 0.439248,0.816485"
                " 0.439248,1.93786 z m -1.069699,-0.0155 q 0,-0.904335"
                " -0.315225,-1.52445 -0.315225,-0.620115 -0.940508,-0.976681"
                " -0.454751,-0.258382 -0.966346,-0.356566 -0.511595,-0.103353"
                " -1.224728,-0.103353 h -0.961179 v 5.937603 h 0.961179 q"
                " 0.738971,0 1.286739,-0.10852 0.552936,-0.10852"
                " 1.012855,-0.403075 0.573607,-0.366901 0.857826,-0.966346"
                " 0.289387,-0.599445 0.289387,-1.498612 z"
            )
        )
    )
    symb.add(letters)
    return symb


@decorations.deco_factories
def or_control_node_symbol(id_="OrControlNodeSymbol"):
    symb = _control_node_symbol(id_=id_)
    letters = container.Group(
        transform="matrix(2.1611566,0,0,2.4212253,-19.677936,-29.516726)",
        style="fill:black;",
    )
    letters.add(
        path.Path(
            d=(
                "m 19.169982,18.858205 q 0.470254,0.516763 0.7183,1.266068"
                " 0.253214,0.749306 0.253214,1.70015 0,0.950843"
                " -0.258382,1.705316 -0.253214,0.749306 -0.713132,1.250566"
                " -0.475422,0.52193 -1.126543,0.785479 -0.645953,0.263549"
                " -1.477941,0.263549 -0.811318,0 -1.477941,-0.268716"
                " -0.661457,-0.268717 -1.126543,-0.780312 -0.465086,-0.511595"
                " -0.7183,-1.255733 -0.248046,-0.744138 -0.248046,-1.700149"
                " 0,-0.940508 0.248046,-1.684647 0.248046,-0.749306"
                " 0.723468,-1.281571 0.454751,-0.506428 1.126542,-0.775144"
                " 0.676959,-0.268717 1.472774,-0.268717 0.82682,0"
                " 1.483109,0.273885 0.661456,0.268716 1.121375,0.769976 z m"
                " -0.09302,2.966218 q 0,-1.498612 -0.671791,-2.30993"
                " -0.671792,-0.816485 -1.834508,-0.816485 -1.173051,0"
                " -1.844842,0.816485 -0.666624,0.811318 -0.666624,2.30993"
                " 0,1.514114 0.682127,2.320264 0.682126,0.800982"
                " 1.829339,0.800982 1.147214,0 1.824173,-0.800982"
                " 0.682126,-0.80615 0.682126,-2.320264 z"
            )
        )
    )
    letters.add(
        path.Path(
            d=(
                "m 28.130647,25.669137 h -1.32808 l -2.573479,-3.059235 h"
                " -1.441767 v 3.059235 H 21.76413 v -7.694596 h 2.154901 q"
                " 0.697629,0 1.162716,0.09302 0.465086,0.08785"
                " 0.837155,0.320393 0.418578,0.263549 0.651121,0.666624"
                " 0.237711,0.397907 0.237711,1.012855 0,0.831987"
                " -0.418578,1.395259 -0.418577,0.558103 -1.15238,0.842323 z m"
                " -2.392612,-5.529361 q 0,-0.330728 -0.118855,-0.583941"
                " -0.113688,-0.258382 -0.382404,-0.434081 -0.222208,-0.149861"
                " -0.527098,-0.206705 -0.30489,-0.06201 -0.7183,-0.06201 h"
                " -1.204057 v 2.904207 h 1.033525 q 0.485757,0"
                " 0.847491,-0.08268 0.361734,-0.08785 0.614947,-0.320392"
                " 0.232544,-0.217041 0.341064,-0.496093 0.113687,-0.284219"
                " 0.113687,-0.7183 z"
            )
        )
    )
    symb.add(letters)
    return symb


@decorations.deco_factories
def iterate_control_node_symbol(id_="IterateControlNodeSymbol"):
    symb = _control_node_symbol(id_=id_)
    letters = container.Group(
        transform="scale(1.0393759,0.9621158)", style="fill:black;"
    )
    letters.add(
        path.Path(
            d="M 15.458523,38.056835 H 12.340129 V 11.439119 h 3.118394 z"
        )
    )
    letters.add(
        path.Path(
            d=(
                "M 38.178247,14.260523 H 30.493634 V 38.056835 H 27.375241 V "
                "14.260523 H 19.70919 v -2.821404 h 18.469057 z"
            )
        )
    )
    symb.add(letters)
    return symb


@decorations.deco_factories
def operational_actor_box_symbol(id_="OperationalActorBoxSymbol"):
    symb = container.Symbol(
        id=id_,
        viewBox="-10 -10 79 79",
        style="stroke: #000000; stroke-width: 2;",
    )
    symb.add(shapes.Circle(center=(6.8, 7.75), r=5, style="fill:none;"))
    symb.add(
        path.Path(
            d=(
                "m 6.723408,12.783569 0.1864956,13.042426 -6.52734189,6.042591"
                " v 0 l 6.52734189,-6.042591 6.2009764,5.95285"
                " -6.2942242,-6.012678 -0.092832,-6.050988 6.2026382,0.033"
                " -12.3973765,0.02992"
            ),
            style="fill: none;",
        )
    )
    return symb


@decorations.deco_factories
def operational_actor_symbol(id_="OperationalActorSymbol"):
    symb = container.Symbol(
        id=id_, viewBox="0 0 50 50", style="stroke: #000000; stroke-width: 2;"
    )
    center = (25.8, 9.965)
    symb.add(
        _make_rgradient(
            "gray",
            center=center,
            focal=center,
            r=8.06,
            stop_colors=("white", "#9aaab9"),
        )
    )
    symb.add(shapes.Circle(center=center, r=7.445, style="fill:url(#gray);"))
    symb.add(
        path.Path(
            d=(
                "m 25.643608,17.4341 0.276914,19.3657 -9.691951,8.97218 v 0 l"
                " 9.691951,-8.97218 9.207354,8.838931 -9.345812,-8.927765 "
                "-0.137836,-8.984648 9.209822,0.04899 -18.407914,0.04443"
            ),
            style="fill: none;",
        )
    )
    return symb


@decorations.deco_factories
def mode_symbol(id_="ModeSymbol"):
    symb = container.Symbol(id=id_, viewBox="-1 -1 4.6458 4.6458")
    symb.add(
        _make_lgradient(
            "mode-grey",
            start=(1, 0),
            end=(0, 1),
            stop_colors=("black", "white"),
            stop_opacity=(0.45, 0),
        )
    )
    symb.add(
        shapes.Rect(
            insert=(0, 0),
            size=(2.6327, 2.6327),
            ry=0.25474,
            style="fill: url(#mode-grey); stroke: #000; stroke-width: .005",
        )
    )
    symb.add(
        text.Text(
            "M",
            insert=(0, 2.6458),
            transform="scale(1.3907 .71906)",
            style=(
                "fill: #000000; font-size: 2.4821px; "
                "stroke-width: .062; line-height:1.25;"
            ),
        )
    )
    return symb


@decorations.deco_factories
def state_symbol(id_="StateSymbol"):
    symb = container.Symbol(id=id_, viewBox="-1 -1 4.6458 4.6458")
    symb.add(
        _make_lgradient(
            "state-grey",
            start=(1, 0),
            end=(0, 1),
            stop_colors=("black", "white"),
            stop_opacity=(0.45, 0),
        )
    )
    symb.add(
        shapes.Rect(
            insert=(0, 0),
            size=(2.6327, 2.6327),
            ry=0.25474,
            style="fill: url(#state-grey); stroke: #000; stroke-width: .005",
        )
    )
    symb.add(
        text.Text(
            "S",
            insert=(0, 2.6458),
            transform="scale(1.2578 .79502)",
            style=(
                "fill:#000000;font-size:3.274px;"
                "stroke-width:.082;line-height:1.25;"
            ),
        )
    )
    return symb


@decorations.deco_factories
def terminate_pseudo_state_symbol(
    id_="TerminatePseudoStateSymbol", stroke="black", stroke_width=0.165
):
    symb = container.Symbol(id=id_, viewBox="0 0 2.6458 2.6458")
    symb.add(
        path.Path(
            d="M 0,0 2.6458333,2.6458333 M 0,2.6458333 2.6458333,0",
            style=(
                f"fill: none; stroke: {stroke}; stroke-width: {stroke_width};"
            ),
        )
    )
    return symb


@decorations.deco_factories
def requirement_symbol(id_: str = "RequirementSymbol") -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="0 0 50 50", style="stroke: none;")
    symb.add(
        path.Path(  # Circle
            d=(
                "M 12.806813,6.5702324 A 6.244379,5.8113241 0 0 1"
                " 6.5624342,12.381557 6.244379,5.8113241 0 0 1"
                " 0.31805515,6.5702324 6.244379,5.8113241 0 0 1"
                " 6.5624342,0.75890827 6.244379,5.8113241 0 0 1"
                " 12.806813,6.5702324 Z"
            ),
            style="fill: #431964",
        )
    )
    symb.add(
        path.Path(  # R
            d=(
                "m 4.3228658,5.8752475 h 2.9514721 q 0.2945581,0"
                " 0.5184223,-0.1413879 Q 8.0225155,5.5865806"
                " 8.1462299,5.3214783 8.2699443,5.056376 8.2758355,4.7029063 v"
                " 0 q 0,-0.3475786 -0.1237144,-0.6126808 Q 8.0284067,3.8251232"
                " 7.7986513,3.6837353 7.5747872,3.5364562 7.2743379,3.5364562"
                " H 4.3228658 V 2.1873801 h 2.9927103 q 0.7246129,0"
                " 1.2724909,0.3122316 0.5478781,0.3122316 0.8483274,0.8836743"
                " 0.3063404,0.5714427 0.3063404,1.3196203 v 0 q 0,0.7540687"
                " -0.3063404,1.3255114 Q 9.1359451,6.5998605"
                " 8.5821759,6.912092 8.0342978,7.2243236 7.3155761,7.2243236 H"
                " 4.3228658 Z M 3.7396407,2.1873801 H 5.1476285 V 10.759021 H"
                " 3.7396407 Z M 6.3906636,6.9592213 7.8516718,6.6882279"
                " 10.102096,10.759021 H 8.4113322 Z"
            ),
            style="fill:#ffffff;",
        )
    )
    return symb


@decorations.deco_factories
def system_component_symbol(
    id_: str = "SystemComponentSymbol",
) -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="0 12 79 55")
    grp = container.Group(
        transform="matrix(0.25509703,0,0,0.25509703,-19.119473,-26.4767)"
    )
    box_grp = container.Group(
        transform="matrix(0.92548165,0,0,0.92249056,-32.422011,-1.2909536)",
        style="fill:#e3ebf8;stroke-width:1.33145",
    )
    box_grp.add(
        path.Path(
            d="m 160.03785,180.47519 h 280.8845 v 200.68502 h -280.8845 z",
            style="stroke:#000000;stroke-width:7;",
        )
    )
    grp.add(box_grp)
    grp.add(
        path.Path(
            d="m 81.854696,210.17533 h 66.250264 v 35.37025 H 81.854696 Z",
            style="fill:#e7efff;stroke:#000000;stroke-width:7;",
        )
    )
    grp.add(
        path.Path(
            d="m 83.588316,268.94271 h 66.250254 v 35.37024 H 83.588316 Z",
            style="fill:#e7efff;stroke:#000000;stroke-width:7;",
        )
    )

    # Black connected boxes
    params = {
        "size": (5, 5),
        "style": "fill:#000000;stroke:#000000;stroke-width:54.1038;",
    }
    grp.add(shapes.Rect(insert=(214.8075, 236.39), **params))
    grp.add(shapes.Rect(insert=(297.44, 298.36), **params))
    grp.add(shapes.Rect(insert=(297.44, 215.73), **params))
    grp.add(
        path.Path(
            d="m 219.70896,218.22099 h 79.0257 v 85.9132 h -80.34135 z",
            style="fill:none;stroke:#000000;stroke-width:4.29901px;",
        )
    )
    symb.add(grp)
    return symb


@decorations.deco_factories
def system_actor_symbol(
    id_: str = "SystemActorSymbol",
) -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="0 0 79 79")
    grp = container.Group(
        transform="matrix(1.4376083,0,0,1.3022512,-15.958775,-15.416201)"
    )
    grp.add(
        path.Path(
            d="M 17.819891,20.041161 H 65.286364 V 64.242623 H 17.819891 Z",
            style="fill:#bdf7ff; stroke:#454647;",
        ),
    )
    grp.add(
        path.Path(
            d="m 12.064948,25.832262 h 11.521155 v 6.687244 H 12.064948 Z",
            style="fill:#e3ebf8;stroke:#454647;",
        )
    )
    grp.add(
        path.Path(
            d="m 12.050427,34.529197 h 11.455007 v 6.635451 H 12.050427 Z",
            style="fill:#e3ebf8;stroke:#454647;",
        )
    )
    grp1 = container.Group(
        transform="matrix(0.83129224,0,0,0.89544642,8.0334318,11.729573)",
        style="fill: black; stroke: none;",
    )
    grp1.add(
        path.Path(
            d=(
                "m 22.506995,47.687597 v -4.602148 q 0.619881,0.563528"
                " 1.465173,1.014351 0.864077,0.450823 1.822075,0.770155"
                " 0.957998,0.300549 1.915996,0.469607 0.957999,0.169059"
                " 1.765722,0.169059 2.817642,0 4.188894,-0.939214"
                " 1.390037,-0.939214 1.390037,-2.72372 0,-0.957998"
                " -0.469607,-1.653017 -0.450823,-0.713802 -1.277331,-1.296115"
                " -0.826508,-0.582312 -1.953565,-1.108272 -1.108272,-0.544744"
                " -2.385603,-1.127057 -1.371252,-0.732587 -2.554662,-1.483958"
                " -1.183409,-0.751371 -2.06627,-1.653016 -0.864077,-0.92043"
                " -1.371252,-2.06627 -0.488392,-1.145841 -0.488392,-2.686152"
                " 0,-1.897212 0.845293,-3.287249 0.864077,-1.40882"
                " 2.254113,-2.310466 1.408821,-0.920429 3.193327,-1.352468"
                " 1.784507,-0.450822 3.64415,-0.450822 4.226462,0"
                " 6.161243,0.957998 v 4.414305 q -2.291682,-1.653016"
                " -5.898263,-1.653016 -0.995567,0 -1.991134,0.187842"
                " -0.976782,0.187843 -1.765722,0.619882 -0.770155,0.432038"
                " -1.258546,1.108272 -0.488391,0.676234 -0.488391,1.634232"
                " 0,0.901645 0.375685,1.559095 0.375686,0.65745"
                " 1.089488,1.202194 0.732587,0.544744 1.765722,1.070703"
                " 1.05192,0.507176 2.423172,1.108273 1.408821,0.732587"
                " 2.648583,1.540311 1.258547,0.807723 2.197761,1.784506"
                " 0.957998,0.976782 1.502742,2.178976 0.563528,1.18341"
                " 0.563528,2.704936 0,2.047486 -0.826508,3.456307"
                " -0.826508,1.408821 -2.235329,2.291682 -1.390037,0.882861"
                " -3.212112,1.277331 -1.822074,0.394469 -3.850776,0.394469"
                " -0.676234,0 -1.671801,-0.112705 -0.976782,-0.09392"
                " -2.009918,-0.300549 -1.033135,-0.187842 -1.953564,-0.469607"
                " -0.92043,-0.281764 -1.483958,-0.638665 z"
            )
        )
    )
    grp1.add(
        path.Path(
            d=(
                "M 66.819105,48.758301 H 61.916408 L 59.493237,41.90204 H"
                " 48.898904 l -2.32925,6.856261 H 41.685742 L"
                " 51.772899,21.821647 h 5.034186 z M 58.309827,38.25789"
                " 54.571756,27.513283 q -0.169058,-0.525959"
                " -0.356901,-1.690585 h -0.07514 q -0.169059,1.070704"
                " -0.375686,1.690585 L 50.06353,38.25789 Z"
            )
        )
    )
    grp.add(grp1)
    symb.add(grp)
    return symb


@decorations.deco_factories
def mission_symbol(id_: str = "MissionSymbol") -> container.Symbol:
    symb = _brown_oval(id_)
    symb.add(
        path.Path(
            d=(
                "M 34.809129,31.801245 31.33755,31.878525 30.470956,18.609297"
                " C 30.399426,17.514106 30.01851,15.93283 30.153514,14.341649"
                " h -0.05786 c -0.212157,0.906491 -0.400206,1.557429"
                " -0.564146,1.952814 L 23.340365,31.801245 H 20.968059 L"
                " 14.762452,16.410183 c -0.173583,-0.453245 -0.35681,-1.142757"
                " -0.549681,-2.068536 h -0.05786 c 0.07715,0.829343"
                " -0.117081,2.344989 -0.230914,4.219301 L 13.115176,31.878523"
                " 9.9328121,31.801245 11.08827,11.058028 h 4.84587 l"
                " 5.453412,13.814346 c 0.414671,1.060787 0.68469,1.851556"
                " 0.810056,2.372306 h 0.07233 c 0.356811,-1.089718"
                " 0.646116,-1.899774 0.867917,-2.430167 L 28.69252,11.058028 h"
                " 4.672287 z"
            ),
            transform="matrix(0.86023492,0,0,0.64311175,6.4177697,4.9887121)",
            style="fill: black; stroke: none;",
        )
    )
    return symb


@decorations.deco_factories
def capability_symbol(id_: str = "CapabilitySymbol") -> container.Symbol:
    symb = _brown_oval(id_)
    grp = container.Group(
        transform="matrix(0.86023492,0,0,0.64311175,6.4177697,4.9887121)"
    )
    grp.add(
        path.Path(
            d=(
                "m 25.147125,33.08327 q -2.060058,0.997225 -5.379769,0.997225"
                " -4.330058,0 -6.81,-2.545549 -2.479942,-2.545549"
                " -2.479942,-6.783757 0,-4.513757 2.781734,-7.321734"
                " 2.794856,-2.807977 7.243006,-2.807977 2.755491,0"
                " 4.644971,0.695434 v 4.080751 q -1.88948,-1.128439"
                " -4.303815,-1.128439 -2.65052,0 -4.277572,1.666416"
                " -1.627052,1.666416 -1.627052,4.513757 0,2.729249"
                " 1.535202,4.356301 1.535202,1.61393 4.133237,1.61393"
                " 2.479942,0 4.54,-1.207167 z"
            ),
            transform="scale(1.1743865,0.85150843)",
            style="fill: black; stroke: none;",
        )
    )
    symb.add(grp)
    return symb


def _brown_oval(id_: str) -> container.Symbol:
    """Create the base symbol of missions and capabilities."""
    symb = container.Symbol(id=id_, viewBox="0 0 50 37")
    symb.add(
        _make_rgradient(
            "brown_oval",
            center=(25.657873, 25.925144),
            r=20.562483,
            focal=(25.657873, 25.925144),
            transform=[
                1.471657,
                0.01303118,
                -0.03846138,
                4.3435681,
                -11.744602,
                -94.299935,
            ],
            stop_colors=("#ffffff", "#d0ab84"),
            offsets=(0, 1),
        )
    )
    symb.add(
        shapes.Ellipse(
            center=(25.017874, 18.64205),
            r=(24.564632, 17.453819),
            style="fill: url(#brown_oval); stroke: #563b18; stroke-width: 1;",
        )
    )
    return symb


@decorations.deco_factories
def system_human_actor_symbol(
    id_: str = "SystemHumanActorSymbol",
) -> container.Symbol:
    return stick_figure_symbol(id_)


@decorations.deco_factories
def class_symbol(id_: str = "ClassSymbol") -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="0 0 25 25")
    grad_id = id_ + "-gradient"
    symb.add(_make_lgradient(grad_id, stop_colors=("#cfa6a5", "#f1e2e3")))
    grp = symb.add(container.Group(style="stroke:#913734;"))
    grp.add(
        shapes.Rect(insert=(5, 17), size=(15, 3), style="fill:#eedcdd;"),
    )
    grp.add(
        shapes.Rect(insert=(5, 14), size=(15, 3), style="fill:#eedcdd;"),
    )
    grp.add(
        shapes.Rect(
            insert=(5, 4),
            size=(15, 10),
            style=f"fill:url(#{grad_id});",
        )
    )
    return symb


@decorations.deco_factories
def fine_arrow_mark(
    id_: str = "FineArrow", *, style: style_.Styling, **kw
) -> container.Marker:
    return _make_marker(
        (7, 3.5),
        (7.5, 7.5),
        id_=id_,
        d=(
            "M 0.4535,0.107 7.309,3.621 0.492,7.407 "
            "0.144,7.407 6.414,3.63 0.136,0.479 Z"
        ),
        style=style,
        **kw,
    )


@decorations.deco_factories
def arrow_mark(
    id_: str = "Arrow", *, style: style_.Styling, **kw
) -> container.Marker:
    return _make_marker(
        (5, 2.5), (5.5, 5.5), id_=id_, d="M 0,0 5,2.5 0,5", style=style, **kw
    )


def _make_diamond_marker(
    id_: str, *, style: style_.Styling, fill: str, **kw
) -> container.Marker:
    if not hasattr(style, "fill"):
        style.fill = fill
    return _make_marker(
        (0, 3),
        (11, 6),
        id_=id_,
        d="M 0,3 5,0.5 10,3 5,5.5 Z",
        style=style,
        **kw,
    )


@decorations.deco_factories
def diamond_mark(
    id_: str = "Diamond", *, style: style_.Styling, **kw
) -> container.Marker:
    return _make_diamond_marker(id_, style=style, fill="white", **kw)


@decorations.deco_factories
def filled_diamond_mark(
    id_: str = "FilledDiamond", *, style: style_.Styling, **kw
) -> container.Marker:
    return _make_diamond_marker(id_, style=style, fill="black", **kw)


@decorations.deco_factories
def generalization_mark(
    id_: str = "Generalization", *, style: style_.Styling, **kw
) -> container.Marker:
    style.fill = "#fff"
    return _make_marker(
        (7, 4),
        (7.5, 7.5),
        id_=id_,
        d="M 0.1275,7.5 7.5,3.75 0,0 Z",
        style=style,
        **kw,
    )


@decorations.deco_factories
def error_symbol(id_: str = "ErrorSymbol", **kw) -> container.Symbol:
    del kw
    return terminate_pseudo_state_symbol(
        id_=id_, stroke="red", stroke_width=0.5
    )
