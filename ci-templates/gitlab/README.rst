..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

Gitlab CI templates
===================

Currently, we provide the following Gitlab CI/CD templates:

- `Model badge`_: Produces and pushes a complexity model badge.

Model badge
-----------
Please add the following section to your ``.gitlab-ci.yml``:

.. code:: yaml

  include:
    - remote: https://raw.githubusercontent.com/DSD-DBS/py-capellambse/${CAPELLAMBSE_REVISION}/ci-templates/gitlab/model-badge.yml

  variables:
    ENTRYPOINT: test/test.aird # Entry point to the .aird file of the model (relative from root level of the repository)

  # The following section is only needed if you want to change the output filename or commit message
  generate-model-badge:
    variables:
      OUTPUT_FILE: model-complexity-badge.svg # Change the filename here
      COMMIT_MSG: "docs: Add/Modify model complexity badge" # Change the commit message here

In addition, you have to add the following environment variables on Gitlab project or group level.
Make sure to enable the "Expand variable reference" flag.

- ``CAPELLAMBSE_REVISION``: Revision of this Github repository
- ``GIT_USERNAME`` and ``GIT_PASSWORD``: Username and password, used to push the model complexity badge back to the repository.
  If using an access token, the token must have the ``write_repository`` scope for the repository, where the Gitlab CI template is included.

For more information, please refer to this template: `Gitlab CI template <./model-badge.yml>`_.
