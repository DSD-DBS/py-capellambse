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
"""Implementation of a ReqIF 1.1 and 1.2 exporter"""
from __future__ import annotations

import collections.abc as cabc
import contextlib
import datetime
import itertools
import math
import os
import re
import typing as t
import zipfile

from lxml import builder, etree

import capellambse

from . import elements

NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
SCHEMA = "https://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
XHMTL_NS = "http://www.w3.org/1999/xhtml"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
NSMAP = {None: NS, "xhtml": XHMTL_NS, "xsi": XSI_NS}
REQIF_UTC_DATEFORMAT = "%Y-%m-%dT%H:%M:%SZ"
STANDARD_ATTRIBUTES = {
    "ForeignID": "STRING",
    "ChapterName": "XHTML",
    "Name": "XHTML",
    "Text": "XHTML",
}

E = builder.ElementMaker(namespace=NS)


class _AttributeDefinition(t.NamedTuple):
    modelobj: (
        elements.AbstractRequirementsAttribute
        | elements.EnumerationValueAttribute
        | None
    )
    type: str

    def __hash__(self) -> int:
        if self.modelobj is None:
            return hash((None, self.type))
        return hash((self.modelobj.uuid, self.type))


def export_module(
    module: elements.RequirementsModule,
    target: str | os.PathLike | t.IO[bytes],
    *,
    metadata: cabc.Mapping[str, t.Any] | None = None,
    pretty: bool = False,
    compress: bool | None = None,
) -> None:
    data = etree.Element(
        "REQ-IF",
        attrib={f"{{{XSI_NS}}}schemaLocation": f"{SCHEMA} {NS}"},
        nsmap=NSMAP,
    )
    header, timestamp = _build_header(module, metadata)
    data.append(header)
    data.append(_build_content(module, timestamp))

    if compress is None and isinstance(target, (str, os.PathLike)):
        compress = os.fspath(target).endswith(".reqifz")
    else:
        compress = False

    if not isinstance(target, (str, os.PathLike)):
        ctx: t.ContextManager[t.IO[bytes]] = contextlib.nullcontext(target)
    else:
        ctx = open(target, "wb")  # pylint: disable=consider-using-with

    with contextlib.ExitStack() as stack:
        container = stack.enter_context(ctx)
        if compress:
            archive = stack.enter_context(
                zipfile.ZipFile(container, "w", zipfile.ZIP_DEFLATED)
            )
            file = archive.open("export.reqif", "w")
        else:
            file = container
        etree.ElementTree(data).write(
            file, encoding="utf-8", pretty_print=pretty, xml_declaration=True
        )


def _build_header(
    module: elements.RequirementsModule,
    metadata: cabc.Mapping[str, t.Any] | None = None,
) -> tuple[etree._Element, str]:
    if metadata is None:
        metadata = {}
    comment = metadata.get(
        "comment",
        f"Requirements module {module.name!r} from {module._model.name!r}",
    )
    title = metadata.get("title", module.long_name)
    creation_time = (
        metadata.get("creation_time", datetime.datetime.now())
        .astimezone(datetime.timezone.utc)
        .strftime(REQIF_UTC_DATEFORMAT)
    )
    header = etree.Element("REQ-IF-HEADER")
    header.set("IDENTIFIER", "_" + module.uuid.upper())
    for key, value in (
        ("COMMENT", comment),
        ("CREATION-TIME", creation_time),
        ("REQ-IF-TOOL-ID", f"capellambse v{capellambse.__version__}"),
        ("REQ-IF-VERSION", "1.1"),
        ("SOURCE-TOOL-ID", f"Capella {module._model.info.capella_version}"),
        ("TITLE", title),
    ):
        header.append(el := etree.Element(key))
        el.text = value
    wrapper = etree.Element("THE-HEADER")
    wrapper.append(header)
    return wrapper, creation_time


def _build_content(
    module: elements.RequirementsModule, timestamp: str
) -> etree._Element:
    content = etree.Element("REQ-IF-CONTENT")

    datatypes = etree.Element("DATATYPES")
    spec_types = etree.Element("SPEC-TYPES")
    spec_objects = etree.Element("SPEC-OBJECTS")
    spec_relations = etree.Element("SPEC-RELATIONS")
    specifications = etree.Element("SPECIFICATIONS")
    spec_relation_groups = etree.Element("SPEC-RELATION-GROUPS")

    reqtypes = _collect_objects(module)
    attr_definitions = itertools.chain.from_iterable(reqtypes.values())
    children = list(_synthesize_standard_datatypes(timestamp))
    children.extend(_build_datatypes(attr_definitions, timestamp))
    children = sorted(children, key=lambda i: i.get("IDENTIFIER"))
    datatypes.extend(children)

    children = list(
        _build_spec_object_types(module._model, reqtypes.items(), timestamp)
    )
    children = sorted(children, key=lambda i: i.get("IDENTIFIER"))
    spec_types.extend(children)

    spec_objects.extend(_build_spec_objects(module, timestamp))
    specifications.extend(_build_specifications(module, timestamp))

    content.append(datatypes)
    content.append(spec_types)
    content.append(spec_objects)
    content.append(spec_relations)
    content.append(specifications)
    content.append(spec_relation_groups)

    wrapper = etree.Element("CORE-CONTENT")
    wrapper.append(content)
    return wrapper


def _synthesize_standard_datatypes(
    timestamp: str,
) -> t.Iterable[etree._Element]:
    for id, type in STANDARD_ATTRIBUTES.items():
        elem = etree.Element("DATATYPE-DEFINITION-STRING")
    return ()


def _build_datatypes(
    attrdefs: cabc.Iterable[_AttributeDefinition], timestamp: str
) -> cabc.Iterable[etree._Element]:
    visited_types: set[str] = set()
    for attrdef, attrtype in attrdefs:
        if attrdef and attrdef.data_type:
            uuid = attrdef.data_type.uuid.upper()
        else:
            uuid = "NULL-DATATYPE"

        id = f"_{uuid}--{attrtype}"
        if id in visited_types:
            continue
        visited_types.add(id)

        elem = etree.Element(f"DATATYPE-DEFINITION-{attrtype}")
        elem.set("IDENTIFIER", id)
        elem.set("LAST-CHANGE", timestamp)
        if attrdef and attrdef.data_type:
            if attrdef.data_type.long_name:
                elem.set("LONG-NAME", attrdef.data_type.long_name)

        type_attrs = {
            "STRING": {"MAX-LENGTH": "2147483647"},
            "REAL": {"ACCURACY": "100", "MAX": "Infinity", "MIN": "-Infinity"},
            "INTEGER": {"MAX": "2147483647", "MIN": "-2147483648"},
        }
        elem.attrib.update(type_attrs.get(attrtype, {}))

        if isinstance(attrdef, elements.AttributeDefinitionEnumeration):
            values = etree.Element("SPECIFIED-VALUES")
            for i in attrdef.data_type.values:
                v = etree.Element("ENUM-VALUE")
                v.set("IDENTIFIER", "_" + i.uuid.upper())
                v.set("LAST-CHANGE", timestamp)
                if i.long_name:
                    v.set("LONG-NAME", i.long_name)
                if i.description:
                    v.set("DESC", i.description)
                values.append(v)
            elem.append(values)

        yield elem


def _build_spec_object_types(
    model: capellambse.MelodyModel,
    reqtypes: cabc.Iterable[tuple[str | None, set[_AttributeDefinition]]],
    timestamp: str,
) -> cabc.Iterable[etree._Element]:
    for reqtype, attr_defs in reqtypes:
        modelobj: elements.RequirementType | None
        if reqtype:
            modelobj = model.by_uuid(reqtype)  # type: ignore[assignment]
            assert isinstance(modelobj, elements.RequirementType)
            reqtype = reqtype.upper()
        else:
            modelobj = None
            reqtype = "NULL-SPEC-TYPE"

        elem = etree.Element("SPEC-OBJECT-TYPE")
        elem.set("IDENTIFIER", "_" + reqtype)
        elem.set("LAST-CHANGE", timestamp)
        if not modelobj:
            elem.set("LONG-NAME", "Null spec type")
            elem.set("DESC", "No requirement type was selected in Capella.")
        else:
            _add_common_attributes(modelobj, elem)

        attributes_wrap = etree.Element("SPEC-ATTRIBUTES")
        # TODO add synthetic attribute definitions for standard attributes
        for attr_def in attr_defs:
            attr_elem = etree.Element(f"ATTRIBUTE-DEFINITION-{attr_def.type}")
            if attr_def.modelobj:
                attid = attr_def.modelobj.uuid.upper()
                dt = attr_def.modelobj.data_type
                dtid = dt.uuid.upper() if dt else "NULL-DATATYPE"
            else:
                attid = "NULL-ATTRIBUTE-DEFINITION"
                dtid = "NULL-DATATYPE"
            attr_elem.set("IDENTIFIER", f"_{attid}--{attr_def.type}")
            attr_elem.set("LAST-CHANGE", timestamp)
            _add_common_attributes(attr_def.modelobj, attr_elem)
            if attr_def.type == "ENUMERATION":
                assert attr_def.modelobj is not None
                attr_elem.set(
                    "MULTI-VALUED",
                    ("false", "true")[attr_def.modelobj.multi_valued],
                )

            dtref = etree.Element(f"DATATYPE-DEFINITION-{attr_def.type}-REF")
            dtref.text = f"_{dtid}--{attr_def.type}"
            dtwrap = etree.Element("TYPE")
            dtwrap.append(dtref)
            attr_elem.append(dtwrap)
            attributes_wrap.append(attr_elem)
        if len(attributes_wrap):
            elem.append(attributes_wrap)

        yield elem


def _build_spec_objects(
    parent: elements.RequirementsModule | elements.RequirementsFolder,
    timestamp: str,
) -> cabc.Iterable[etree._Element]:
    for req in parent.requirements:
        yield _build_spec_object(req, timestamp)

    for folder in parent.folders:
        yield from _build_spec_objects(folder, timestamp)


def _build_spec_object(
    req: elements.Requirement, timestamp: str
) -> etree._Element:
    obj = etree.Element("SPEC-OBJECT")
    obj.set("IDENTIFIER", "_" + req.uuid.upper())
    obj.set("LAST-CHANGE", timestamp)
    if req.long_name:
        obj.set("LONG-NAME", req.long_name)
    # TODO Add standard attributes (`ReqIF.Text` etc.)

    if req.attributes:
        obj.append(_build_attribute_values(req))

    obj.append(type := etree.Element("TYPE"))
    type.append(ref := etree.Element("SPEC-OBJECT-TYPE-REF"))
    if req.type:
        ref.text = "_" + req.type.uuid.upper()
    else:
        ref.text = "_NULL-SPEC-TYPE"

    return obj


def _build_attribute_values(req: elements.Requirement) -> etree._Element:
    factories = {
        elements.XT_REQ_ATTR_BOOLEANVALUE: _build_attribute_value_simple,
        elements.XT_REQ_ATTR_DATEVALUE: _build_attribute_value_simple,
        elements.XT_REQ_ATTR_INTEGERVALUE: _build_attribute_value_simple,
        elements.XT_REQ_ATTR_REALVALUE: _build_attribute_value_simple,
        elements.XT_REQ_ATTR_STRINGVALUE: _build_attribute_value_simple,
        elements.XT_REQ_ATTR_ENUMVALUE: _build_attribute_value_enum,
    }
    wrapper = etree.Element("VALUES")
    for attr in req.attributes:
        factory = factories[attr.xtype]
        wrapper.append(factory(attr))
    return wrapper


def _build_attribute_value_simple(
    attr: elements.AbstractRequirementsAttribute,
) -> etree._Element:
    attrtype = _attrtype2reqif(attr)
    obj = etree.Element(f"ATTRIBUTE-VALUE-{attrtype}")
    value: t.Any
    if attrtype == "BOOLEAN":
        obj.set("THE-VALUE", "true" if attr.value else "false")
    elif attrtype == "DATE":
        value = attr.value
        if value is None:
            obj.set("THE-VALUE", "1990-01-01T00:00:00Z")
        elif isinstance(value, datetime.datetime):
            utcval = value.astimezone(datetime.timezone.utc)
            obj.set("THE-VALUE", utcval.strftime(REQIF_UTC_DATEFORMAT))
        else:
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
    elif attrtype == "INTEGER":
        obj.set("THE-VALUE", str(int(attr.value)))
    elif attrtype == "REAL":
        value = attr.value
        if value == math.inf:
            value = "Infinity"
        elif value == -math.inf:
            value = "-Infinity"
        else:
            value = str(value)
        obj.set("THE-VALUE", value)
    elif attrtype == "STRING":
        obj.set("THE-VALUE", attr.value or "")
    else:
        raise ValueError(f"Unknown attribute type {attrtype}")
    obj.append(_ref_attribute_definition(attrtype, attr.definition))
    return obj


def _build_attribute_value_enum(
    attribute: elements.AbstractRequirementsAttribute,
) -> etree._Element:
    obj = etree.Element("ATTRIBUTE-VALUE-ENUMERATION")

    obj.append(_ref_attribute_definition("ENUMERATION", attribute.definition))

    obj.append(values := etree.Element("VALUES"))
    for i in attribute.values:
        values.append(ref := etree.Element("ENUM-VALUE-REF"))
        ref.text = "_" + i.uuid.upper()
    return obj


def _build_specifications(
    module: elements.RequirementsModule, timestamp: str
) -> cabc.Iterable[etree._Element]:
    def create_hierarchy_object(req: elements.Requirement) -> etree._Element:
        id = "_" + req.uuid.upper()
        id_hier = id + "--HIER"
        return E(
            "SPEC-HIERARCHY",
            {"IDENTIFIER": id_hier, "LAST-CHANGE": timestamp},
            E("OBJECT", E("SPEC-OBJECT-REF", id)),
        )

    def create_hierarchy_folder(
        folder: elements.RequirementsModule | elements.RequirementsFolder,
    ) -> cabc.Iterable[etree._Element]:
        for req in folder.requirements:
            yield create_hierarchy_object(req)
        for sub in folder.folders:
            yield from create_hierarchy_folder(sub)

    spec = E.SPECIFICATION(
        {"IDENTIFIER": "_" + module.uuid.upper(), "LAST-CHANGE": timestamp},
        wrapper := E.CHILDREN(),
    )
    if module.long_name:
        spec.set("LONG-NAME", module.long_name)
    if module.description:
        spec.set("DESC", module.description)

    wrapper.extend(create_hierarchy_folder(module))
    return (spec,)


def _ref_attribute_definition(
    type: str, adef: elements.AttributeDefinition | None
) -> etree._Element:
    if adef is not None:
        reftext = f"_{adef.uuid.upper()}--{type}"
    else:
        reftext = f"NULLTYPE--{type}"
    definition = etree.Element("DEFINITION")
    ref = etree.Element(f"ATTRIBUTE-DEFINITION-{type}-REF")
    ref.text = reftext
    definition.append(ref)
    return definition


def _add_common_attributes(obj: t.Any | None, element: etree._Element) -> None:
    if obj is None:
        return

    if value := obj.long_name:
        element.set("LONG-NAME", value)
    if value := obj.description:
        element.set("DESC", value)


def _collect_objects(
    module: elements.RequirementsModule,
) -> dict[str | None, set[_AttributeDefinition]]:
    requirements: set[str] = set()
    req_types: dict[str | None, set[_AttributeDefinition]] = {}

    def collect_requirement(i: elements.Requirement) -> None:
        if i.uuid in requirements:
            return
        requirements.add(i.uuid)
        attr_definitions = req_types.setdefault(i.type and i.type.uuid, set())
        for attr in i.attributes:
            adef = _AttributeDefinition(attr.definition, _attrtype2reqif(attr))
            attr_definitions.add(adef)

    def collect_folder(
        i: elements.RequirementsFolder | elements.RequirementsModule,
    ) -> None:
        for req in i.requirements:
            collect_requirement(req)
        for fld in i.folders:
            collect_folder(fld)

    collect_folder(module)
    return req_types


def _attrtype2reqif(
    attrtype: elements.AbstractRequirementsAttribute,
) -> str:
    m = re.fullmatch("([A-Z][A-Za-z]*)ValueAttribute", type(attrtype).__name__)
    assert m and m.group(1)
    return m.group(1).upper()
