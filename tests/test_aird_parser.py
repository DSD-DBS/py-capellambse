# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

import json

import pytest

import capellambse
from capellambse import aird, diagram, loader

from .conftest import Models  # type: ignore


class TestAIRDBasicFunctionality:
    (test_model,) = Models.aird_parser.glob("*.aird")
    test_diagram = "[LAB] Logical System"

    @pytest.fixture
    def model(self):
        return loader.MelodyLoader(self.test_model)

    @pytest.fixture
    def diagram_under_test(self, model):
        descriptor = next(aird.enumerate_descriptors(model), None)
        assert descriptor is not None
        return aird.parse_diagram(model, descriptor)

    def test_parsing_all_diagrams_does_not_raise_exceptions(
        self, model, caplog
    ):
        del caplog
        num = sum(1 for _ in aird.parse_diagrams(model))
        assert num == 1

    def test_enumerate_descriptors_doesnt_crash_if_there_are_no_diagrams(self):
        model = loader.MelodyLoader(Models.empty)
        for _ in aird.enumerate_descriptors(model):
            pass


def test_airdparser_msm_produces_valid_json_without_error(
    model: capellambse.MelodyModel,
):
    dg = model.diagrams.by_name("[MSM] States of Functional Human Being")
    parsed = aird.parse_diagram(model._loader, dg._element)

    generated_json = diagram.DiagramJSONEncoder(indent=4).encode(parsed)
    json.loads(generated_json)


@pytest.mark.parametrize(
    ("diag_uid", "num_nodes"),
    [
        ("_7Ft7QKrxEeqOgqWuHJrXFA", 34),
        ("_KLGoEKyJEeqCdMaqCWkrKg", 14),
        ("_be95kNYrEeqiU8uzTY0Puw", 11),
        ("_-NU3gV2mEey8erljvkS-pQ", 13),
        ("_KZRQIWA9Eey8erljvkS-pQ", 15),
        ("_jofb8WDdEey8erljvkS-pQ", 5),
        ("_bpuRwWDhEey8erljvkS-pQ", 4),
        ("_OAjYgXPIEeyW3OIB4qRWZA", 18),
        ("_RSYVoXPIEeyW3OIB4qRWZA", 8),
        ("_bNNAAXPIEeyW3OIB4qRWZA", 6),
        ("_sCBdcMn-EeyS2Zr7ZWFrXA", 7),
        ("_1aihhGpbEe2Scdb2k-Fvhg", 18),
        ("_kqj3UF9REe2rko4oG1H6IQ", 5),
        ("_fr69QBKnEeuBCogvtwwNBw", 43),
        ("_erzycVIqEeyiRNlyKPJwqw", 44),
        ("_8BQYEYQzEeyxv9w6U6_UQg", 6),
        ("_L8b8cCoPEe6CTqm4KXEZ8w", 20),
        ("_amKHoKg0EeujRPrkuugYGw", 5),
        ("_APOQ0QPhEeynfbzU12yy7w", 11),
        ("_K-BhAIKBEeyd4IW8P6K-AQ", 14),
        ("_yov6wM-ZEeytxdoVf3xHjA", 7),
        ("_hJD6gaWXEeqh-bahrg4jkA", 18),
        ("_u8_YMLB-EeqP7JXhmLvOsg", 26),
        ("_2TLuoAL8EeuogvvqBpYPnQ", 6),
        ("_KVGPoKJwEeusg-blS2y7tg", 18),
        ("_ZN1JAKJxEeusg-blS2y7tg", 21),
        ("_MDzzEAWrEeyIAukYgdUX5A", 11),
        ("_VKTjIIQTEeyxv9w6U6_UQg", 26),
        ("_dr0dQLB8EeqLtsTDMgEHBw", 48),
        ("_gRrk4bB_EeqLtsTDMgEHBw", 11),
        ("__dKYsdZLEeqiU8uzTY0Puw", 21),
        ("_jGZ6geCUEeu-FsE4WGMncQ", 4),
        ("_NfMDoAATEeykFulkDFvkrg", 8),
    ],
)
def test_iter_visible(model, diag_uid, num_nodes):
    diag = model.diagrams.by_uuid(diag_uid)
    diagram_elements = sum(
        1 for _ in aird.iter_visible(model._loader, diag._element)
    )

    assert diagram_elements == num_nodes
