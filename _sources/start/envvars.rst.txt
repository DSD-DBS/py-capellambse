..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

Environment variables affecting |project|
=========================================

This page provides an overview over the environment variables that |project|
understands, and how they affect regular operation.

- ``GIT_USERNAME`` and ``GIT_PASSWORD`` can be used to provide default
  credentials to the Git file handler. If set, the file handler overrides
  ``GIT_ASKPASS`` when interacting with git in order to forward these
  credentials.

- ``CAPELLAMBSE_GLART_MAX_JOBS`` determines the maximum number of CI jobs that
  the Gitlab Artifacts file handler will search through when looking for the
  last successful job with a given name. It can be used to limit the search
  radius to reduce server load, or to extend it to find older jobs as well.

  It defaults to 1000, which results in up to 5 requests to the Gitlab server.
  The limit can be disabled by setting the variable to 0.

- ``CI_SERVER_URL``, ``CI_PROJECT_ID``, ``CI_DEFAULT_BRANCH`` and
  ``CI_JOB_TOKEN`` are used by the Gitlab Artifacts file handler to fill in the
  hostname, the "project" and "branch" parameters, and the access token,
  respectively, if they were not passed explicitly. These variables are
  automatically set by Gitlab CI/CD runners.

- ``CREDENTIALS_DIRECTORY`` is used to find files containing tokens or other
  types of credentials, if no absolute path is given.

- ``CAPELLAMBSE_PNG_SCALE`` can be used to upscale diagrams before rendering
  them as PNG.

- ``TERM`` is used to determine whether the terminal supports PNG display, in
  order to preview diagrams in the REPL.

- ``CAPELLAMBSE_UUID_SEED`` sets a seed for the internal pseudo-random number
  generator for UUIDs. This is used when inserting new elements into a model,
  either directly or indirectly by adding elements to ``Allocation`` relations.
  If unset or empty, a randomized seed will be used.

  This may be helpful when debugging CI runs or other automations. Note however
  that the code creating the objects must then also be deterministic (i.e.
  create and insert  the same objects in the same order every time), which
  usually rules out any potentially multi-threaded applications.

  Be aware that the generated UUIDs will still be checked against the model
  that they will be used in, and if duplications are detected, the PRNG is
  queried again. This may lead to different UUIDs than expected if the same
  seed has been used before in a model.

Debugging helpers
-----------------

- ``AIRD_NOSNAP``, if defined, disables point snapping while parsing AIRD data.
  This causes the positioning data from the AIRD file to be used as-is, which
  leads to very broken layouts.

- ``CAPELLAMBSE_SVG_DEBUG``, if defined, causes the built-in SVG renderer to
  draw additional red markers to indicate various reference positions.

Experimental features
---------------------

- ``CAPELLAMBSE_XHTML``: If set to "1", content from attributes that contain
  HTML markup will be cleaned up and made XHTML compliant before it is returned
  when using the high-level model API. This means that content read with
  capellambse no longer fully matches what is stored in the model.

  Considered experimental, as it may be changed or removed without a preceding
  deprecation period.

- ``CAPELLAMBSE_EXPERIMENTAL_CROP_SVG_DIAGRAM_CACHE_VIEWPORT`` can be set to
  "1" to recalculate the viewport of SVG files exported by Capella. This can be
  used to reduce white borders in some cases.

  Experimental because not all possible elements are currently handled, and
  because the bounding box calculations for text objects don't fully match what
  Capella or some other SVG viewers use.
