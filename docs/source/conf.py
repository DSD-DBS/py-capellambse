# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

import capellambse

# -- Project information -----------------------------------------------------

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
with open("../../pyproject.toml", "rb") as f:
    _metadata = tomllib.load(f)["project"]

project = "py-capellambse"
pypi = "capellambse"
author = _metadata["authors"][0]["name"]
copyright = f"{author} and the {_metadata['name']} contributors"
license = _metadata["license"]["text"]
install_requirements = _metadata["dependencies"]
python_requirement = _metadata["requires-python"]

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "capellambse.sphinx",
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_argparse_cli",
]

# Enable nitpicky mode
nitpicky = True
nitpick_ignore = [
    ("any", "capellambse.aird.GLOBAL_FILTERS"),
    ("py:class", "_MapFunction"),
    ("py:class", "_T"),
    ("py:class", "T"),
    ("py:class", "c.Accessor"),
    ("py:class", "c.AttributeProperty"),
    ("py:class", "c.AttrProxyAccessor"),
    ("py:class", "c.GenericElement"),
    ("py:class", "cabc.Mapping"),
    ("py:class", "cabc.Sequence"),
    ("py:class", "cabc.Set"),
    ("py:class", "capellambse.filehandler.abc._F"),
    ("py:class", "capellambse.helpers.UUIDString"),
    ("py:class", "capellambse.helpers._T"),
    ("py:class", "capellambse.loader.exs._HasWrite"),
    ("py:class", "capellambse.model.common.T"),
    ("py:class", "capellambse.model.common.U"),
    ("py:class", "capellambse.model.common.accessors._NewObject"),
    ("py:class", "capellambse.model.common.accessors._Specification"),
    ("py:class", "capellambse.model.modeltypes._StringyEnumMixin"),
    ("py:class", "json.encoder.JSONEncoder"),
    ("py:class", "operator.attrgetter"),
    ("py:class", "rq.AbstractRequirementsRelation"),
    ("py:class", "t.Any"),
    ("py:class", "yaml.dumper.SafeDumper"),
    ("py:class", "yaml.loader.SafeLoader"),
    ("py:class", "yaml.nodes.Node"),
    ("py:exc", "capellambse.UnsupportedPluginError"),
    ("py:exc", "capellambse.UnsupportedPluginVersionError"),
    ("py:meth", "fail"),
    ("py:meth", "write_transaction"),
    ("py:obj", "capellambse.filehandler.abc._F"),
    (
        "py:obj",
        "capellambse.filehandler.localfilehandler"
        ".LocalFileHandler.write_transaction",
    ),
    ("py:obj", "capellambse.model.common.T"),
    ("py:obj", "capellambse.model.common.U"),
]


# Add any paths that contain templates here, relative to this directory.
# templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude_patterns = []


# -- General information about the project -----------------------------------

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# The full version, including alpha/beta/rc tags.
version = capellambse.__version__
rst_epilog = f"""
.. |Project| replace:: {project}
.. |Version| replace:: {version}
"""


# -- Options for auto-doc ----------------------------------------------------
autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_typehints = "description"


# -- Options for napoleon ----------------------------------------------------
napoleon_custom_sections = ["Transaction arguments", "Well-known arguments"]
napoleon_google_docstring = False
napoleon_include_init_with_doc = True


# -- Options for Intersphinx output ------------------------------------------
intersphinx_mapping = {
    "click": ("https://click.palletsprojects.com/en/latest", None),
    "lxml": ("https://lxml.de/apidoc/", None),
    "markupsafe": ("https://markupsafe.palletsprojects.com/en/2.1.x", None),
    "python": ("https://docs.python.org/3", None),
    "svgwrite": ("https://svgwrite.readthedocs.io/en/latest/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "PIL": ("https://pillow.readthedocs.io/en/stable", None),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages. See the documentation
# for a list of builtin themes.

html_theme = "furo"
html_theme_options = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/DSD-DBS/py-capellambse",
            "html": '<img src="/_static/img/github-logo.svg"/>',
            "class": "",
        },
    ],
}
html_short_title = "py-capellambse"
html_show_sourcelink = False
html_context = {
    "dependencies": install_requirements,
    "py_req": python_requirement,
}

# -- Extra options for Furo theme --------------------------------------------

pygments_style = "tango"
pygments_dark_style = "monokai"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Options for CapellaMBSE-Sphinx ------------------------------------------
capellambse_model = "../capella-python-api/capella-python-api.aird"


# -- Skip __new__ methods ----------------------------------------------------
# This skips all __new__ methods. They only appear for NamedTuple
# classes, and they don't show any useful information that's not
# documented on the members already anyways.
def skip_dunder_new(app, what, name, obj, skip, options) -> bool:
    del app, obj, options
    return skip or (what == "class" and name == "__new__")


def setup(app):
    app.connect("autodoc-skip-member", skip_dunder_new)
