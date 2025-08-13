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

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "sphinx_autodoc_typehints",
]

nitpicky = True
nitpick_ignore = [
    # in inventory as "py:function"
    ("py:class", "operator.attrgetter"),
    # exposed as `json.JSONEncoder`
    ("py:class", "json.encoder.JSONEncoder"),
    # TODO figure out why sphinx doesn't document these
    ("py:exc", "capellambse.UnsupportedPluginError"),
    ("py:exc", "capellambse.UnsupportedPluginVersionError"),
    ("any", "capellambse.aird.GLOBAL_FILTERS"),
    # Private type hinting helpers
    ("py:class", "_MapFunction"),
    ("py:class", "_NotSpecifiedType"),
    ("py:class", "capellambse.model._descriptors._Specification"),
    # Deprecated ABC
    ("py:class", "capellambse.metamodel.fa._AbstractExchange"),
    ("py:class", "capellambse.metamodel.interaction._CapabilityRelation"),
    ("py:class", "capellambse.metamodel.interaction._EventOperation"),
]
nitpick_ignore_regex = [
    ("py:.*", r"^(?:awesomeversion|yaml)\..*"),
    ("py:.*", r"^(?:.*\.)?_[A-Z]$"),  # Single-letter TypeVars (e.g. _T)
    ("py:.*", r"^(?:.*\.)?(?:_UnspecifiedType|_NOT_SPECIFIED)$"),
    # Super/subclass and "see also" references sometimes break
    ("py:(meth|obj)", r"(?:.*\.)?write_transaction"),
    # Sometimes autodoc_typehints doesn't properly resolve aliases
    ("py:class", r"(?:cabc|etree|m|t|_obj)\..*"),
]


# Add any paths that contain templates here, relative to this directory.
templates_path: list[str] = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = []


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

autodoc_type_aliases = {
    "capellambse.model.common.accessors._NewObject": "capellambse.model.new_object",
}


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
    "svgwrite": ("https://svgwrite.readthedocs.io/en/latest", None),
    "requests": ("https://requests.readthedocs.io/en/latest", None),
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
            "url": "https://github.com/dbinfrago/py-capellambse",
            "html": '<img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHN0cm9rZT0iY3VycmVudENvbG9yIiBmaWxsPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMCIgdmlld0JveD0iMCAwIDE2IDE2Ij48cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik04IDBDMy41OCAwIDAgMy41OCAwIDhjMCAzLjU0IDIuMjkgNi41MyA1LjQ3IDcuNTkuNC4wNy41NS0uMTcuNTUtLjM4IDAtLjE5LS4wMS0uODItLjAxLTEuNDktMi4wMS4zNy0yLjUzLS40OS0yLjY5LS45NC0uMDktLjIzLS40OC0uOTQtLjgyLTEuMTMtLjI4LS4xNS0uNjgtLjUyLS4wMS0uNTMuNjMtLjAxIDEuMDguNTggMS4yMy44Mi43MiAxLjIxIDEuODcuODcgMi4zMy42Ni4wNy0uNTIuMjgtLjg3LjUxLTEuMDctMS43OC0uMi0zLjY0LS44OS0zLjY0LTMuOTUgMC0uODcuMzEtMS41OS44Mi0yLjE1LS4wOC0uMi0uMzYtMS4wMi4wOC0yLjEyIDAgMCAuNjctLjIxIDIuMi44Mi42NC0uMTggMS4zMi0uMjcgMi0uMjcuNjggMCAxLjM2LjA5IDIgLjI3IDEuNTMtMS4wNCAyLjItLjgyIDIuMi0uODIuNDQgMS4xLjE2IDEuOTIuMDggMi4xMi41MS41Ni44MiAxLjI3LjgyIDIuMTUgMCAzLjA3LTEuODcgMy43NS0zLjY1IDMuOTUuMjkuMjUuNTQuNzMuNTQgMS40OCAwIDEuMDctLjAxIDEuOTMtLjAxIDIuMiAwIC4yMS4xNS40Ni41NS4zOEE4LjAxMyA4LjAxMyAwIDAgMCAxNiA4YzAtNC40Mi0zLjU4LTgtOC04eiIvPjwvc3ZnPg=="/>',
            "class": "",
        },
    ],
}
html_short_title = "py-capellambse"
html_show_sourcelink = False

# -- Extra options for Furo theme --------------------------------------------

pygments_style = "tango"
pygments_dark_style = "monokai"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Skip __new__ methods ----------------------------------------------------
# This skips all __new__ methods. They only appear for NamedTuple
# classes, and they don't show any useful information that's not
# documented on the members already anyways.
def skip_dunder_new(app, what, name, obj, skip, options) -> bool:
    del app, obj, options
    return skip or (what == "class" and name == "__new__")


def setup(app):
    app.connect("autodoc-skip-member", skip_dunder_new)
