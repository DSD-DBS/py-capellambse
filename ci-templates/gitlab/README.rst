..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
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
filtered projects from the main project.

__ https://github.com/eclipse/capella-filtering

This can also be combined with pre-rendering cached diagram images for each
derived model.

Add the following code to your ``.gitlab-ci.yml``:

.. code:: yaml

  include:
    - remote: https://raw.githubusercontent.com/DSD-DBS/py-capellambse/${CAPELLAMBSE_REVISION}/ci-templates/gitlab/filter-derive.yml

  variables:
    ENTRYPOINT: test/test.aird # Entry point to the .aird file of the model (relative from root level of the repository)

  derive:
    # Use the following line to only derive filtered models.
    extends: .derive
    # Use this instead if you also want to generate diagrams after derivation.
    extends: .derive-and-generate-diagrams

    # If you want to change any settings (see filter-derive.yml),
    # add a variables section, like so:
    variables:
      CAPELLA_DOCKERIMAGE: some/image/name:{VERSION}
      DERIVE_RESULTS: 01234567-89ab-cdef-0123-456789abcdef;My Result 1;My Result 2

If your Gitlab runner does not support Docker-in-Docker, you can still use this
template, but you'll have to specify slightly different options. In this case,
the Capella image you use must have a Python interpreter installed.

.. code:: yaml

  derive:
    extends: .derive # As above
    image:
      name: some/image/name:6.0.0 # You have to pre-select the correct version manually
      entrypoint: [""]
    variables:
      CAPELLA_EXECUTABLE: /opt/capella/capella-in-xvfb.sh
