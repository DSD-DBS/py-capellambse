// SPDX-FileCopyrightText: Copyright DB InfraGO AG
// SPDX-License-Identifier: Apache-2.0

use pyo3::prelude::*;

#[pymodule(name = "_compiled")]
fn setup_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    Ok(())
}
