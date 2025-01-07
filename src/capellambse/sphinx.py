# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Sphinx extension for capellambse.

This extension is be used to display diagrams in Sphinx-generated
documentation.

Usage
-----

To render a diagram in your documentation, simply define a diagram directive.

.. code::

    .. diagram:: [CDB] BaseLayer ORM
        :alt: Base layer diagram
        :height: 480
        :width: 640
        :align: center -- can be left/right/center

The options are optional.

Configuration
-------------

To enable this extension, add it to your list of extensions in Sphinx'
``conf.py``.

.. code:: python

    # conf.py

    extensions = [
        ...,
        'capellambse.sphinx',
    ]

The following configuration variables are understood by this extension:

* ``capellambse_model``: Path to the Capella model.

  Set this variable to the root ``.aird`` file of the model you want to
  use in the documentation. The path must be relative to Sphinx' current
  working directory, which should be the directory containing the
  ``conf.py`` file.

Known limitations
-----------------

* The extension currently does not detect changes to the model, nor does
  it track which source files are using it. This means that, after
  changing the model, you need to force a full rebuild of all pages by
  passing ``--fresh-env`` to Sphinx' build command.
"""

from __future__ import annotations

import pathlib
import typing as t

import sphinx.util.docutils
from docutils import nodes
from docutils.parsers import rst

import capellambse

if t.TYPE_CHECKING:
    import sphinx.application
    import sphinx.environment


def setup(app: sphinx.application.Sphinx) -> dict[str, t.Any]:
    """Set up the extensions.

    Called by Sphinx if the extension is configured in ``conf.py``.
    """
    app.add_config_value(
        "capellambse_model", "../model/Documentation.aird", "html"
    )
    app.add_directive("diagram", DiagramDirective)

    app.connect("env-before-read-docs", load_model)
    app.connect("env-updated", unload_model)

    return {
        "version": capellambse.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def load_model(
    app: sphinx.application.Sphinx,
    env: sphinx.environment.BuildEnvironment,
    *_: t.Any,
) -> None:
    """Load the model."""
    if app.confdir is None:
        raise ValueError("Cannot load model: No confdir defined for Sphinx")

    env.capellambse_loaded_model = (  # type: ignore[attr-defined]
        capellambse.MelodyModel(
            pathlib.Path(app.confdir, app.config.capellambse_model)
        )
    )


def unload_model(_: t.Any, env: sphinx.environment.BuildEnvironment) -> None:
    """Unload the model.

    The LXML tree cannot be pickled together with the rest of the build
    environment. This means we need to unload the model again after
    processing the source files.
    """
    if hasattr(env, "capellambse_loaded_model"):
        del env.capellambse_loaded_model


class DiagramDirective(sphinx.util.docutils.SphinxDirective):
    """The ``diagram`` reST directive."""

    has_content = True
    required_arguments = 1
    final_argument_whitespace = True
    option_spec: t.ClassVar = {
        "alt": rst.directives.unchanged,
        "height": rst.directives.nonnegative_int,
        "width": rst.directives.nonnegative_int,
        "align": lambda arg: rst.directives.choice(
            arg, ("left", "center", "right")
        ),
    }

    def run(self) -> list[nodes.Node]:
        name = self.arguments[0]
        if not hasattr(self.env, "capellambse_loaded_model"):
            raise self.error(
                f"Cannot show diagram {name!r}: No model configured"
            )

        model = self.env.capellambse_loaded_model
        try:
            diagram = model.diagrams.by_name(name)
        except KeyError as error:
            raise self.error(
                f"Cannot find diagram {name!r} in the configured model"
            ) from error

        uri = diagram.as_datauri_svg
        return [
            nodes.image(rawsource=self.block_text, uri=uri, **self.options)
        ]
