#!/usr/bin/env python
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import re
from typing import NamedTuple

import click
from lxml import etree

import capellambse
from capellambse import helpers


@click.command()
@click.argument(
    "metamodel",
    default="git+https://github.com/eclipse-capella/capella.git",
)
def main(metamodel: str):
    """Import all EEnum definitions from the given METAMODEL."""
    logging.basicConfig(level="INFO")
    handler = capellambse.get_filehandler(metamodel)

    print("import enum as _enum")
    print("class _StringyEnumMixin: ...")

    classes = {}
    for path in handler.rootdir.rglob("*.ecore"):
        with path.open("rb") as file:
            tree = etree.parse(file)
        for elem in tree.getroot().iter():
            if (
                elem.tag != "eClassifiers"
                or helpers.xtype_of(elem) != "ecore:EEnum"
            ):
                continue

            clsname = elem.attrib["name"]
            if clsname in classes:
                continue

            literals = [
                Literal(lit.attrib["name"], lit.get("value", "0"), getdoc(lit))
                for lit in elem.iterchildren("eLiterals")
            ]
            classes[clsname] = Class(clsname, literals, getdoc(elem))

    for i, cls in enumerate(sorted(classes.values())):
        if i:
            print("\n\n", end="")

        print("@_enum.unique")
        print(f"class {cls.name}(_StringyEnumMixin, _enum.Enum):")
        if cls.doc:
            print(f'    """{cls.doc}"""\n')
        for lit in cls.literals:
            print(f"    {fixname(lit.name)} = {lit.name!r}")
            if lit.doc:
                print(f'    """{lit.doc}"""')


def getdoc(elem: etree._Element) -> str:
    try:
        annotation = next(
            i
            for i in elem.iterchildren("eAnnotations")
            if i.get("source")
            == "http://www.polarsys.org/kitalpha/ecore/documentation"
        )
    except StopIteration:
        return ""

    detail = annotation.xpath(".//details[@key='description']/@value")
    if not detail:
        return ""
    return detail[0].replace("\r", "")


def fixname(name: str) -> str:
    return re.sub(
        r"[a-z]+",
        lambda m: m.group(0).upper() + "_" * (m.span(0)[1] != len(name)),
        name,
    )


class Class(NamedTuple):
    name: str
    literals: list[Literal]
    doc: str


class Literal(NamedTuple):
    name: str
    value: str
    doc: str


if __name__ == "__main__":
    main()
