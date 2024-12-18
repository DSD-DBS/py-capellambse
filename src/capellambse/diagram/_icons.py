# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

__all__ = [
    "get_icon",
    "get_svg_symbol",
    "has_icon",
]

import collections.abc as cabc
import re
import typing as t

from svgwrite import container, drawing, gradients, path, shapes, text

_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")

_FACTORIES: dict[str, _FactoryDefinition] = {}


def get_icon(styleclass: str, /, *, size: int = 16) -> str:
    """Get the icon of the given model element as standalone SVG.

    Parameters
    ----------
    styleclass
        The object's style class.
    size
        The desired size of the icon.

    Returns
    -------
    str
        The SVG data as string.

    Raises
    ------
    ValueError
        Raised if there is no icon available for this object.
    """
    dw = drawing.Drawing(
        width=size,
        height=size,
        viewBox=f"0 0 {size} {size}",
    )

    have: set[str] = set()
    missing = [styleclass]
    while missing:
        styleclass = missing.pop()
        symbol, deps = get_svg_symbol(styleclass)
        dw.defs.add(symbol)
        have.add(styleclass)
        missing.extend(set(deps) - have)

    dw.add(
        dw.use(href=f"#{styleclass}Symbol", insert=(0, 0), size=(size, size))
    )
    return dw.tostring()


def get_svg_symbol(
    styleclass: str, /
) -> tuple[container.Symbol, tuple[str, ...]]:
    """Get the icon as reusable SVG symbol.

    The resulting fragment may be referenced by a ``<use>`` element.

    Parameters
    ----------
    styleclass
        A string describing the object type.

    Returns
    -------
    Any
        The element that needs to be deployed to the resulting SVG's
        ``<defs>`` section.
    tuple[str, ...]
        Dependencies of this element, which also need to be deployed to
        the SVG's ``<defs>``. This function may be called with each of
        the provided values in turn in order to obtain the actual SVG
        fragments.

    Raises
    ------
    ValueError
        Raised if there is no icon for the given typename.
    """
    try:
        factory_def = _FACTORIES[f"{styleclass}Symbol"]
    except KeyError:
        raise ValueError(f"No icon for type {styleclass}") from None
    return (factory_def.function(), factory_def.dependencies)


def has_icon(styleclass: str, /) -> bool:
    """Determine if an icon exists for the given styleclass."""
    return f"{styleclass}Symbol" in _FACTORIES


class _FactoryDefinition(t.NamedTuple):
    function: cabc.Callable[[], container.Symbol]
    dependencies: tuple[str, ...]


def _factory(
    *, needs: str | tuple[str, ...] = ()
) -> cabc.Callable[[cabc.Callable[_P, _T]], cabc.Callable[_P, _T]]:
    if isinstance(needs, str):
        needs = (needs,)

    def decorator(func):
        symbol_name = re.sub(
            "(?:^|_)([a-z])",
            lambda m: m.group(1).capitalize(),
            func.__name__.strip("_"),
        )
        _FACTORIES[symbol_name] = _FactoryDefinition(func, needs)
        return func

    return decorator


@_factory()
def _error_symbol() -> container.Symbol:
    symb = container.Symbol(id="ErrorSymbol", viewBox="0 0 10 10")
    d = "M 0,0 10,10 M 0,10 10,0"
    symb.add(path.Path(d=d, fill="none", stroke="red", stroke_width=0.5))
    return symb


@_factory()
def _port_symbol() -> container.Symbol:
    port = _make_port_box("PortSymbol")
    port.add(path.Path(d="M5 1L1 9h8z", fill="#fff"))
    return port


@_factory()
def _component_port_symbol() -> container.Symbol:
    port = _make_port_box("ComponentPortSymbol")
    port.add(path.Path(d="M 2,2 5,7 8,2"))
    return port


@_factory()
def _functional_exchange_symbol() -> container.Symbol:
    return _make_edge_symbol(
        "FunctionalExchangeSymbol",
        grad_colors=("#4F7C45", "#BCDDB4"),
        middle_color="#61c34c",
    )


@_factory()
def _component_exchange_symbol() -> container.Symbol:
    return _make_edge_symbol(
        "ComponentExchangeSymbol",
        grad_colors=("#8FA5B6", "#E0E9F3"),
        middle_color="#A3BCD0",
    )


@_factory()
def _physical_link_symbol() -> container.Symbol:
    return _make_edge_symbol(
        "PhysicalLinkSymbol",
        grad_colors=("#DFDF00", "#E8E809"),
        middle_color="#F60A0A",
    )


@_factory()
def _operational_exchange_symbol() -> container.Symbol:
    return _make_edge_symbol(
        "OperationalExchangeSymbol",
        grad_colors=("#DF943C", "#FFF1E0"),
        middle_color="#EF8D1C",
    )


@_factory()
def _entity_symbol() -> container.Symbol:
    symb = _make_icon_frame("EntitySymbol", color="#a5b9c8")
    d = (
        "m 41.658466,55.581913 q 0,1.062616 -0.693953,1.734883"
        " -0.672267,0.672267 -1.734883,0.672267 h -9.498483 q"
        " -1.062615,0 -1.734883,-0.672267 -0.672267,-0.672267"
        " -0.672267,-1.734883 V 26.457569 q 0,-1.062615"
        " 0.672267,-1.734882 0.672268,-0.672267 1.734883,-0.672267 h"
        " 9.498483 q 1.062616,0 1.734883,0.672267 0.693953,0.672267"
        " 0.693953,1.734882 z M 38.644107,55.321681 V 26.717802 h"
        " -8.305751 v 28.603879 z"
    )
    symb.add(path.Path(d=d, fill="#000"))
    d = (
        "M 58.248283,57.989063 H 47.101662 V 24.05042 h 11.016505 v"
        " 2.667382 H 50.11602 v 12.664644 h 5.091614 l"
        " 0.09145,2.616665 -5.183068,0.09409 v 13.228481 h 8.132263 z"
    )
    symb.add(path.Path(d=d, fill="#000"))
    return symb


@_factory()
def _logical_component_symbol() -> container.Symbol:
    symb = _make_icon_frame("LogicalComponentSymbol", color="#dbe6f4")
    letter = container.Group(transform="scale(0.90705135,1.1024734)")
    d = (
        "m 37.427456,20.821353 h 4.221475 V 50.90971 H 37.427456 Z M"
        " 39.538194,46.89517 H 56.75519 v 4.01454 H 39.538194 Z"
    )
    letter.add(path.Path(d=d, fill="#000", stroke_width=0.1))
    symb.add(letter)
    return symb


@_factory(needs=("StickFigure",))
def _logical_human_actor_symbol() -> container.Symbol:
    return standalone_stick_figure_symbol("LogicalHumanActorSymbol")


@_factory()
def _stick_figure_symbol() -> container.Symbol:
    symb = container.Symbol(
        id="StickFigureSymbol",
        viewBox="362.861 210.892 75 75",
        stroke="#000",
        stroke_width=2,
    )
    grp = container.Group(
        transform="matrix(1.0611338,0,0,1.0611338,-24.47665,-12.241673)",
        stroke="#000",
        stroke_width=2.4944,
    )
    grp.add(shapes.Line((400.362, 232.586), (400.362, 257.534), fill="none"))
    grp.add(shapes.Line((400.83401, 254.299), (388.423, 275.009), fill="none"))
    grp.add(
        shapes.Line((400.25201, 254.46001), (413.97, 274.987), fill="none")
    )
    grp.add(shapes.Line((385.634, 244.569), (415.703, 244.49699), fill="none"))
    grp.add(
        shapes.Ellipse(
            center=(400.53201, 223.35899),
            r=(9.2180004, 8.5080004),
            fill="none",
        )
    )
    symb.add(grp)
    return symb


@_factory(needs="StickFigure")
def standalone_stick_figure_symbol(
    id_: str = "StandaloneStickFigureSymbol",
) -> container.Symbol:
    symb = container.Symbol(
        id=id_, viewBox="0 0 79 79", stroke="#000", stroke_width=2
    )
    use_tf = "matrix(0.81762456,0,0,0.81762456,-2.5207584,0.47091696)"
    symb.add(container.Use(href="#StickFigureSymbol", transform=use_tf))
    return symb


@_factory()
def _logical_actor_symbol() -> container.Symbol:
    symb = _make_icon_frame("LogicalActorSymbol", color="#dbe6f4")
    letters = container.Group(
        transform="scale(0.83010896,1.2046611)", fill="#000", stroke_width=0.1
    )
    # Upper-Case L
    d = (
        "m 31.063676,19.942628 h 3.754427 v 26.759494 h -3.754427 "
        "z m 1.877213,23.189107 h 15.312173 v 3.570387 H 32.940889 Z"
    )
    letters.add(path.Path(d=d))
    # Upper-Case A
    d = (
        "m 60.32612,19.942628 h 3.202306 l 9.864572,26.759494 H"
        " 69.344107 L 61.927273,25.114167 54.51044,46.702122 H"
        " 50.461548 Z M 55.007349,37.260842 H 69.08645 v 3.570387 H"
        " 55.007349 Z"
    )
    letters.add(path.Path(d=d))
    symb.add(letters)
    return symb


@_factory(needs="StickFigure")
def _logical_human_component_symbol() -> container.Symbol:
    symb = _make_icon_frame("LogicalHumanComponentSymbol", color="#dbe6f4")
    use_tf = "matrix(0.62,0,0,0.62,23.82,16.51)"
    symb.add(container.Use(href="#StickFigureSymbol", transform=use_tf))
    return symb


@_factory()
def _final_state_symbol() -> container.Symbol:
    symb = container.Symbol(id_="FinalStateSymbol", viewBox="-1 -1 28 28")
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


@_factory()
def _initial_pseudo_state_symbol() -> container.Symbol:
    symb = container.Symbol(
        id_="InitialPseudoStateSymbol", viewBox="0 0 26.458333 26.458334"
    )
    grad_id = "InitialPseudoStateSymbol_RG"
    symb.add(
        _make_rgradient(
            grad_id,
            center=(17.2, 283.23),
            r=8.5,
            focal=(17.2, 283.23),
            matrix=[1.14887, 1.12434, -0.90541, 0.93377, 253.31643, -3.725107],
        )
    )
    symb.add(
        shapes.Ellipse(
            center=(13.25, 283.77),
            r=(13.25, 13.25),
            fill=f"url(#{grad_id})",
            transform="translate(0 -270.54165)",
        )
    )
    return symb


@_factory()
def _logical_function_symbol() -> container.Symbol:
    return function_symbol(
        "LogicalFunctionSymbol",
        gradient_url="LF_green",
        label="LF",
    )


@_factory()
def _system_function_symbol() -> container.Symbol:
    return function_symbol(
        "SystemFunctionSymbol",
        gradient_url="SF_green",
        label="SF",
    )


@_factory()
def _physical_function_symbol() -> container.Symbol:
    return function_symbol(
        "PhysicalFunctionSymbol",
        gradient_url="PF_green",
        label="PF",
    )


@_factory()
def _operational_activity_symbol() -> container.Symbol:
    return function_symbol(
        "OperationalActivitySymbol",
        colors=("#f4901d", "#fff"),
        gradient_url="OA_orange",
        label="OA",
    )


@_factory()
def function_symbol(
    id_: str = "FunctionSymbol",
    gradient_url="green",
    label: str = "F",
    colors: tuple[str, str] = ("#6CB35B", "#ffffff"),
) -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="0 0 79 79")
    gradient = _make_lgradient(gradient_url, stop_colors=colors, end=(1, 0))
    symb.add(gradient)
    symb.add(
        shapes.Ellipse(
            center=(39.5, 39.5),
            r=(26, 21),
            fill=f"url(#{gradient.get_id()})",
            stroke="#000",
            stroke_width=2,
        )
    )
    symb.add(
        text.Text(
            text=label,
            insert=(40, 50),
            text_anchor="middle",
            font_family="'Open Sans','Segoe UI',Arial,sans-serif",
            font_size="25px",
            font_weight="bold",
            fill="#000",
            stroke="none",
        )
    )
    return symb


@_factory()
def _operational_capability_symbol() -> container.Symbol:
    symb = _brown_oval("OperationalCapabilitySymbol")
    grp = container.Group(
        transform="matrix(0.99781353,0,0,0.74596554,0.47471941,4.4891996)"
    )
    letters = container.Group(
        transform="matrix(1.1032581,0,0,0.63735306,-10.659712,-9.548313)",
        fill="#000",
        stroke="none",
    )
    d = (
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
    )
    letters.add(path.Path(d=d))
    d = (
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
    )
    letters.add(path.Path(d=d))
    grp.add(letters)
    symb.add(grp)
    return symb


@_factory()
def _and_control_node_symbol() -> container.Symbol:
    symb = _control_node_symbol("AndControlNodeSymbol")
    letters = container.Group(
        transform="matrix(1.5022395,0,0,2.1293615,-5.360383,-20.771755)",
        fill="#000",
    )
    d = (
        "m 16.278054,24.790231 h -1.09037 l -0.754473,-2.144565 h"
        " -3.327952 l -0.754473,2.144565 H 9.3120927 L"
        " 12.112946,17.095634 H 13.4772 Z m -2.160068,-3.023062"
        " -1.348751,-3.777535 -1.353918,3.777535 z"
    )
    letters.add(path.Path(d=d))
    d = (
        "m 23.316361,24.790231 h -1.266068 l -3.648345,-6.883279 v"
        " 6.883279 h -0.956011 v -7.694597 h 1.586461 l"
        " 3.327952,6.283835 v -6.283835 h 0.956011 z"
    )
    letters.add(path.Path(d=d))
    d = (
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
    letters.add(path.Path(d=d))
    symb.add(letters)
    return symb


@_factory()
def _or_control_node_symbol() -> container.Symbol:
    symb = _control_node_symbol("OrControlNodeSymbol")
    letters = container.Group(
        transform="matrix(2.1611566,0,0,2.4212253,-19.677936,-29.516726)",
        fill="#000",
    )
    d = (
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
    letters.add(path.Path(d=d))
    d = (
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
    letters.add(path.Path(d=d))
    symb.add(letters)
    return symb


@_factory()
def _iterate_control_node_symbol() -> container.Symbol:
    symb = _control_node_symbol("IterateControlNodeSymbol")
    letters = container.Group(
        transform="scale(1.0393759,0.9621158)",
        fill="#000",
    )
    d = "M 15.458523,38.056835 H 12.340129 V 11.439119 h 3.118394 z"
    letters.add(path.Path(d=d))
    d = (
        "M 38.178247,14.260523 H 30.493634 V 38.056835 H 27.375241 V "
        "14.260523 H 19.70919 v -2.821404 h 18.469057 z"
    )
    letters.add(path.Path(d=d))
    symb.add(letters)
    return symb


def _control_node_symbol(id_: str) -> container.Symbol:
    symb = container.Symbol(id=id_, viewBox="-1 -1 52 52")
    symb.add(
        shapes.Circle(
            center=(25, 25),
            r=25,
            stroke="#000",
            stroke_width=2,
            fill="#fff",
        )
    )
    return symb


@_factory()
def _operational_actor_box_symbol() -> container.Symbol:
    symb = container.Symbol(
        id_="OperationalActorBoxSymbol",
        viewBox="-10 -10 79 79",
        stroke="#000",
        stroke_width=2,
    )
    symb.add(shapes.Circle(center=(6.8, 7.75), r=5, fill="none"))
    d = (
        "m 6.723408,12.783569 0.1864956,13.042426 -6.52734189,6.042591"
        " v 0 l 6.52734189,-6.042591 6.2009764,5.95285"
        " -6.2942242,-6.012678 -0.092832,-6.050988 6.2026382,0.033"
        " -12.3973765,0.02992"
    )
    symb.add(path.Path(d=d, fill="none"))
    return symb


@_factory()
def _operational_actor_symbol() -> container.Symbol:
    symb = container.Symbol(
        id_="OperationalActorSymbol",
        viewBox="0 0 50 50",
        stroke="#000",
        stroke_width=2,
    )
    center = (25.8, 9.965)
    symb.add(
        _make_rgradient(
            "gray",
            center=center,
            focal=center,
            r=8.06,
            stop_colors=("#fff", "#9aaab9"),
        )
    )
    symb.add(shapes.Circle(center=center, r=7.445, fill="url(#gray)"))
    d = (
        "m 25.643608,17.4341 0.276914,19.3657 -9.691951,8.97218 v 0 l"
        " 9.691951,-8.97218 9.207354,8.838931 -9.345812,-8.927765 "
        "-0.137836,-8.984648 9.209822,0.04899 -18.407914,0.04443"
    )
    symb.add(path.Path(d=d, fill="none"))
    return symb


@_factory()
def _mode_symbol() -> container.Symbol:
    symb = container.Symbol(id_="ModeSymbol", viewBox="-1 -1 4.6458 4.6458")
    symb.add(
        _make_lgradient(
            "mode-grey",
            start=(1, 0),
            end=(0, 1),
            stop_colors=("#000", "#fff"),
            stop_opacity=(0.45, 0),
        )
    )
    symb.add(
        shapes.Rect(
            insert=(0, 0),
            size=(2.6327, 2.6327),
            ry=0.25474,
            fill="url(#mode-grey)",
            stroke="#000",
            stroke_width=0.005,
        )
    )
    symb.add(
        text.Text(
            "M",
            insert=(0, 2.6458),
            transform="scale(1.3907 .71906)",
            fill="#000",
            font_size="2.4821px",
            stroke_width=0.062,
        )
    )
    return symb


@_factory()
def _state_symbol() -> container.Symbol:
    symb = container.Symbol(id_="StateSymbol", viewBox="-1 -1 4.6458 4.6458")
    symb.add(
        _make_lgradient(
            "state-grey",
            start=(1, 0),
            end=(0, 1),
            stop_colors=("#000", "#fff"),
            stop_opacity=(0.45, 0),
        )
    )
    symb.add(
        shapes.Rect(
            insert=(0, 0),
            size=(2.6327, 2.6327),
            ry=0.25474,
            fill="url(#state-grey)",
            stroke="#000",
            stroke_width=0.005,
        )
    )
    symb.add(
        text.Text(
            "S",
            insert=(0, 2.6458),
            transform="scale(1.2578 .79502)",
            fill="#000",
            font_size="3.274px",
            stroke_width=0.082,
        )
    )
    return symb


@_factory()
def _terminate_pseudo_state_symbol() -> container.Symbol:
    symb = container.Symbol(
        id="TerminatePseudoStateSymbol", viewBox="0 0 10 10"
    )
    symb.add(
        path.Path(
            d="M 0,0 10,10 M 0,10 10,0",
            fill="none",
            stroke="#000",
            stroke_width=0.165,
        )
    )
    return symb


@_factory()
def _requirement_symbol() -> container.Symbol:
    symb = container.Symbol(id="RequirementSymbol", viewBox="0 0 50 50")
    d = (  # Circle
        "M 12.806813,6.5702324 A 6.244379,5.8113241 0 0 1"
        " 6.5624342,12.381557 6.244379,5.8113241 0 0 1"
        " 0.31805515,6.5702324 6.244379,5.8113241 0 0 1"
        " 6.5624342,0.75890827 6.244379,5.8113241 0 0 1"
        " 12.806813,6.5702324 Z"
    )
    symb.add(path.Path(d=d, fill="#431964", stroke="none"))
    d = (  # R
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
    )
    symb.add(path.Path(d=d, fill="#fff", stroke="none"))
    return symb


@_factory()
def _system_component_symbol() -> container.Symbol:
    symb = container.Symbol(id="SystemComponentSymbol", viewBox="0 12 79 55")
    grp = container.Group(
        transform="matrix(0.25509703,0,0,0.25509703,-19.119473,-26.4767)"
    )
    box_grp = container.Group(
        transform="matrix(0.92548165,0,0,0.92249056,-32.422011,-1.2909536)",
        fill="#e3ebf8",
        stroke_width=1.33145,
    )
    box_grp.add(
        path.Path(
            d="m 160.03785,180.47519 h 280.8845 v 200.68502 h -280.8845 z",
            stroke="#000",
            stroke_width=7,
        )
    )
    grp.add(box_grp)
    grp.add(
        path.Path(
            d="m 81.854696,210.17533 h 66.250264 v 35.37025 H 81.854696 Z",
            fill="#e7efff",
            stroke="#000",
            stroke_width=7,
        )
    )
    grp.add(
        path.Path(
            d="m 83.588316,268.94271 h 66.250254 v 35.37024 H 83.588316 Z",
            fill="#e7efff",
            stroke="#000",
            stroke_width=7,
        )
    )

    # Black connected boxes
    params = {
        "size": (5, 5),
        "fill": "#000",
        "stroke": "#000",
        "stroke_width": 54.1038,
    }
    grp.add(shapes.Rect(insert=(214.8075, 236.39), **params))
    grp.add(shapes.Rect(insert=(297.44, 298.36), **params))
    grp.add(shapes.Rect(insert=(297.44, 215.73), **params))
    grp.add(
        path.Path(
            d="m 219.70896,218.22099 h 79.0257 v 85.9132 h -80.34135 z",
            fill="none",
            stroke="#000",
            stroke_width="4.29901px",
        )
    )
    symb.add(grp)
    return symb


@_factory()
def _system_actor_symbol() -> container.Symbol:
    symb = container.Symbol(id="SystemActorSymbol", viewBox="0 0 79 79")
    grp = container.Group(
        transform="matrix(1.4376083,0,0,1.3022512,-15.958775,-15.416201)"
    )
    d = "M 17.819891,20.041161 H 65.286364 V 64.242623 H 17.819891 Z"
    grp.add(path.Path(d=d, fill="#bdf7ff", stroke="#454647"))
    d = "m 12.064948,25.832262 h 11.521155 v 6.687244 H 12.064948 Z"
    grp.add(path.Path(d=d, fill="#e3ebf8", stroke="#454647"))
    d = "m 12.050427,34.529197 h 11.455007 v 6.635451 H 12.050427 Z"
    grp.add(path.Path(d=d, fill="#e3ebf8", stroke="#454647"))
    grp1 = container.Group(
        transform="matrix(0.83129224,0,0,0.89544642,8.0334318,11.729573)",
        fill="#000",
        stroke="none",
    )
    d = (
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
    grp1.add(path.Path(d=d))
    d = (
        "M 66.819105,48.758301 H 61.916408 L 59.493237,41.90204 H"
        " 48.898904 l -2.32925,6.856261 H 41.685742 L"
        " 51.772899,21.821647 h 5.034186 z M 58.309827,38.25789"
        " 54.571756,27.513283 q -0.169058,-0.525959"
        " -0.356901,-1.690585 h -0.07514 q -0.169059,1.070704"
        " -0.375686,1.690585 L 50.06353,38.25789 Z"
    )
    grp1.add(path.Path(d=d))
    grp.add(grp1)
    symb.add(grp)
    return symb


@_factory()
def _mission_symbol() -> container.Symbol:
    symb = _brown_oval("MissionSymbol")
    d = (
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
    )
    transform = "matrix(0.86023492,0,0,0.64311175,6.4177697,4.9887121)"
    symb.add(path.Path(d=d, transform=transform, fill="#000", stroke="none"))
    return symb


@_factory()
def _capability_symbol() -> container.Symbol:
    symb = _brown_oval("CapabilitySymbol")
    grp = container.Group(
        transform="matrix(0.86023492,0,0,0.64311175,6.4177697,4.9887121)"
    )
    d = (
        "m 25.147125,33.08327 q -2.060058,0.997225 -5.379769,0.997225"
        " -4.330058,0 -6.81,-2.545549 -2.479942,-2.545549"
        " -2.479942,-6.783757 0,-4.513757 2.781734,-7.321734"
        " 2.794856,-2.807977 7.243006,-2.807977 2.755491,0"
        " 4.644971,0.695434 v 4.080751 q -1.88948,-1.128439"
        " -4.303815,-1.128439 -2.65052,0 -4.277572,1.666416"
        " -1.627052,1.666416 -1.627052,4.513757 0,2.729249"
        " 1.535202,4.356301 1.535202,1.61393 4.133237,1.61393"
        " 2.479942,0 4.54,-1.207167 z"
    )
    transform = "scale(1.1743865,0.85150843)"
    grp.add(path.Path(d=d, transform=transform, fill="#000", stroke="none"))
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
            matrix=[
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
            fill="url(#brown_oval)",
            stroke="#563b18",
            stroke_width=1,
        )
    )
    return symb


@_factory(needs="StickFigure")
def _system_human_actor_symbol() -> container.Symbol:
    return standalone_stick_figure_symbol("SystemHumanActorSymbol")


@_factory()
def _class_symbol() -> container.Symbol:
    symb = container.Symbol(id="ClassSymbol", viewBox="0 0 25 25")
    grad_id = "ClassSymbol-gradient"
    symb.add(_make_lgradient(grad_id, stop_colors=("#cfa6a5", "#f1e2e3")))
    grp = symb.add(container.Group(stroke="#913734"))
    grp.add(shapes.Rect(insert=(5, 17), size=(15, 3), fill="#eedcdd"))
    grp.add(shapes.Rect(insert=(5, 14), size=(15, 3), fill="#eedcdd"))
    grp.add(shapes.Rect(insert=(5, 4), size=(15, 10), fill=f"url(#{grad_id})"))
    return symb


@_factory()
def _class_feature_symbol() -> container.Symbol:
    symb = container.Symbol(id="ClassFeatureSymbol", viewBox="0 0 27 21")
    grad_id = "ClassFeatureSymbol-gradient"
    symb.add(_make_lgradient(grad_id, stop_colors=("#cfa6a5", "#f1e2e3")))
    grp = symb.add(container.Group())
    grp.add(shapes.Rect(insert=(7, 4), fill="#913734", size=(17, 11.5)))
    grp.add(
        shapes.Rect(insert=(7, 5), size=(17, 9.5), fill=f"url(#{grad_id})")
    )
    grp.add(
        shapes.Circle(
            center=(20.7, 12.1),
            r=4.1,
            fill="#f1e2e3",
            stroke="#913734",
            stroke_width=1,
        )
    )
    return symb


@_factory()
def _enumeration_symbol() -> container.Symbol:
    symb = container.Symbol(id="EnumerationSymbol", viewBox="0 0 25 20")
    grad_id = "EnumerationSymbol-gradient"
    symb.add(_make_lgradient(grad_id, stop_colors=("#cfa6a5", "#f1e2e3")))
    grp = symb.add(container.Group(stroke="#913734"))
    grp.add(shapes.Rect(insert=(5, 13), size=(15, 3.5), fill="#eedcdd"))
    grp.add(shapes.Rect(insert=(5, 4), size=(15, 9), fill=f"url(#{grad_id})"))
    letters = container.Group(
        transform="scale(0.3,0.3) translate(20, 16)",
        stroke="#000",
        stroke_width=1.5,
    )
    d1 = (
        "M 4.25 17.4 L 0 17.6 L 0 15.6 L 3.375 15.475 L 3.375 2.65 "
        "L 0.25 2.875 L 0.25 1 L 5.625 0 L 5.625 15.475 L 8.5 15.6 "
        "L 8.5 17.6 L 4.25 17.4 Z"
    )
    letters.add(path.Path(d=d1))
    d2 = (
        "M 13.375 15.5 L 24.625 15.5 L 24.625 17.5 L 11.125 17.5 "
        "L 11.125 8.7 L 22.375 7.45 L 22.375 2 L 11.375 2 L 11.375 0 "
        "L 22.625 0 L 24.625 2 L 24.625 9.125 L 13.375 10.375 L 13.375 15.5 Z"
    )
    letters.add(path.Path(d=d2, transform="translate(1, 3)"))
    d3 = (
        "M 40.375 15.5 L 38.375 17.5 L 26.875 17.5 L 26.875 15.5 "
        "L 38.125 15.5 L 38.125 9.5 L 28.375 9.5 L 28.375 7.5 L 37.625 7.5 "
        "L 37.625 2 L 27.125 2 L 27.125 0 L 37.875 0 L 39.875 2 "
        "L 39.875 7.275 L 38.45 8.35 L 40.375 9.85 L 40.375 15.5 Z"
    )
    letters.add(path.Path(d=d3, transform="translate(3, 6)"))
    symb.add(letters)
    return symb


@_factory()
def _enumeration_feature_symbol() -> container.Symbol:
    symb = container.Symbol(id="EnumerationFeatureSymbol", viewBox="0 0 27 21")
    grad_id = "EnumerationFeatureSymbol-gradient"
    symb.add(_make_lgradient(grad_id, stop_colors=("#cfa6a5", "#f1e2e3")))
    grp = symb.add(container.Group())
    grp.add(shapes.Rect(insert=(7, 4), fill="#913734", size=(17, 11.5)))
    grp.add(
        shapes.Rect(insert=(7, 5), size=(17, 9.5), fill=f"url(#{grad_id})")
    )
    letters = container.Group(
        transform="scale(0.4,0.4) translate(24, 15.5)",
        stroke="#000",
        stroke_width=1.5,
    )
    d1 = (
        "M 12.25 17.5 L 0 17.5 L 0 0 L 12 0 L 12 2 L 2.25 2 L 2.25 7.5 "
        "L 10.75 7.5 L 10.75 9.5 L 2.25 9.5 L 2.25 15.5 L 12.25 15.5 "
        "L 12.25 17.5 Z"
    )
    letters.add(path.Path(d=d1))
    d2 = (
        "M 27.25 17.5 L 14.5 17.5 L 14.5 0 L 16.75 0 L 16.75 15.5 "
        "L 27.25 15.5 Z"
    )
    letters.add(path.Path(d=d2, transform="translate(2, 0)"))
    symb.add(letters)
    return symb


@_factory()
def _representation_link_symbol() -> container.Symbol:
    symb = container.Symbol(id="RepresentationLinkSymbol", viewBox="0 0 16 16")
    grp = symb.add(container.Group(stroke_width=0.5))
    grp.add(
        shapes.Rect(
            insert=(5.95, 2.96),
            size=(4.98, 2.7),
            rx=0.5,
            fill="#d9d297",
            stroke="#a48a44",
        )
    )
    grp.add(
        shapes.Rect(
            insert=(1.66, 10.1),
            size=(4.98, 2.7),
            rx=0.5,
            fill="#abc0c9",
            stroke="#557099",
        )
    )
    grp.add(
        shapes.Rect(
            insert=(10.12, 10.1),
            size=(4.98, 2.7),
            rx=0.5,
            fill="#acbd57",
            stroke="#326f46",
        )
    )
    d = (
        "m 8.4526548,7.7355622 -4.3161119,-0.00711 0.00491,"
        "2.2573969 m 4.3112023,-2.250294 4.3161128,-0.00711 "
        "-0.0049,2.2573968"
    )
    grp.add(path.Path(d=d, fill="none", stroke="#557099"))
    d = "m 8.5000114,5.7276095 0.00519,2.0502552"
    grp.add(path.Path(d=d, fill="none", stroke="#557099"))
    return symb


@_factory()
def _physical_behavior_component_symbol() -> container.Symbol:
    return _make_physical_component_symbol(
        "PhysicalBehaviorComponentSymbol",
        color="#a5bde7",
    )


@_factory(needs="StickFigure")
def _physical_behavior_human_component_symbol() -> container.Symbol:
    symb = _make_icon_frame(
        "PhysicalBehaviorHumanComponentSymbol", color="#a5bde7"
    )
    symb.add(
        container.Use(
            href="#StickFigureSymbol",
            transform="matrix(0.62,0,0,0.62,23.82,16.51)",
        )
    )
    return symb


@_factory()
def _physical_behavior_actor_symbol() -> container.Symbol:
    symb = _make_icon_frame("PhysicalBehaviorActorSymbol", color="#a5bde7")
    letter = container.Group(transform="scale(0.7,0.7) translate(15, 15)")
    d = (
        "m 43.148621,34.293143 q 0,2.11571 -0.747979,3.93224"
        " -0.726611,1.79514 -2.051603,3.12014 -1.645557,1.64555"
        " -3.889499,2.47902 -2.243939,0.81209 -5.663277,0.81209 h"
        " -4.231429 v 11.86083 h -4.23143 v -31.82122 h 8.633826 q"
        " 2.863694,0 4.851185,0.49153 1.98749,0.47016 3.526192,1.49597"
        " 1.816524,1.21813 2.799583,3.03466 1.004431,1.81652"
        " 1.004431,4.59474 z m -4.402396,0.10687 q 0,-1.64556"
        " -0.577016,-2.8637 -0.577013,-1.21814 -1.752408,-1.98749"
        " -1.025802,-0.6625 -2.350798,-0.94032 -1.303619,-0.29919"
        " -3.312483,-0.29919 h -4.188686 v 12.71566 h 3.568931 q"
        " 2.564503,0 4.167321,-0.44878 1.602814,-0.47016"
        " 2.607242,-1.47459 1.004432,-1.0258 1.410478,-2.15846"
        " 0.427419,-1.13265 0.427419,-2.54313 z m 34.001037,22.09746 H"
        " 68.23801 l -3.120146,-8.8689 H 51.355032 l -3.120147,8.8689"
        " h -4.295541 l 11.583005,-31.82123 h 5.641907 z m"
        " -8.933021,-12.50195 -5.577791,-15.6221 -5.599169,15.6221 z"
    )
    letter.add(path.Path(d=d, stroke_width=0.1))
    symb.add(letter)
    return symb


@_factory()
def _physical_behavior_human_actor_symbol() -> container.Symbol:
    return standalone_stick_figure_symbol("PhysicalBehaviorHumanActorSymbol")


@_factory()
def _physical_node_component_symbol() -> container.Symbol:
    return _make_physical_component_symbol(
        "PhysicalNodeComponentSymbol",
        color="#ffff00",
    )


@_factory()
def _physical_component_symbol() -> container.Symbol:
    return _make_physical_component_symbol(
        "PhysicalComponentSymbol",
        color="#dbe6f4",
    )


@_factory(needs="StickFigure")
def _physical_node_human_component_symbol() -> container.Symbol:
    symb = _make_icon_frame(
        "PhysicalNodeHumanComponentSymbol", color="#ffff00"
    )
    symb.add(
        container.Use(
            href="#StickFigureSymbol",
            transform="matrix(0.62,0,0,0.62,23.82,16.51)",
        )
    )
    return symb


@_factory()
def _physical_node_actor_symbol() -> container.Symbol:
    symb = _make_icon_frame("PhysicalNodeActorSymbol", color="#bdf7ff")
    letter = container.Group(transform="scale(0.7,0.7) translate(15, 15)")
    d = (
        "m 43.148621,34.293143 q 0,2.11571 -0.747979,3.93224"
        " -0.726611,1.79514 -2.051603,3.12014 -1.645557,1.64555"
        " -3.889499,2.47902 -2.243939,0.81209 -5.663277,0.81209 h"
        " -4.231429 v 11.86083 h -4.23143 v -31.82122 h 8.633826 q"
        " 2.863694,0 4.851185,0.49153 1.98749,0.47016 3.526192,1.49597"
        " 1.816524,1.21813 2.799583,3.03466 1.004431,1.81652"
        " 1.004431,4.59474 z m -4.402396,0.10687 q 0,-1.64556"
        " -0.577016,-2.8637 -0.577013,-1.21814 -1.752408,-1.98749"
        " -1.025802,-0.6625 -2.350798,-0.94032 -1.303619,-0.29919"
        " -3.312483,-0.29919 h -4.188686 v 12.71566 h 3.568931 q"
        " 2.564503,0 4.167321,-0.44878 1.602814,-0.47016"
        " 2.607242,-1.47459 1.004432,-1.0258 1.410478,-2.15846"
        " 0.427419,-1.13265 0.427419,-2.54313 z m 34.001037,22.09746 H"
        " 68.23801 l -3.120146,-8.8689 H 51.355032 l -3.120147,8.8689"
        " h -4.295541 l 11.583005,-31.82123 h 5.641907 z m"
        " -8.933021,-12.50195 -5.577791,-15.6221 -5.599169,15.6221 z"
    )
    letter.add(path.Path(d=d, stroke_width=0.1))
    symb.add(letter)
    return symb


@_factory()
def _physical_node_human_actor_symbol() -> container.Symbol:
    return standalone_stick_figure_symbol("PhysicalNodeHumanActorSymbol")


def _make_port_box(id_: str) -> container.Symbol:
    port = container.Symbol(id=id_, viewBox="0 0 10 10")
    port.add(path.Path(d="M0 0h10v10H0z"))
    return port


def _make_edge_symbol(
    id_: str, grad_colors: tuple[str, str], middle_color: str
) -> container.Symbol:
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
            f"{grad_id}reverse",
            stop_colors=grad_colors[::-1],
            start=(0, 0),
            end=(1, 1),
        )
    )

    grp = container.Group(stroke="#000", stroke_width=2)
    grp.add(
        path.Path(
            d="M 36.190065,5.0377724 V 24.962228 H 26.17482 V 5.0377724 Z",
            fill=f"url(#{grad_id}reverse)",
        )
    )
    d = (
        "m 14.372107,10 h 12.622435 c 0.926189,0.585267"
        " 1.836022,1.274509 2.268178,5 -0.208657,2.812473"
        " -0.954601,4.503809 -2.273297,5 H 14.296948"
    )
    grp.add(path.Path(d=d, fill=middle_color))
    d = (
        "M 3.9464908,5.0048246 V 24.995175 H 10.87518 C"
        " 12.433713,24.159139 15.158267,20.291241 15.313795,15"
        " 15.498614,11.583142 14.059659,6.6240913 10.87518,5.0048246 c"
        " -2.2179509,0 -4.5908341,0 -6.9286892,0 z"
    )
    grp.add(path.Path(d=d, fill=f"url(#{grad_id})"))
    symb.add(grp)
    return symb


def _make_lgradient(
    id_,
    /,
    *,
    start=(0, 0),
    end=(0, 1),
    stop_colors=("#fff", "#000"),
    stop_opacity=(1, 1),
) -> gradients.LinearGradient:
    if len(start) != 2 or len(end) != 2:
        raise ValueError(
            "Exactly two values each for start and end are needed"
        )
    if len(stop_colors) != len(stop_opacity):
        raise ValueError(
            "stop_colors and stop_opacity must have the same lengths"
            f" (len(stop_colors) = {len(stop_colors)},"
            f" len(stop_opacity) = {len(stop_opacity)})"
        )

    offsets = [i / (len(stop_colors) - 1) for i in range(len(stop_colors))]
    grad = gradients.LinearGradient(id_=id_, start=start, end=end)
    for offset, stop_col, stop_op in zip(
        offsets, stop_colors, stop_opacity, strict=True
    ):
        grad.add_stop_color(offset=offset, color=stop_col, opacity=stop_op)
    return grad


def _make_rgradient(
    id_,
    /,
    *,
    center=(0, 0),
    r=1,
    focal=(0, 0),
    matrix=None,
    stop_colors=("#fff", "#000"),
    offsets=("0", "1"),
) -> gradients.RadialGradient:
    if len(stop_colors) != len(offsets):
        raise ValueError(
            "stop_colors and offsets must have the same lengths"
            f" (len(stop_colors) = {len(stop_colors)},"
            f" len(stop_opacity) = {len(offsets)})"
        )

    grad = gradients.RadialGradient(
        id_=id_,
        center=center,
        r=r,
        focal=focal,
        gradientUnits="userSpaceOnUse",
    )
    if matrix:
        grad.matrix(*matrix)
    for offset, stop_color in zip(offsets, stop_colors, strict=True):
        grad.add_stop_color(offset=offset, color=stop_color)
    return grad


def _make_icon_frame(id_: str, /, *, color: str) -> container.Symbol:
    symb = container.Symbol(
        id=id_, viewBox="0 0 79 79", stroke="#000", stroke_width=2
    )
    tf = "translate(0 -218)"
    symb.add(path.Path(d="M18 237h46v43H18z", transform=tf, fill=color))
    symb.add(path.Path(d="M12 247h11v8H12z", transform=tf, fill=color))
    symb.add(path.Path(d="M12 261h11v8H12z", transform=tf, fill=color))
    return symb


def _make_physical_component_symbol(id_: str, color: str) -> container.Symbol:
    symb = _make_icon_frame(id_, color=color)
    d = (
        "m 57.589299,33.276194 c 0,1.410473 -0.249326,2.72122"
        " -0.747979,3.93224 -0.484407,1.19676 -1.168275,2.236807"
        " -2.051603,3.12014 -1.097038,1.097033 -2.393538,1.923373"
        " -3.889499,2.47902 -1.495959,0.541393 -3.383718,0.81209"
        " -5.663277,0.81209 h -4.231429 v 11.86083 h -4.23143 v"
        " -31.82122 h 8.633826 c 1.909129,0 3.526191,0.163843"
        " 4.851185,0.49153 1.324993,0.31344 2.500391,0.812097"
        " 3.526192,1.49597 1.211016,0.812087 2.14421,1.82364"
        " 2.799583,3.03466 0.669621,1.211013 1.004431,2.742593"
        " 1.004431,4.59474 z m -4.402396,0.10687 c 0,-1.09704"
        " -0.192339,-2.051607 -0.577016,-2.8637 -0.384675,-0.812093"
        " -0.968811,-1.47459 -1.752408,-1.98749 -0.683868,-0.441667"
        " -1.467467,-0.755107 -2.350798,-0.94032 -0.869079,-0.19946"
        " -1.97324,-0.29919 -3.312483,-0.29919 h -4.188686 v 12.71566"
        " h 3.568931 c 1.709669,0 3.098776,-0.149593 4.167321,-0.44878"
        " 1.068543,-0.31344 1.937623,-0.80497 2.607242,-1.47459"
        " 0.669621,-0.683867 1.139781,-1.403353 1.410478,-2.15846"
        " 0.284946,-0.7551 0.427419,-1.60281 0.427419,-2.54313 z"
    )
    symb.add(path.Path(d=d, fill="#000", stroke_width=0.1))
    return symb
