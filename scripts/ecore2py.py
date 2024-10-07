#!/usr/bin/env python
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import collections
import dataclasses
import enum
import logging
import operator
import re
import sys
import textwrap
import typing as t

import click
from lxml import etree

from capellambse import model
from capellambse.helpers import qtype_of

if sys.version_info >= (3, 11):
    from typing import assert_never
else:
    from typing_extensions import assert_never

LOGGER = logging.getLogger(__name__)

NS_ECORE = "http://www.eclipse.org/emf/2002/Ecore"
EPackage = etree.QName(NS_ECORE, "EPackage")
EEnum = etree.QName(NS_ECORE, "EEnum")
EClass = etree.QName(NS_ECORE, "EClass")
EReference = etree.QName(NS_ECORE, "EReference")
EAttribute = etree.QName(NS_ECORE, "EAttribute")

DOCUMENTATION_SOURCE = "http://www.polarsys.org/kitalpha/ecore/documentation"
XPATH_DESCRIPTION = (
    "./eAnnotations[@source='{}']/details[@key='{}']/@value"
).format(DOCUMENTATION_SOURCE, "{}")
BAD_DESCRIPTIONS = ("n/a", "none")


@click.command()
@click.argument("ecore_file", type=click.File("r"))
@click.argument("python_file", type=click.File("w"))
@click.option(
    "--subpackage",
    nargs=1,
    default=None,
    help=(
        "Write a module for the given subpackage."
        " Use '.' for the top-level package (equivalent to __init__.py)."
    ),
)
@click.option(
    "--docstrings/--no-docstrings",
    is_flag=True,
    default=True,
    help="Add docstrings with documentation extracted from the XML.",
)
@click.option(
    "--namespaces-module",
    is_flag=True,
    default=False,
    help=(
        "Assume a module named 'namespaces' containing all Namespace"
        " instances. If not passed, each imported module is assumed to have a"
        " top-level 'NS' attribute containing the respective Namespace"
        " instance."
    ),
)
def main(
    *,
    ecore_file: t.IO[str],
    python_file: t.IO[str],
    subpackage: str | None,
    docstrings: bool,
    namespaces_module: bool,
) -> None:
    """Generate a Python module from an ecore definition.

    Note that the code is generated on a best-effort basis, with no hard
    guarantees about syntactical correctness. Also, due to the script
    only handling a single file, import locations of other modules will
    likely need to be adjusted as well.

    Only basic code formatting is applied, mainly for syntactical
    reasons. It's recommended to run an auto-formatter over the produced
    output file.
    """
    logging.basicConfig(level="INFO")
    tree = etree.parse(ecore_file)
    root = tree.getroot()
    if qtype_of(root) != EPackage:
        raise click.UsageError(
            "Provided ecore file does not contain an EPackage as root element"
        )

    module_doc = find_description(root)

    imports: set[str] = set()
    classes = collections.deque[ClassDef]()
    enums: list[EnumDef] = []
    location_path: list[str] = []

    if subpackage is not None and subpackage != ".":
        for i in subpackage.split("."):
            location_path.append(i)
            pkgs = root.xpath(f"./eSubpackages[@name={i!r}]")
            if len(pkgs) > 1:
                raise SystemExit(
                    "Error: Multiple matches for subpackage"
                    f" {i!r} in {root.get('name')}"
                )
            if len(pkgs) < 1:
                raise SystemExit(f"Error: Subpackage not found: {subpackage}")
            (root,) = pkgs
    location = ".".join(location_path)

    for classifier in root.iterchildren("eClassifiers"):
        qtype = qtype_of(classifier)
        if qtype == EEnum:
            enums.append(parse_enum(classifier))
        elif qtype == EClass:
            cls, new_imports = parse_class(location, classifier)
            classes.append(cls)
            imports |= new_imports

    with python_file as f:
        if docstrings and module_doc:
            writedoc(f, module_doc, 0)

        f.write("from __future__ import annotations\n")
        if enums:
            f.write("\nimport enum\n")
        f.write("\nimport capellambse.model as m\n")

        if imports:
            if namespaces_module:
                imports.add("namespaces as ns")
            if subpackage is None:
                isource = "."
            elif subpackage == ".":
                isource = ".."
            else:
                isource = "." * (1 + subpackage.count("."))
            f.write(f"\nfrom {isource} import {', '.join(sorted(imports))}\n")

        # fmt: off
        f.write(
            (
                "\n"
                "NS = m.Namespace(\n"
                "    {nsURI!r},\n"
                "    {nsPrefix!r},\n"
                ")\n"
            ).format(**root.attrib)
        )
        # fmt: on

        write_enums(f, enums, docstrings)
        write_classes(f, location, classes, docstrings, namespaces_module)


def write_enums(
    f: t.IO[str],
    enums: list[EnumDef],
    docstrings: bool,
) -> None:
    for enumdef in sorted(enums, key=operator.attrgetter("name")):
        f.write("\n\n@m.stringy_enum\n@enum.unique\n")
        f.write(f"class {enumdef.name}(enum.Enum):\n")
        if docstrings and enumdef.docstring:
            writedoc(f, enumdef.docstring, 1)
            if enumdef.literals:
                f.write("\n")

        for lit in enumdef.literals:
            f.write(f"    {lit.name} = {lit.value!r}\n")
        if (not docstrings or not enumdef.docstring) and not enumdef.literals:
            f.write("    pass\n")


def write_classes(
    f: t.IO[str],
    location: str,
    classes: collections.deque[ClassDef],
    docstrings: bool,
    nsmodule: bool,
) -> None:
    written_classes: set[str] = set()
    while classes:
        cls = classes.popleft()

        for base in cls.bases:
            if "." in base or base in written_classes:
                continue
            classes.appendleft(cls)
            try:
                index, basedef = next(
                    (i, c) for i, c in enumerate(classes) if c.name == base
                )
            except StopIteration:
                if location:
                    isource = "." * (1 + location.count("."))
                    f.write(f"\n\nfrom {isource} import {base}")
                else:
                    raise ValueError(
                        f"Reference to undefined base {base}"
                    ) from None
                written_classes.add(base)
            else:
                del classes[index]
                classes.appendleft(basedef)
                break

        else:
            write_class(f, cls, docstrings=docstrings, nsmodule=nsmodule)
            written_classes.add(cls.name)


def write_class(
    f: t.IO[str],
    cls: ClassDef,
    *,
    docstrings: bool,
    nsmodule: bool,
) -> None:
    f.write(f"\n\nclass {cls.name}(")
    f.write(", ".join(cls.bases) or "m.ModelElement")
    if cls.abstract:
        f.write(", abstract=True")
    f.write("):\n")

    if docstrings and cls.docstring:
        writedoc(f, cls.docstring, 1)
        if cls.members:
            f.write("\n")

    for member in cls.members:
        if isinstance(member, EnumPODMember):
            f.write(
                f"    {member.name} = m.EnumPOD"
                f"({member.xmlname!r}, {member.pod_type})\n"
            )
        elif isinstance(member, PODMember):
            f.write(
                f"    {member.name} = m.{member.pod_type}POD"
                f"({member.xmlname!r})\n"
            )
        elif isinstance(member, RelationshipMember):
            write_relationship(f, member, nsmodule=nsmodule)
        else:
            raise AssertionError(
                f"Unhandled member type {type(member).__name__}"
            )
        if docstrings and member.docstring:
            writedoc(f, member.docstring, 1)

    if not cls.members and not (docstrings and cls.docstring):
        f.write("    pass\n")


def write_relationship(
    f: t.IO[str],
    member: RelationshipMember,
    *,
    nsmodule: bool,
) -> None:
    f.write(f"    {member.name} = ")

    member_type = member.type.value
    if member.single:
        f.write(f"m.Single[{member.cls!r}](m.{member_type}(")
    else:
        f.write(f"m.{member_type}[{member.cls!r}](")

    clsname = clsname2tuplestring(member.cls, nsmodule)
    match member.type:
        case RelationshipType.Containment:
            f.write(f"{member.xmlname!r}, {clsname}")
        case RelationshipType.Association:
            f.write(f"{clsname}, {member.xmlname!r}")
        case _:
            assert_never(f"Unhandled relationship type: {member.type.name}")

    if member.single:
        f.write(")")
    f.write(")\n")


def writedoc(f, docstring: str, indent: int) -> None:
    wrapped = f'"""{docstring}\n"""\n'
    f.write(textwrap.indent(wrapped, "    " * indent))


def find_description(element: etree._Element) -> str:
    description = [
        i.strip().replace("\r\n", "\n")
        for i in element.xpath(XPATH_DESCRIPTION.format("description"))
        if not i.lower().startswith(BAD_DESCRIPTIONS)
    ]
    assert all(isinstance(i, str) for i in description)

    usage_guideline = [
        i.strip().replace("\r\n", "\n")
        for i in element.xpath(XPATH_DESCRIPTION.format("usage guideline"))
        if not i.strip().lower().startswith(BAD_DESCRIPTIONS)
    ]
    if usage_guideline:
        description.append("Usage guideline\n---------------\n")
        description.extend(usage_guideline)
    return "\n\n".join(description)


@dataclasses.dataclass(frozen=True)
class EnumDef:
    name: str
    docstring: str
    literals: tuple[EnumLiteral, ...]


@dataclasses.dataclass(frozen=True)
class EnumLiteral:
    name: str
    docstring: str
    value: str


def parse_enum(element: etree._Element) -> EnumDef:
    literal_elems = sorted(
        element.iterchildren("eLiterals"),
        key=lambda i: int(i.get("value", "0")),
    )
    return EnumDef(
        name=element.attrib["name"],
        docstring=find_description(element),
        literals=tuple(
            EnumLiteral(
                name=screaming_snake(lit.attrib["name"]),
                docstring=find_description(lit),
                value=lit.attrib["name"],
            )
            for lit in literal_elems
        ),
    )


@dataclasses.dataclass(frozen=True)
class ClassDef:
    name: str
    docstring: str
    bases: tuple[str, ...]
    members: tuple[ClassMember, ...]
    abstract: bool


@dataclasses.dataclass(frozen=True)
class ClassMember:
    name: str
    docstring: str


@dataclasses.dataclass(frozen=True)
class PODMember(ClassMember):
    pod_type: str
    xmlname: str


@dataclasses.dataclass(frozen=True)
class EnumPODMember(PODMember):
    pass


@dataclasses.dataclass(frozen=True)
class RelationshipMember(ClassMember):
    type: RelationshipType
    cls: str
    single: bool
    xmlname: str


class RelationshipType(enum.Enum):
    Containment = model.Containment.__name__
    Association = model.Association.__name__


def parse_class(
    location: str, element: etree._Element
) -> tuple[ClassDef, set[str]]:
    imports: set[str] = set()
    bases: list[str] = []
    for base in element.get("eSuperTypes", "").split():
        name = clspath2dotted(base, start=location)
        if "." in name:
            imports.add(name.split(".", 1)[0])
        bases.append(name)

    members: list[ClassMember] = []
    clsname = element.attrib["name"]
    for member in element.iterchildren("eStructuralFeatures"):
        memberdef = parse_class_member(location, clsname, member)
        if memberdef is not None:
            members.append(memberdef)

    classdef = ClassDef(
        name=clsname,
        docstring=find_description(element),
        bases=tuple(bases),
        members=tuple(members),
        abstract=element.get("abstract", "false") == "true",
    )
    return classdef, imports


def parse_class_member(
    location: str,
    clsname: str,
    member: etree._Element,
) -> ClassMember | None:
    membname = member.attrib["name"]
    pyname = camel2snake(member.attrib["name"])
    qtype = qtype_of(member)
    if qtype == EReference:
        if member.get("derived", "false") == "true":
            LOGGER.warning(
                "Ignoring derived class member %s.%s", clsname, membname
            )
            return None

        clsname = clspath2dotted(
            member.attrib["eType"].rsplit(" ", 1)[-1], start=location
        )
        single = (
            member.get("upperBound", "0") == "1"
            or member.get("lowerBound", "0") == "1"
        )

        if member.get("containment", "false") == "true":
            return RelationshipMember(
                type=RelationshipType.Containment,
                name=camel2snake(membname).removeprefix("owned_"),
                docstring=find_description(member),
                xmlname=membname,
                cls=clsname,
                single=single,
            )

        return RelationshipMember(
            type=RelationshipType.Association,
            name=camel2snake(membname),
            docstring=find_description(member),
            xmlname=membname,
            cls=clsname,
            single=single,
        )

    if qtype == EAttribute:
        attrtype = clspath2dotted(
            member.attrib["eType"].rsplit(" ", 1)[-1], start=location
        )
        cls = PODMember
        if attrtype == "ecore.EBoolean":
            pod_type = "Bool"
            if pyname != "value":
                pyname = "is_" + pyname.removeprefix("is_")
        elif attrtype in {"ecore.EString", "ecore.EChar"}:
            pod_type = "String"
        elif attrtype in {
            "ecore.EByte",
            "ecore.EInt",
            "ecore.EBigInteger",
            "ecore.ELong",
        }:
            pod_type = "Int"
        elif attrtype in {"ecore.EDouble", "ecore.EFloat"}:
            pod_type = "Float"
        elif attrtype == "ecore.EDate":
            pod_type = "Datetime"
        else:
            cls = EnumPODMember
            pod_type = attrtype
        return cls(
            name=pyname,
            docstring=find_description(member),
            pod_type=pod_type,
            xmlname=member.attrib["name"],
        )

    LOGGER.warning("Unknown structural feature type: %s", qtype)
    return None


def screaming_snake(name: str) -> str:
    return re.sub(
        r"[a-z]+",
        lambda m: m.group(0).upper() + "_" * (m.span(0)[1] != len(name)),
        name,
    )


def camel2snake(name: str) -> str:
    return re.sub(
        "[A-Z]",
        lambda m: "_" * (m.start(0) > 0) + m.group(0).lower(),
        name,
    )


def clspath2dotted(path: str, *, start: str) -> str:
    module, _, name = path.rpartition("#//")
    name = name.replace("/", ".")
    if module:
        return f"{fname2modname(module)}.{name}"

    if name.startswith(f"{start}."):
        name = name.removeprefix(start).lstrip(".")
    return name


def fname2modname(fname: str) -> str:
    return fname.rpartition("/")[2].removesuffix(".ecore").lower()


def clsname2tuplestring(clsname: str, nsmodule: bool) -> str:
    if "." in clsname:
        module, clsname = clsname.rsplit(".", 1)
        if nsmodule:
            return f"(ns.{module.upper()}, {clsname!r})"
        return f"({module}.NS, {clsname!r})"
    return f"(NS, {clsname!r})"


if __name__ == "__main__":
    main()
