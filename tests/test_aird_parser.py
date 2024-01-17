# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import json
import pathlib
import sys

import pytest

import capellambse
from capellambse import aird, diagram, loader

EMPTY_MODEL = pathlib.Path(__file__).parent.joinpath(
    "data/decl/empty_project_52/empty_project_52.aird"
)


class TestAIRDBasicFunctionality:
    test_model = (
        pathlib.Path(__file__).parent / "data" / "parser" / "TestItems.aird"
    )
    test_diagram = "[LAB] Logical System"
    test_json = test_model.with_suffix(".json")
    test_repr = test_model.with_suffix(".repr.txt")
    test_txt = test_model.with_suffix(".txt")

    @pytest.fixture
    def model(self):
        return loader.MelodyLoader(self.test_model)

    @pytest.fixture
    def diagram_under_test(self, model):
        descriptor = next(aird.enumerate_diagrams(model), None)
        assert descriptor is not None
        yield aird.parse_diagram(model, descriptor)

    def test_parsing_all_diagrams_does_not_raise_exceptions(
        self, model, caplog
    ):
        del caplog
        i = 0
        for i, _ in enumerate(aird.parse_diagrams(model), start=1):
            pass
        assert i == 1

    @pytest.mark.xfail(
        sys.platform not in {"win32", "cygwin"},
        reason="Expected rendering inaccuracies on non-Windows platforms",
    )
    @pytest.mark.skip(reason="Currently broken")
    def test_json_output_matches_expected_output(
        self, diagram_under_test, caplog
    ):
        del caplog
        expected = self.test_json.read_text().strip()
        encoder = diagram.DiagramJSONEncoder(indent=4)

        actual = encoder.encode(diagram_under_test)

        assert actual == expected

    @pytest.mark.xfail(
        sys.platform not in {"win32", "cygwin"},
        reason="Expected rendering inaccuracies on non-Windows platforms",
    )
    @pytest.mark.skip(reason="Currently broken")
    def test_plain_text_representation_matches_expected_output(
        self, diagram_under_test, caplog
    ):
        del caplog
        expected = self.test_txt.read_text()
        actual = str(diagram_under_test)
        assert actual + "\n" == expected

    @pytest.mark.xfail(
        sys.platform not in {"win32", "cygwin"},
        reason="Expected rendering inaccuracies on non-Windows platforms",
    )
    @pytest.mark.skip(reason="Currently broken")
    def test_python_code_representation_matches_expected_output(
        self, diagram_under_test, caplog
    ):
        del caplog
        expected = self.test_repr.read_text().strip()
        actual = repr(diagram_under_test)
        assert actual == expected

    def test_enumerate_diagrams_doesnt_crash_if_there_are_no_diagrams(self):
        model = loader.MelodyLoader(EMPTY_MODEL)
        for _ in aird.enumerate_diagrams(model):
            pass


def test_airdparser_msm_produces_valid_json_without_error(
    model: capellambse.MelodyModel,
):
    diag_name = "[MSM] States of Functional Human Being"
    all_diagrams = aird.enumerate_diagrams(model._loader)
    descriptor = next(i for i in all_diagrams if i.name == diag_name)
    parsed = aird.parse_diagram(model._loader, descriptor)

    generated_json = diagram.DiagramJSONEncoder(indent=4).encode(parsed)
    json.loads(generated_json)


@pytest.mark.parametrize(
    ["diag_uid", "num_nodes"],
    [
        ("_7FWu4KrxEeqOgqWuHJrXFA", 34),
        ("_KK2wcKyJEeqCdMaqCWkrKg", 14),
        ("_beibwNYrEeqiU8uzTY0Puw", 11),
        ("_9inmIKgWEeujco-rU7ZOtA", 1),
        ("_Go81cDaWEey5m4gkio8hew", 2),
        ("_-NRNIF2mEey8erljvkS-pQ", 13),
        ("_KZOz4GA9Eey8erljvkS-pQ", 15),
        ("_joc_sGDdEey8erljvkS-pQ", 5),
        ("_bpsckGDhEey8erljvkS-pQ", 4),
        ("_OAg8QHPIEeyW3OIB4qRWZA", 18),
        ("_RSWgcHPIEeyW3OIB4qRWZA", 8),
        ("_bNLx4HPIEeyW3OIB4qRWZA", 6),
        ("_sB8k8Mn-EeyS2Zr7ZWFrXA", 7),
        ("_1adB8GpbEe2Scdb2k-Fvhg", 17),
        ("_fqzi8BKnEeuBCogvtwwNBw", 42),
        ("_ervhAFIqEeyiRNlyKPJwqw", 44),
        ("_8BMtsIQzEeyxv9w6U6_UQg", 6),
        ("_al3zwKg0EeujRPrkuugYGw", 5),
        ("_1sCb8OSREeulYvEGRaHazg", 5),
        ("_APMboAPhEeynfbzU12yy7w", 11),
        ("_K9160IKBEeyd4IW8P6K-AQ", 14),
        ("_0g-esB4cEe2Jgqeci1tAhA", 1),
        ("_hIt8QKWXEeqh-bahrg4jkA", 18),
        ("_u8lIgLB-EeqP7JXhmLvOsg", 26),
        ("_2SjcgAL8EeuogvvqBpYPnQ", 6),
        ("_KTxZ8KJwEeusg-blS2y7tg", 18),
        ("_ZNrYAKJxEeusg-blS2y7tg", 21),
        ("_mKI_kKZwEeuRO5WMG4dh5w", 2),
        ("_MDoM4AWrEeyIAukYgdUX5A", 11),
        ("_VKPRsIQTEeyxv9w6U6_UQg", 26),
        ("_dpUi4LB8EeqLtsTDMgEHBw", 48),
        ("_gRewkLB_EeqLtsTDMgEHBw", 11),
        ("__dDrANZLEeqiU8uzTY0Puw", 14),
        ("_jGNGMOCUEeu-FsE4WGMncQ", 4),
        ("_Ne8zEAATEeykFulkDFvkrg", 7),
        ("_I0nugeQUEe2jpIKbeHI0hw", 14),
    ],
)
def test_iter_visible(model, diag_uid, num_nodes):
    diag = model.diagrams.by_uuid(diag_uid)
    diagram_elements = sum(
        1 for _ in aird.iter_visible(model._loader, diag._element)
    )

    assert diagram_elements == num_nodes
