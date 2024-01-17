..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

Gitlab CI templates
===================

Currently, we provide the following Gitlab CI/CD templates:

- `Model badge`_: Produces and pushes a complexity model badge.
- `Filtered project derivation`_: Derives filtered projects, and optionally pre-renders diagrams for them.

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

Filtered project derivation
---------------------------

If you use the `Capella Filtering extension`__, you can automatically derive
filtered projects from the main project. The derived projects are stored as
Gitlab job artifacts, and can optionally be pushed to separate branches.


__ https://github.com/eclipse/capella-filtering

Add the following code to your ``.gitlab-ci.yml``:

.. code:: yaml

  include:
    - remote: https://raw.githubusercontent.com/DSD-DBS/py-capellambse/${CAPELLAMBSE_REVISION}/ci-templates/gitlab/filter-derive.yml

  variables:
    CAPELLA_VERSION: 6.0.0 # Semantic Capella version
    ENTRYPOINT: test/test.aird # Entry point to the .aird file of the model (relative from root level of the repository)
    CAPELLAMBSE_REVISION: release-0.5 # Set the capellambse revision. Defaults to release-0.5.

  derive:
    # If you want to change any settings (see filter-derive.yml),
    # add a variables section, like so:
    variables:

      # Push derived model to individual branches.
      # The branch name is 'derived/<derived-project-name>'.
      # Defaults to 1, set it to 0 if pushing in separate branches is not wanted.
      PUSH_DERIVED_MODELS: 1

      DERIVE_RESULTS: 01234567-89ab-cdef-0123-456789abcdef;My Result 1;My Result 2
