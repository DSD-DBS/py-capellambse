..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

Github CI templates
===================

Currently, we provide the following Github Action:

- `Model badge`_: Produces and pushes a complexity model badge.

Model badge
-----------

To use this action, add it as a step to a job in your workflows:

.. code:: yaml

   on: [push]
   jobs:
     generate-model-badge:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: DSD-DBS/py-capellambse/ci-templates/github/model-complexity-badge@master

This is the minimal configuration, which will produce a badge with a name of
``model-complexity-badge.svg``, push it back to the repository and upload it as
workflow artifact. The model will be searched in the runner's working
directory by default.

This behavior is configurable via several options specified in the ``with:``
section. For details about those options, please refer to the ``inputs:``
section in the `Model Badge Action definition
<./model-complexity-badge/action.yml>`_.
