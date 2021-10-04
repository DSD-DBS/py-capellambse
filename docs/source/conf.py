# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

logger = logging.getLogger(__name__)

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

from setuptools.config import read_configuration

import capellambse

# -- Project information -----------------------------------------------------

config = read_configuration("../../setup.cfg")
project = "Python Capella MBSE Tools"
pypi = "pycapellambse"
author = config["metadata"]["author"]
copyright = "2020, %s" % author
license = config["metadata"]["license"]
install_requirements = config["options"]["install_requires"]
python_requirement = config["options"]["python_requires"]

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
import sphinx_rtd_theme

sys.path.append(os.path.abspath("./_ext"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx_rtd_theme",
    "jinja_in_rst",
    "capellambse.sphinx",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

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
rst_epilog = """
.. |Project| replace:: {project}
.. |Version| replace:: {version}
""".format(
    project=project, version=version
)

# -- Options for auto-doc ----------------------------------------------------
autoclass_content = "class"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": False,
    "collapse_navigation": True,
}
html_short_title = "Python Capella MBSE Tools"
html_logo = "_static/PyCap_logo3.svg"
html_show_sourcelink = False
html_context = {
    "dependencies": install_requirements,
    "py_req": python_requirement,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Options for CapellaMBSE-Sphinx ------------------------------------------
capellambse_model = "../capella-python-api/capella-python-api.aird"
