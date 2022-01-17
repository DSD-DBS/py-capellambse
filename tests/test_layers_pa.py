# pylint: disable=no-self-use
import typing as t

import capellambse.model.common as c
from capellambse import MelodyModel


def test_pa_has_all_physical_paths(model: MelodyModel):
    expected_path = model.by_uuid("42c5ffb3-29b3-4580-a061-8f76833a3d37")
    assert expected_path in model.pa.all_physical_paths


def test_pa_has_all_component_exchanges(model: MelodyModel):
    expected_exchange = model.by_uuid("3aa006b1-f954-4e8f-a4e9-2e9cd38555de")
    assert expected_exchange in model.pa.all_component_exchanges
