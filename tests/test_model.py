# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=redefined-outer-name

import collections.abc as cabc
import contextlib
import datetime
import importlib.metadata as imm
import math
import re
import textwrap
import typing as t
import unittest.mock as umock
import uuid

import pytest

from capellambse import model
from capellambse.filehandler import memory

NS = model.Namespace(
    "test://capellambse/{VERSION}",
    "capellambse",
    "capellambse.test.viewpoint",
    "1.0.0",
)
NS_URI = NS.uri.format(VERSION=NS.maxver)


@pytest.fixture
def fh() -> memory.MemoryFileHandler:
    """Create a memory file handler containing the boilerplate."""
    fh = memory.MemoryFileHandler()

    aird = """\
        <?xml version="1.0" encoding="UTF-8"?>
        <viewpoint:DAnalysis xmlns:viewpoint="http://www.eclipse.org/sirius/1.1.0">
          <semanticResources>main.afm</semanticResources>
          <semanticResources>main.capella</semanticResources>
        </viewpoint:DAnalysis>
        """
    fh.write_file("main.aird", textwrap.dedent(aird).encode("utf-8"))

    afm = f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <metadata:Metadata xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:metadata="http://www.polarsys.org/kitalpha/ad/metadata/1.0.0" id="_mainafm">
          <viewpointReferences id="_mainafm_core" vpId="org.polarsys.capella.core.viewpoint" version="5.0.0"/>
          <viewpointReferences id="_mainafm_test" vpId="{NS.viewpoint}" version="{NS.maxver}"/>
        </metadata:Metadata>
        """
    fh.write_file("main.afm", textwrap.dedent(afm).encode("utf-8"))

    capella = """\
        <?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj xmlns:demo="test://capellambse/1.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
        """
    fh.write_file("main.capella", textwrap.dedent(capella).encode("utf-8"))

    return fh


@pytest.fixture(scope="module", autouse=True)
def mock_namespaces() -> cabc.Iterator[None]:
    """Mock the entry_points function to list our test namespace.

    We don't want the test namespace to be registered permanently, so
    that test classes don't have a chance of accidentally ending up in a
    real model. So we mock importlib to temporarily add our namespace
    while tests that need it are running.
    """
    real_entry_points = imm.entry_points

    def mocked_entry_points(*, group: str):
        ns_group = "capellambse.namespaces"
        if group == ns_group:
            fake_ep = imm.EntryPoint(
                name="demo",
                group=ns_group,
                value=__name__ + ":NS",
            )
            return [fake_ep] + list(real_entry_points(group=group))
        return real_entry_points(group=group)

    with umock.patch("importlib.metadata.entry_points", mocked_entry_points):
        yield


class ParentObj(model.ModelElement):
    children = model.Containment["ChildObj"]("ownedChild", (NS, "ChildObj"))
    inquisition = model.Containment["SpanishInquisition"](
        "ownedInquisition", (NS, "SpanishInquisition")
    )


class ChildObj(model.ModelElement):
    name = model.StringPOD(name="name")

    children = model.Containment["ChildObj"]("ownedChild", (NS, "ChildObj"))

    associated = model.Association["ChildObj"]("associated", (NS, "ChildObj"))

    allocated = model.Allocation["ChildObj"](
        (NS, "Allocation"),
        ("ownedAllocation", "allocated"),
        (NS, "ChildObj"),
    )


class PODContainer(model.ModelElement):
    name = model.StringPOD(name="name")
    cost = model.FloatPOD(name="cost")
    amount = model.IntPOD(name="amount")
    is_used = model.BoolPOD(name="is_used")
    last_sold = model.DateTimePOD(name="last_sold")

    author_name = model.StringPOD(name="author_name", writable=False)


class SpanishInquisition(model.ModelElement):
    pass


class Company(model.ModelElement):
    vehicles = model.Containment["Vehicle"]("ownedVehicles", (NS, "Vehicle"))
    cars = model.TypeFilter["Car"]("vehicles", (NS, "Car"))
    buses = model.TypeFilter["Bus"]("vehicles", (NS, "Bus"))
    trains = model.TypeFilter["Train"]("vehicles", (NS, "Train"))

    drivers = model.Containment["Driver"]("employedDrivers", (NS, "Driver"))


class Vehicle(model.ModelElement, abstract=True):
    passengers = model.IntPOD("passengers")


class Car(Vehicle):
    build_year = model.IntPOD("buildYear")


class Bus(Vehicle):
    is_double_decker = model.BoolPOD("doubleDecker")


class Train(Vehicle):
    is_high_speed = model.BoolPOD("highSpeed")


class Driver(model.ModelElement):
    vehicles = model.Association["Vehicle"]("vehicles", (NS, "Vehicle"))


class TrainDriver(Driver):
    vehicles = model.TypeFilter["Train"](  # type: ignore[assignment]
        None, (NS, "Train")
    )


class TestModel:
    @staticmethod
    def test_loaded_model_root_is_instance_of_parent_class(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = loaded.root
        assert isinstance(obj, ParentObj)

    @staticmethod
    def test_loading_fails_if_a_namespace_is_missing(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild xsi:type="missing_namespace:ChildObj"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(ValueError, match="Bad XML"):
            model.Model(fh, entrypoint="main.aird")

    @staticmethod
    def test_loading_fails_if_an_object_has_no_xsi_type(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(ValueError, match="Bad XML"):
            model.Model(fh, entrypoint="main.aird")

    @staticmethod
    def test_loading_fails_if_root_object_has_no_namespace(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(ValueError, match="Bad XML"):
            model.Model(fh, entrypoint="main.aird")

    @staticmethod
    def test_loading_models_warns_about_unhandled_children(fh, caplog) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <unownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird")

        assert "Alien Menace" in caplog.text
        assert re.search(r"unhandled children:", caplog.text)
        assert re.search(r"\n.*\bunownedChild\b.*", caplog.text)
        alien = loaded.by_uuid("83567fe3-3acd-46b1-8a76-df48dfa322d1")
        assert isinstance(alien, ChildObj)

    @staticmethod
    def test_loading_models_warns_about_alien_attributes(fh, caplog) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            unhandledAttribute="true"/>
        """
        fh.write_file("main.capella", xml)

        model.Model(fh, entrypoint="main.aird")

        assert "Alien Menace" in caplog.text
        assert "unhandled attributes: unhandledAttribute" in caplog.text

    @staticmethod
    def test_loading_models_warns_about_unhandled_text(fh, caplog) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            >this is fine.</demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        model.Model(fh, entrypoint="main.aird")

        assert "Alien Menace" in caplog.text
        assert "unhandled text: 'this is fine.'" in caplog.text

    @staticmethod
    def test_model_objects_can_be_found_via_by_uuid(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)
        root = loaded.root

        obj = loaded.by_uuid("19e0fd7b-c3ab-4746-b6e7-7df57840f7b4")
        assert obj is root

    @staticmethod
    def test_model_loads_multiple_roots_from_xmi(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI
            xmi:version="2.0"
            xmlns:xmi="http://www.omg.org/XMI"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:demo="test://capellambse/1.0.0">
          <demo:ParentObj id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
          <demo:ParentObj id="f395a8f0-3220-4de8-9eaf-205cb7d5d1eb"/>
        </xmi:XMI>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        assert len(loaded.trees) == 3
        assert all(
            isinstance(i, (model.Metadata, ParentObj)) for i in loaded.trees
        )

    @staticmethod
    def test_model_loads_aird_with_xmi(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI
            xmi:version="2.0"
            xmlns:xmi="http://www.omg.org/XMI"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
            xmlns:demo="test://capellambse/1.0.0">
          <viewpoint:DAnalysis xmlns:viewpoint="http://www.eclipse.org/sirius/1.1.0">
            <semanticResources>main.afm</semanticResources>
            <semanticResources>main.capella</semanticResources>
          </viewpoint:DAnalysis>
        </xmi:XMI>
        """
        fh.write_file("main.aird", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        assert len(loaded.trees) == 2
        assert isinstance(loaded.root, ParentObj)

    @staticmethod
    def test_model_exposes_active_viewpoints(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <metadata:Metadata
            xmi:version="2.0"
            xmlns:xmi="http://www.omg.org/XMI"
            xmlns:metadata="http://www.polarsys.org/kitalpha/ad/metadata/1.0.0"
            id="_mainafm">
          <viewpointReferences
            id="_mainafm_core"
            vpId="org.polarsys.capella.core.viewpoint"
            version="5.0.0"/>
          <viewpointReferences
            id="_mainafm_test"
            vpId="capellambse.test.viewpoint"
            version="1.0.0"/>
          <viewpointReferences
            id="_mainafm_kitreq"
            vpId="org.polarsys.kitalpha.vp.requirements"
            version="0.13.0"/>
          <viewpointReferences
            id="_mainafm_capreq"
            vpId="org.polarsys.capella.vp.requirements"
            version="0.13.0"/>
        </metadata:Metadata>
        """
        fh.write_file("main.afm", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        assert loaded.metadata.viewpoints.as_dict() == {
            "capellambse.test.viewpoint": "1.0.0",
            "org.polarsys.capella.core.viewpoint": "5.0.0",
            "org.polarsys.kitalpha.vp.requirements": "0.13.0",
            "org.polarsys.capella.vp.requirements": "0.13.0",
        }


class TestPOD:
    @staticmethod
    def test_loading_pod_stores_data_on_the_object(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            name="Parent object"
            cost="7.5"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(PODContainer, loaded.root)
        assert obj.uuid == "19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
        assert obj.name == "Parent object"
        assert obj.cost == 7.5

    @staticmethod
    def test_loading_required_pod_fails_if_missing_from_xml(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError, match=r"[Mm]issing.*\bid\b"
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)

    @staticmethod
    def test_setting_readonly_pod_fails() -> None:
        obj = PODContainer(author_name="Wolciferon, Herald of the Winter Mist")
        with pytest.raises(AttributeError, match="read-only"):
            obj.author_name = "The Impostor"

    @staticmethod
    def test_deleting_readonly_pod_fails() -> None:
        obj = PODContainer(author_name="Wolciferon, Herald of the Winter Mist")
        with pytest.raises(AttributeError, match="read-only"):
            del obj.author_name

    @staticmethod
    def test_deleting_required_pod_fails() -> None:
        obj = PODContainer(uuid="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4")
        with pytest.raises(AttributeError, match="required"):
            del obj.uuid

    @staticmethod
    @pytest.mark.parametrize(
        ["xval", "pval"],
        [
            ("&amp;", "&"),
            ("&lt;", "<"),
            ("&gt;", ">"),
            ("&quot;", '"'),
            ("&apos;", "'"),
            ("&amp;&lt;&gt;&quot;&apos;", "&<>\"'"),
            ("&amp;lt;", "&lt;"),
            ("&amp;gt;", "&gt;"),
            ("&amp;quot;", "&quot;"),
            ("&amp;apos;", "&apos;"),
            (
                (
                    "&lt;p style=&quot;color: red&quot;&gt;"
                    "Hello &amp;amp; good day, world!&lt;/p&gt;"
                ),
                '<p style="color: red">Hello &amp; good day, world!</p>',
            ),
        ],
    )
    def test_string_pod_unescapes_xml_entities(fh, xval, pval) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            name="{}"/>
        """
        fh.write_file("main.capella", xml.format(xval).encode("utf-8"))

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(PODContainer, loaded.root)
        assert obj.name == pval

    @staticmethod
    @pytest.mark.parametrize(
        ["xval", "pval"],
        [
            ("7.5", 7.5),
            ("+7.5", 7.5),
            ("-7.5", -7.5),
            ("0.0", 0.0),
            ("0", 0.0),
            ("+0", 0.0),
            ("-0", 0.0),
            ("1.5e2", 150.0),
            ("1.5e+2", 150.0),
            ("1.5e-2", 0.015),
            ("1.5E2", 150.0),
            ("1.5E+2", 150.0),
            ("1.5E-2", 0.015),
            ("1.5e02", 150.0),
            ("1.5e+02", 150.0),
            ("1.5e-02", 0.015),
            ("1.5E02", 150.0),
            ("1.5E+02", 150.0),
            ("1.5E-02", 0.015),
            ("1.5e2", 150.0),
            ("*", math.inf),
        ],
    )
    def test_float_pod_loads_as_python_float(fh, xval, pval) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            cost="{}"/>
        """
        fh.write_file("main.capella", xml.format(xval).encode("utf-8"))

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(PODContainer, loaded.root)
        assert obj.cost == pval

    @staticmethod
    @pytest.mark.parametrize("value", [-math.inf, math.nan])
    def test_float_pod_rejects_invalid_values(value) -> None:
        with pytest.raises(ValueError, match=r"Invalid value.*\bcost\b"):
            PODContainer(cost=value)

    @staticmethod
    def test_int_pod_loads_as_python_int(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            amount="3"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(PODContainer, loaded.root)
        assert obj.amount == 3

    @staticmethod
    def test_bool_pod_loads_as_python_bool(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            is_used="true"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(PODContainer, loaded.root)
        assert obj.is_used is True

    @staticmethod
    def test_datetime_pod_loads_as_stdlib_datetime(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:PODContainer
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"
            last_sold="2019-07-23T17:45:30+0000"/>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        expected = datetime.datetime(
            2019, 7, 23, 17, 45, 30, tzinfo=datetime.timezone.utc
        )
        obj = t.cast(PODContainer, loaded.root)
        assert obj.last_sold == expected

    @staticmethod
    def test_datetime_pod_accepts_none_values() -> None:
        obj = PODContainer(last_sold=None)

        assert obj.last_sold is None

    @staticmethod
    def test_datetime_pod_returns_none_after_deleting_value() -> None:
        obj = PODContainer(last_sold=datetime.datetime.now())

        del obj.last_sold

        assert obj.last_sold is None

    @staticmethod
    def test_datetime_pod_converts_unaware_datetimes_to_localtime() -> None:
        timestamp = datetime.datetime(2019, 7, 23, 17, 45, 30)
        obj = PODContainer(last_sold=timestamp)

        assert obj.last_sold == timestamp.astimezone()

    @staticmethod
    def test_datetime_truncates_to_millisecond_precision() -> None:
        timestamp = datetime.datetime(
            2019, 7, 23, 17, 45, 30, 123456, tzinfo=datetime.timezone.utc
        )
        obj = PODContainer(last_sold=timestamp)

        assert obj.last_sold == timestamp.replace(microsecond=123000)


class TestModelObject:
    @staticmethod
    def test_model_object_has_uuid() -> None:
        obj = model.ModelElement()

        assert obj.uuid is not None

    @staticmethod
    def test_model_object_uuid_is_immutable() -> None:
        obj = model.ModelElement()

        with pytest.raises(AttributeError):
            obj.uuid = "test"

    @staticmethod
    def test_model_object_uuid_is_unique() -> None:
        obj1 = model.ModelElement()
        obj2 = model.ModelElement()

        assert obj1.uuid != obj2.uuid

    @staticmethod
    def test_model_object_uuid_is_valid_uuid() -> None:
        obj = model.ModelElement()

        assert uuid.UUID(obj.uuid)

    @staticmethod
    @pytest.mark.parametrize(
        "uuid",
        [
            "19e0fd7b-c3ab-4746-b6e7-7df57840f7b4",
            uuid.UUID("19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"),
        ],
    )
    def test_model_uuid_can_be_specified(uuid) -> None:
        obj = model.ModelElement(uuid=uuid)

        assert obj.uuid == str(uuid)

    @staticmethod
    @pytest.mark.parametrize("missing", ["name", "cost", "amount"])
    def test_model_object_fails_instantiation_without_required_attributes(
        missing,
    ) -> None:
        class Test(model.ModelElement):
            name = model.StringPOD(name="name", required=True)
            cost = model.FloatPOD(name="cost", required=True)
            amount = model.IntPOD(name="amount", required=True)

        kwargs = {"name": "test", "cost": 1.0, "amount": 1}
        del kwargs[missing]

        with pytest.raises(TypeError, match=f": {missing}$"):
            Test(**kwargs)

    @staticmethod
    def test_model_object_lets_the_model_generate_a_uuid_if_given() -> None:
        mock_model: t.Any = umock.Mock()
        mock_model._generate_uuid.return_value = (
            "01234567-89ab-cdef-0123-456789abcdef"
        )

        obj = model.ModelElement(model=mock_model)

        assert obj.uuid == "01234567-89ab-cdef-0123-456789abcdef"
        mock_model._generate_uuid.assert_called_once_with()

    @staticmethod
    def test_accessing_model_on_unassociated_modelobject_raises_error() -> (
        None
    ):
        obj = model.ModelElement()

        with pytest.raises(AttributeError, match="model$"):
            _ = obj._model

    @staticmethod
    def test_model_object_can_be_associated_with_a_model() -> None:
        mock_model: t.Any = umock.Mock()

        obj = model.ModelElement(model=mock_model)

        assert obj._model is mock_model

    @staticmethod
    def test_model_object_can_be_associated_with_a_model_after_instantiation() -> (
        None
    ):
        mock_model: t.Any = umock.Mock()

        obj = model.ModelElement()
        obj._model = mock_model

        assert obj._model is mock_model

    @staticmethod
    def test_model_object_instantiation_fails_on_invalid_attributes() -> None:
        with pytest.raises(TypeError, match=": invalid$"):
            model.ModelElement(invalid="test")

    @staticmethod
    def test_model_object_disallows_setting_undefined_attributes() -> None:
        obj = model.ModelElement()

        with pytest.raises(AttributeError, match=": invalid$"):
            obj.invalid = "test"

    @staticmethod
    def test_aliens_cannot_be_instantiated() -> None:
        with pytest.raises(TypeError, match=r"\bAlien\b"):
            model.Alien()


class TestContainment:
    @staticmethod
    def test_containment_loads_child_objects_recursively(fh) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child A">
            <ownedChild
                xsi:type="demo:ChildObj"
                id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
                name="Child B">
              <ownedChild
                  xsi:type="demo:ChildObj"
                  id="581affc7-261a-4435-84c9-4051531c7342"
                  name="Child C"/>
            </ownedChild>
          </ownedChild>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        obj = t.cast(ParentObj, loaded.root)
        children = obj.children
        assert len(children) == 1
        assert children[0].uuid == "83567fe3-3acd-46b1-8a76-df48dfa322d1"
        assert children[0].name == "Child A"
        grandchildren = children[0].children
        assert len(grandchildren) == 1
        assert grandchildren[0].uuid == "7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
        assert grandchildren[0].name == "Child B"
        greatgrandcld = grandchildren[0].children
        assert len(greatgrandcld) == 1
        assert greatgrandcld[0].uuid == "581affc7-261a-4435-84c9-4051531c7342"
        assert greatgrandcld[0].name == "Child C"

    @staticmethod
    def test_containment_fails_to_load_if_xml_requests_an_unexpected_class(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:SpanishInquisition"
              id="decd01d7-d4c2-492e-a988-091d80a46743"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError,
            match=r"xsi:type .*\bSpanishInquisition\b",
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)

    @staticmethod
    def test_containment_fails_to_load_if_element_has_no_xsi_type(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              id="decd01d7-d4c2-492e-a988-091d80a46743"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError,
            match="[Mm]issing xsi:type",
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)


class TestAssociation:
    @staticmethod
    def test_association_resolves_forward_and_backward_references_at_load(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child A"/>
          <ownedChild
              xsi:type="demo:ChildObj"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
              name="Child B"
              associated="#83567fe3-3acd-46b1-8a76-df48dfa322d1 #581affc7-261a-4435-84c9-4051531c7342"/>
          <ownedChild
              xsi:type="demo:ChildObj"
              id="581affc7-261a-4435-84c9-4051531c7342"
              name="Child C"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)
        obj = loaded.by_uuid("7d3b0a26-f5cb-4775-8171-7ed63ebff1ff", ChildObj)

        assert len(obj.associated) == 2
        assert obj.associated[0].uuid == "83567fe3-3acd-46b1-8a76-df48dfa322d1"
        assert obj.associated[1].uuid == "581affc7-261a-4435-84c9-4051531c7342"

    @staticmethod
    def test_association_fails_loading_with_unexpected_target_classes(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child A"
              associated="#7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"/>
          <ownedInquisition
              xsi:type="demo:SpanishInquisition"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError,
            match=r"[Aa]ssociat\w+ .* SpanishInquisition\b",
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)


class TestAllocation:
    @staticmethod
    def test_allocation_resolves_forward_and_backward_references_at_load(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child A"/>
          <ownedChild
              xsi:type="demo:ChildObj"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
              name="Child B">
            <ownedAllocation
                xsi:type="demo:Allocation"
                id="842aaa8a-f320-4a8a-bf14-fa873b81dd79"
                allocated="#83567fe3-3acd-46b1-8a76-df48dfa322d1"/>
            <ownedAllocation
                xsi:type="demo:Allocation"
                id="558153e6-8e98-48ea-8da7-b90d0653ec8f"
                allocated="#581affc7-261a-4435-84c9-4051531c7342"/>
          </ownedChild>
          <ownedChild
              xsi:type="demo:ChildObj"
              id="581affc7-261a-4435-84c9-4051531c7342"
              name="Child C"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)
        obj = loaded.by_uuid("7d3b0a26-f5cb-4775-8171-7ed63ebff1ff", ChildObj)

        assert len(obj.allocated) == 2
        assert obj.allocated[0].uuid == "83567fe3-3acd-46b1-8a76-df48dfa322d1"
        assert obj.allocated[1].uuid == "581affc7-261a-4435-84c9-4051531c7342"

    @staticmethod
    def test_allocation_fails_to_load_with_unexpected_target_class(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child">
            <ownedAllocation
                xsi:type="demo:Allocation"
                id="842aaa8a-f320-4a8a-bf14-fa873b81dd79"
                allocated="#7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"/>
          </ownedChild>
          <ownedInquisition
              xsi:type="demo:SpanishInquisition"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"/>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError,
            match=r"[Uu]nexpected .*\bSpanishInquisition\b",
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)

    @staticmethod
    def test_allocation_fails_to_load_if_allocation_is_missing_xsi_type(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:ParentObj
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedChild
              xsi:type="demo:ChildObj"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              name="Child A"/>
          <ownedChild
              xsi:type="demo:ChildObj"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
              name="Child B">
            <ownedAllocation
                id="842aaa8a-f320-4a8a-bf14-fa873b81dd79"
                allocated="#83567fe3-3acd-46b1-8a76-df48dfa322d1"/>
          </ownedChild>
        </demo:ParentObj>
        """
        fh.write_file("main.capella", xml)

        with pytest.raises(
            model.BrokenModelError,
            match=r"[Mm]issing xsi:type",
        ):
            model.Model(fh, entrypoint="main.aird", xenophobia=True)


class TestTypeFilter:
    @staticmethod
    def test_type_filter_ignores_nonmatching_existing_members(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:Company
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedVehicles
              xsi:type="demo:Car"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              passengers="3"/>
          <ownedVehicles
              xsi:type="demo:Train"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
              passengers="300"/>
        </demo:Company>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        company = t.cast(Company, loaded.root)
        assert len(company.vehicles) == 2
        assert len(company.cars) == 1
        assert len(company.buses) == 0
        assert len(company.trains) == 1
        assert company.cars[0].passengers == 3
        assert company.trains[0].passengers == 300

    @staticmethod
    def test_type_filter_can_filter_same_named_attribute_from_super_class(fh):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <demo:Company
            xmlns:demo="test://capellambse/1.0.0"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
          <ownedVehicles
              xsi:type="demo:Car"
              id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
              passengers="3"/>
          <ownedVehicles
              xsi:type="demo:Train"
              id="7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"
              passengers="300"/>
          <employedDrivers
              xsi:type="demo:TrainDriver"
              id="842aaa8a-f320-4a8a-bf14-fa873b81dd79"
              vehicles="#83567fe3-3acd-46b1-8a76-df48dfa322d1 #7d3b0a26-f5cb-4775-8171-7ed63ebff1ff"/>
        </demo:Company>
        """
        fh.write_file("main.capella", xml)

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        company = t.cast(Company, loaded.root)
        driver = company.drivers[0]
        assert len(driver.vehicles) == 1
        assert isinstance(driver.vehicles[0], Train)


@pytest.mark.skip(reason="Not yet implemented")
class TestSaving:  # pylint: disable=line-too-long
    @staticmethod
    @pytest.mark.parametrize(
        "xml",
        [
            pytest.param(
                """\
                <?xml version="1.0" encoding="UTF-8"?>

                <!--Capella_Version_5.0.0-->
                <demo:ParentObj xmlns:demo="test://capellambse/1.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4"/>
                """,
                id="single",
            ),
            pytest.param(
                """\
                <?xml version="1.0" encoding="UTF-8"?>

                <!--Capella_Version_5.0.0-->
                <demo:ParentObj xmlns:demo="test://capellambse/1.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    id="19e0fd7b-c3ab-4746-b6e7-7df57840f7b4">
                  <ownedChild xsi:type="demo:ChildObj" id="83567fe3-3acd-46b1-8a76-df48dfa322d1"
                      name="Child A"/>
                </demo:ParentObj>
                """,
                id="nested",
            ),
        ],
    )
    def test_saving_produces_the_same_model_xml_that_was_read(fh, xml: str):
        xml = textwrap.dedent(xml)
        fh.write_file("main.capella", xml.encode("utf-8"))

        loaded = model.Model(fh, entrypoint="main.aird", xenophobia=True)

        fh.write_file("main.capella", b"")
        loaded.save()

        actual = fh.read_file("main.capella").decode("utf-8")
        assert actual == xml
