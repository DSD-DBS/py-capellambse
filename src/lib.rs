// SPDX-FileCopyrightText: Copyright DB InfraGO AG
// SPDX-License-Identifier: Apache-2.0

use pyo3::prelude::*;

mod exs;

#[pymodule(name = "_compiled")]
fn setup_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(exs::serialize, m)?)?;

    Ok(())
}
