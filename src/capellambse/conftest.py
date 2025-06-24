# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Test fixtures for capellambse's doctests."""

import pytest

import capellambse
from capellambse import helpers


@pytest.fixture(autouse=True)
def load_test_models(doctest_namespace):
    model = capellambse.loadcli("test-5.0")
    doctest_namespace["model"] = model
    doctest_namespace["loader"] = model._loader


@pytest.fixture(autouse=True)
def deterministic_ids():
    with helpers.deterministic_ids():
        yield
