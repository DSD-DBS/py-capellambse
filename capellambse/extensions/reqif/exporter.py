# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Implementation of a ReqIF 1.1 and 1.2 exporter."""

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

from lxml import builder, etree, html

import capellambse

from . import _capellareq as cr
from . import _requirements as rq

NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
SCHEMA = "https://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
XHMTL_NS = "http://www.w3.org/1999/xhtml"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
NSMAP = {None: NS, "xhtml": XHMTL_NS, "xsi": XSI_NS}
REQIF_UTC_DATEFORMAT = "%Y-%m-%dT%H:%M:%SZ"

STD_SPEC_OBJECT_ATTRIBUTES = {
    "ForeignID": {"type": "STRING", "attr": "identifier"},
    "ChapterName": {"type": "XHTML", "attr": "chapter_name"},
    "Name": {"type": "XHTML", "attr": "name"},
    "Text": {"type": "XHTML", "attr": "text"},
}
STD_SPECIFICATION_ATTRIBUTES = {
    "Description": {"type": "XHTML", "attr": "long_name"},
}

E = builder.ElementMaker(namespace=NS)


class _AttributeDefinition(t.NamedTuple):
    modelobj: rq.AttributeDefinition | rq.AttributeDefinitionEnumeration | None
    type: str

    def __hash__(self) -> int:
        if self.modelobj is None:
            return hash((None, self.type))
        return hash((self.modelobj.uuid, self.type))


def export_module(
    module: cr.CapellaModule,
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

    if compress is None and isinstance(target, str | os.PathLike):
        compress = os.fspath(target).endswith(".reqifz")
    else:
        compress = False

    if not isinstance(target, str | os.PathLike):
        ctx: t.ContextManager[t.IO[bytes]] = contextlib.nullcontext(target)
    else:
        ctx = open(target, "wb")  # noqa: SIM115

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
    module: cr.CapellaModule,
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
    header.set("IDENTIFIER", "_" + module._model.uuid.upper())
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


def _build_content(module: cr.CapellaModule, timestamp: str) -> etree._Element:
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
    children = sorted(children, key=lambda i: i.get("IDENTIFIER", ""))
    datatypes.extend(children)

    children = list(
        _build_spec_object_types(module._model, reqtypes.items(), timestamp)
    )
    children = sorted(children, key=lambda i: i.get("IDENTIFIER", ""))
    spec_types.extend(children)

    spec_types.append(_build_specification_type(module, timestamp))

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
    collected_names: list[str] = []
    for std_attributes in (
        STD_SPEC_OBJECT_ATTRIBUTES,
        STD_SPECIFICATION_ATTRIBUTES,
    ):
        for name, std_attr in std_attributes.items():
            if name in collected_names:
                continue
            collected_names.append(name)
            attributes = {
                "IDENTIFIER": f"_STD-DATATYPE-ReqIF.{name}",
                "LAST-CHANGE": timestamp,
                "LONG-NAME": f"ReqIF.{name}",
            }
            if std_attr["type"] == "STRING":
                attributes["MAX-LENGTH"] = "32000"
            elem = E(
                f"DATATYPE-DEFINITION-{std_attr['type']}",
                attributes,
            )
            yield elem


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
        if attrdef and attrdef.data_type and attrdef.data_type.long_name:
            elem.set("LONG-NAME", attrdef.data_type.long_name)

        type_attrs = {
            "STRING": {"MAX-LENGTH": "2147483647"},
            "REAL": {"ACCURACY": "100", "MAX": "Infinity", "MIN": "-Infinity"},
            "INTEGER": {"MAX": "2147483647", "MIN": "-2147483648"},
        }
        elem.attrib.update(type_attrs.get(attrtype, {}))

        if isinstance(attrdef, rq.AttributeDefinitionEnumeration):
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


def _build_specification_type(
    module: cr.CapellaModule, timestamp: str
) -> etree._Element:
    module_type = module.type
    identifier = (
        "NULL-SPECIFICATION-TYPE"
        if module_type is None
        else module_type.uuid.upper()
    )
    spec_attributes = E("SPEC-ATTRIBUTES")
    for name, std_attr in STD_SPECIFICATION_ATTRIBUTES.items():
        spec_attributes.append(
            E(
                f"ATTRIBUTE-DEFINITION-{std_attr['type']}",
                {
                    "IDENTIFIER": (
                        "_STD-SPECIFICATION-ATTRIBUTE-"
                        f"{identifier}"
                        f"-ReqIF.{name}"
                    ),
                    "LAST-CHANGE": timestamp,
                    "LONG-NAME": f"ReqIF.{name}",
                },
                E(
                    "TYPE",
                    E(
                        f"DATATYPE-DEFINITION-{std_attr['type']}-REF",
                        f"_STD-DATATYPE-ReqIF.{name}",
                    ),
                ),
            )
        )

    if module_type is None:
        return E(
            "SPECIFICATION-TYPE",
            {
                "IDENTIFIER": f"_{identifier}",
                "LAST-CHANGE": timestamp,
                "LONG-NAME": "Null specification type",
                "DESC": "No module type was selected in Capella.",
            },
            spec_attributes,
        )

    return E(
        "SPECIFICATION-TYPE",
        {
            "IDENTIFIER": f"_{identifier}",
            "LAST-CHANGE": timestamp,
            "LONG-NAME": module_type.long_name,
        },
        spec_attributes,
    )


def _build_spec_object_types(
    model: capellambse.MelodyModel,
    reqtypes: cabc.Iterable[tuple[str | None, set[_AttributeDefinition]]],
    timestamp: str,
) -> cabc.Iterable[etree._Element]:
    for reqtype, attr_defs in reqtypes:
        modelobj: rq.RequirementType | None
        if reqtype:
            modelobj = model.by_uuid(reqtype)
            assert isinstance(modelobj, rq.RequirementType)
            reqtype = reqtype.upper()
        else:
            modelobj = None
            reqtype = "NULL-SPEC-OBJECT-TYPE"

        elem = etree.Element("SPEC-OBJECT-TYPE")
        elem.set("IDENTIFIER", "_" + reqtype)
        elem.set("LAST-CHANGE", timestamp)
        if not modelobj:
            elem.set("LONG-NAME", "Null spec object type")
            elem.set("DESC", "No requirement type was selected in Capella.")
        else:
            _add_common_attributes(modelobj, elem)

        attributes_wrap = etree.Element("SPEC-ATTRIBUTES")
        for name, std_attr in STD_SPEC_OBJECT_ATTRIBUTES.items():
            attributes = {
                "IDENTIFIER": f"_STD-ATTRIBUTE-{reqtype}-ReqIF.{name}",
                "LAST-CHANGE": timestamp,
                "LONG-NAME": f"ReqIF.{name}",
            }
            elem_attrdef = E(
                f"ATTRIBUTE-DEFINITION-{std_attr['type']}",
                attributes,
                E(
                    "TYPE",
                    E(
                        f"DATATYPE-DEFINITION-{std_attr['type']}-REF",
                        f"_STD-DATATYPE-ReqIF.{name}",
                    ),
                ),
            )
            attributes_wrap.append(elem_attrdef)
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
    parent: cr.CapellaModule | rq.Folder,
    timestamp: str,
) -> cabc.Iterable[etree._Element]:
    for req in parent.requirements:
        yield _build_spec_object(req, timestamp)

    for folder in parent.folders:
        yield from _build_spec_objects(folder, timestamp)


def _build_spec_object(req: rq.Requirement, timestamp: str) -> etree._Element:
    obj = etree.Element("SPEC-OBJECT")
    obj.set("IDENTIFIER", "_" + req.uuid.upper())
    obj.set("LAST-CHANGE", timestamp)
    if req.long_name:
        obj.set("LONG-NAME", req.long_name)

    values_elem = E("VALUES")
    values_elem.extend(_build_standard_attribute_values(req))
    if req.attributes:
        values_elem.extend(_build_attribute_values(req))
    obj.append(values_elem)

    obj.append(type := etree.Element("TYPE"))
    type.append(ref := etree.Element("SPEC-OBJECT-TYPE-REF"))
    if req.type:
        ref.text = "_" + req.type.uuid.upper()
    else:
        ref.text = "_NULL-SPEC-OBJECT-TYPE"

    return obj


def _build_standard_attribute_values(
    req: rq.Requirement,
) -> t.Iterable[etree._Element]:
    if req.type:
        reqtype_ref = req.type.uuid.upper()
    else:
        reqtype_ref = "NULL-SPEC-OBJECT-TYPE"
    for name, std_attr in STD_SPEC_OBJECT_ATTRIBUTES.items():
        type_ = std_attr["type"]
        attrdef_ref = f"_STD-ATTRIBUTE-{reqtype_ref}-ReqIF.{name}"
        value_elem = None
        capella_val = getattr(req, std_attr["attr"])
        if capella_val is None:
            capella_val = ""
        if type_ == "STRING":
            value_elem = E(
                "ATTRIBUTE-VALUE-STRING",
                {"THE-VALUE": capella_val},
                E(
                    "DEFINITION",
                    E("ATTRIBUTE-DEFINITION-STRING-REF", attrdef_ref),
                ),
            )
        elif type_ == "XHTML":
            if capella_val:
                html_val = capella_val
            else:
                html_val = "<div></div>"
            xml_elem = html.fromstring(html_val)
            html.html_to_xhtml(xml_elem)
            value_elem = E(
                "ATTRIBUTE-VALUE-XHTML",
                E(
                    "DEFINITION",
                    E("ATTRIBUTE-DEFINITION-XHTML-REF", attrdef_ref),
                ),
                E("THE-VALUE", xml_elem),
            )
        if value_elem is not None:
            yield value_elem


def _build_attribute_values(
    req: rq.Requirement,
) -> t.Iterable[etree._Element]:
    for attr in req.attributes:
        if isinstance(attr, rq.EnumerationValueAttribute):
            yield _build_attribute_value_enum(attr)
        else:
            yield _build_attribute_value_simple(attr)


def _build_attribute_value_simple(
    attr: rq.AbstractRequirementsAttribute,
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
    attribute: rq.AbstractRequirementsAttribute,
) -> etree._Element:
    obj = etree.Element("ATTRIBUTE-VALUE-ENUMERATION")

    obj.append(_ref_attribute_definition("ENUMERATION", attribute.definition))

    obj.append(values := etree.Element("VALUES"))
    for i in attribute.values:
        values.append(ref := etree.Element("ENUM-VALUE-REF"))
        ref.text = "_" + i.uuid.upper()
    return obj


def _build_specifications(
    module: cr.CapellaModule, timestamp: str
) -> cabc.Iterable[etree._Element]:
    def create_hierarchy_object(req: rq.Requirement) -> etree._Element:
        id = "_" + req.uuid.upper()
        id_hier = id + "--HIER"
        return E(
            "SPEC-HIERARCHY",
            {"IDENTIFIER": id_hier, "LAST-CHANGE": timestamp},
            E("OBJECT", E("SPEC-OBJECT-REF", id)),
        )

    def create_hierarchy_folder(
        folder: cr.CapellaModule | rq.Folder,
    ) -> cabc.Iterable[etree._Element]:
        for req in folder.requirements:
            yield create_hierarchy_object(req)
        for sub in folder.folders:
            yield from create_hierarchy_folder(sub)

    module_type_ref = (
        "NULL-SPECIFICATION-TYPE"
        if (module_type := module.type) is None
        else module_type.uuid.upper()
    )

    spec_values = E("VALUES")

    for name, std_attr in STD_SPECIFICATION_ATTRIBUTES.items():
        attr_def_ref = (
            f"_STD-SPECIFICATION-ATTRIBUTE-{module_type_ref}-ReqIF.{name}"
        )
        if (type_ := std_attr["type"]) == "XHTML":
            xml_elem = html.fromstring(
                f"<div>{getattr(module, std_attr['attr'])}</div>"
            )
            html.html_to_xhtml(xml_elem)
            spec_values.append(
                E(
                    "ATTRIBUTE-VALUE-XHTML",
                    E.DEFINITION(
                        E("ATTRIBUTE-DEFINITION-XHTML-REF", attr_def_ref)
                    ),
                    E("THE-VALUE", xml_elem),
                )
            )
        else:
            spec_values.append(
                E(
                    f"ATTRIBUTE-VALUE-{type_}",
                    {"THE-VALUE": str(getattr(module, std_attr["attr"]))},
                    E.DEFINITION(
                        E(f"ATTRIBUTE-DEFINITION-{type_}-REF", attr_def_ref)
                    ),
                )
            )

    spec = E.SPECIFICATION(
        {
            "IDENTIFIER": "_" + module.uuid.upper(),
            "LAST-CHANGE": timestamp,
        },
        E.TYPE(E("SPECIFICATION-TYPE-REF", f"_{module_type_ref}")),
        spec_values,
        children := E.CHILDREN(),
    )
    if module.long_name:
        spec.set("LONG-NAME", module.long_name)
    if module.description:
        spec.set("DESC", module.description)

    children.extend(create_hierarchy_folder(module))
    return (spec,)


def _ref_attribute_definition(
    type: str, adef: rq.AttributeDefinition | None
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
    module: cr.CapellaModule,
) -> dict[str | None, set[_AttributeDefinition]]:
    requirements: set[str] = set()
    req_types: dict[str | None, set[_AttributeDefinition]] = {}

    def collect_requirement(i: rq.Requirement) -> None:
        if i.uuid in requirements:
            return
        requirements.add(i.uuid)
        attr_definitions = req_types.setdefault(i.type and i.type.uuid, set())
        for attr in i.attributes:
            adef = _AttributeDefinition(attr.definition, _attrtype2reqif(attr))
            attr_definitions.add(adef)

    def collect_folder(
        i: rq.Folder | cr.CapellaModule,
    ) -> None:
        for req in i.requirements:
            collect_requirement(req)
        for fld in i.folders:
            collect_folder(fld)

    collect_folder(module)
    return req_types


def _attrtype2reqif(
    attrtype: rq.AbstractRequirementsAttribute,
) -> str:
    m = re.fullmatch("([A-Z][A-Za-z]*)ValueAttribute", type(attrtype).__name__)
    assert m
    assert m.group(1)
    return m.group(1).upper()
