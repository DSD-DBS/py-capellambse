# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import capellambse.model as m

from . import capellacore, capellamodeller
from . import namespaces as ns

NS = ns.SHARED_MODEL


class SharedPkg(capellacore.ReuseableStructure, capellamodeller.ModelRoot):
    data_pkg = m.Containment["information.DataPkg"](
        "ownedDataPkg", (ns.INFORMATION, "DataPkg")
    )
    generic_pkg = m.Containment["GenericPkg"](
        "ownedGenericPkg", (NS, "GenericPkg")
    )


class GenericPkg(capellacore.Structure):
    packages = m.Containment["GenericPkg"](
        "subGenericPkgs", (NS, "GenericPkg")
    )
    capella_elements = m.Containment["capellacore.CapellaElement"](
        "capellaElements", (ns.CAPELLACORE, "CapellaElement")
    )


from . import information  # noqa: F401
