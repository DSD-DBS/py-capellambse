..
   SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
   SPDX-License-Identifier: Apache-2.0

Python-Capellambse
==================

.. image:: https://img.shields.io/pypi/pyversions/capellambse
   :target: https://pypi.org/project/capellambse/
   :alt: PyPI - Python Version

.. image:: https://github.com/DSD-DBS/py-capellambse/actions/workflows/build-test-publish.yml/badge.svg
  :target: https://github.com/DSD-DBS/py-capellambse/actions/workflows/build-test-publish.yml/badge.svg

.. image:: https://github.com/DSD-DBS/py-capellambse/actions/workflows/lint.yml/badge.svg
  :target: https://github.com/DSD-DBS/py-capellambse/actions/workflows/lint.yml/badge.svg

.. image:: https://img.shields.io/github/license/dsd-dbs/py-capellambse
   :target: LICENSES/Apache-2.0.txt
   :alt: License

.. image:: https://api.reuse.software/badge/github.com/DSD-DBS/py-capellambse
   :target: https://api.reuse.software/info/github.com/DSD-DBS/py-capellambse
   :alt: REUSE status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
   :target: https://pycqa.github.io/isort/

*A Python 3 headless implementation of the Capella modeling tool*

Intro
-----

``capellambse`` allows you reading and writing Capella models from Python
without Java or the `Capella tool`__ on any (reasonable) platform. We wanted to
"talk" to Capella models from Python, but without any Java on the way. We
thought this project will help individuals and organisations getting through
the MBSE adoption journey with Capella faster and so we made it public and
open-source.

__ https://www.eclipse.org/capella/

With ``capellambse`` you can access all (or almost all) Capella model elements,
and render diagrams as SVG and PNG. We made it for automation of Systems
Engineering work, so it integrates nicely into most CI/CD toolchains. We also
found it at the core of our artifact generation pipelines (model to documents,
model to SW interfaces).

The library works with `PVMT`__ and `Requirements`__ extensions without any
additional efforts.

__ https://www.eclipse.org/capella/addons.html
__ https://github.com/eclipse/capella-requirements-vp

It started as a basic library somewhere mid 2019. Since then it was
re-architected a few times and now has a full read/write capability for most of
the present Capella ontology. We are continuously improving the API
(introducing shortcuts), increasing the meta-model coverage and have more
engineering automations and improvements in the pipeline to share.

Documentation and examples
--------------------------

The library is designed to be easy to use and discover, especially in an
interactive environment such as JupyterLab. Additionally, `API documentation`__
is automatically generated and published whenever new features and bug fixes
are added.

__ https://dsd-dbs.github.io/py-capellambse/

You are encouraged to explore our test models and demo notebooks. Click on the
button below to launch a `Jupyter notebook server`_ on the public myBinder
service, and get started in seconds:

.. image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/DSD-DBS/py-capellambse/HEAD?labpath=docs%2Fsource%2Fexamples%2F01%20Introduction.ipynb

*Warning:* `Do not enter confidential information`__, such as passwords for
non-public models, into a notebook hosted on myBinder. If you want to try out
``capellambse`` with those models, please `install and run`__ it in a local,
trusted environment!

__ https://github.com/alan-turing-institute/the-turing-way/blob/b36c3ac1c78acbbe18441beaa89514544ed12021/workshops/boost-research-reproducibility-binder/workshop-presentations/zero-to-binder-python.md#private-files
__ #installation

The ``docs/source/examples`` directory contains several hands-on example
notebooks that you can immediately run and start experimenting with. Below is a
short summary of each notebook's goal. If you are in the JupyterLab
environment, you can click the notebook names to directly open them in a new
lab tab. On Github, you will be shown a statically rendered preview of the
notebook.

- `01 Introduction.ipynb`__ provides a high-level overview of the library
  features. It visualizes examples like a Component - Function allocation table
  by leveraging Jupyter's and IPython's rich display functionality.

  __ https://dsd-dbs.github.io/py-capellambse/examples/01%20Introduction.html

- `02 Intro to Physical Architecture.ipynb`__ explores some more advanced
  concepts on the example of the Physical Architecture Layer. It shows how to
  derive tabular data, like a Bill of Materials or a Software to Hardware
  allocation table, by using ``pandas`` dataframes.

  __ https://dsd-dbs.github.io/py-capellambse/examples/02%20Intro%20to%20Physical%20Architecture%20API.html

- `03 Data Values.ipynb`__ shows how the API can be used to explore classes,
  class instances and other objects related to data modeling.

  __ https://dsd-dbs.github.io/py-capellambse/examples/03%20Data%20Values.html

- `04 Intro to Jinja templating.ipynb`__ demonstrates how to effectively
  combine ``capellambse`` with the powerful Jinja__ templating engine. This
  enables the creation of all sorts of model-derived documents and artifacts,
  including interactive web pages, PDF documents and any other textual
  representations of your models.

  __ https://dsd-dbs.github.io/py-capellambse/examples/04%20Intro%20to%20Jinja%20templating.html
  __ https://palletsprojects.com/p/jinja/

- `05 Introduction to Libraries.ipynb`__ shows how to use Capella Library
  Projects within capellambse. In this example you'll learn how the API can be
  used to open a project that is based on a library and find objects in both
  models.

  __ https://dsd-dbs.github.io/py-capellambse/examples/05%20Introduction%20to%20Libraries.html

- `06 Introduction to Requirement access and management.ipynb`__ shows how the
  API can be used to work with requirements objects, introduced by the Capella
  `Requirements Viewpoint`__. In this example you'll see how to find
  requirements in the model, see which objects requirements are linked / traced
  to and even export requirements to Excel or ReqIF formats.

  __ https://dsd-dbs.github.io/py-capellambse/examples/06%20Introduction%20to%20Requirement%20access%20and%20management.html
  __ https://www.eclipse.org/capella/addons.html

- `07 Code Generation.ipynb`__ shows how to generate code from class diagrams.
  In particular, we focus on Interface Descriptive Languages with concrete
  examples for ``Class`` to `ROS2 IDL`__ and Google `Protocol Buffers`__. We
  also show how simple Python stubs could be generated given a ``Class``
  object.

  __ https://dsd-dbs.github.io/py-capellambse/examples/07%20Code%20Generation.html
  __ https://docs.ros.org/en/rolling/Concepts/About-ROS-Interfaces.html
  __ https://developers.google.com/protocol-buffers

We are constantly working on improving everything shown here, as well as adding
even more useful functionality and helpful demos. If you have any new ideas
that were not mentioned yet, `don't hesitate to contribute`__!

__ CONTRIBUTING.rst

Installation
------------

In order to use private models that are not publicly available, please install
and use ``capellambse`` in a local, trusted environment.

You can install the latest released version directly from PyPI.

.. code::

    pip install capellambse

To set up a development environment, clone the project and install it into a
virtual environment.

.. code::

    git clone https://github.com/DSD-DBS/py-capellambse
    cd capellambse
    python -m venv .venv

    source .venv/bin/activate.sh  # for Linux / Mac
    .venv\Scripts\activate  # for Windows

    pip install -U pip pre-commit
    pip install -e '.[docs,test]'
    pre-commit install

We recommend developing within a local `Jupyter notebook server`_ environment.
In order to install and run it in the same virtual environment, execute the
following additional commands:

.. code::

     pip install jupyter capellambse
     cd docs/source/examples
     jupyter-notebook

If your browser did not open automatically, follow the instructions in the
terminal to start it manually.

Once in the browser, simply click on the `01 Introduction.ipynb`__ notebook to
start!

__ docs/source/examples/01%20Introduction.ipynb

Current limitations
-------------------

We are continuously improving coverage of Capella onthology with our
`high-level API`__ (the current coverage map is available `here`__), however it
is still incomplete. It covers most of the commonly used paths but when you
need to get to an ontology element that isnt covered yet you may do so by using
the `low-level API`__.

__ #TODO
__ #TODO
__ https://dsd-dbs.github.io/py-capellambse/development/low-level-api.html

Also, as we started in mid 2019 and there was no such thing as
`Python4Capella`__ yet, we are not API compatible with that project. However,
we intend to add API compatibility with Python4Capella in later releases.

__ https://github.com/labs4capella/python4capella

The generated diagrams are currently not persisted in ``.aird`` files, and
currently there is no plan to implement this. If there is a genuine usecase for
that we may re-consider it - feel free to create an issue or add comments to an
existing one.

Render diagrams in untrusted jupyter notebooks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The SVG format relies on a stylesheet, however in untrusted notebooks any
stylesheets are stripped. As a workaround we support the PNG format. For this
the `cairosvg`__ library is needed which requires the following additional
setup steps on windows:

__ https://pypi.org/project/CairoSVG/

- Download and execute the `latest GTK installer`__.

  __ https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/tag/2022-01-04

- Reboot to add the path to the installed compiled libraries into your system
  environment PATH

Contributing
------------

We'd love to see your bug reports and improvement suggestions! Please take a
look at our `guidelines for contributors <CONTRIBUTING.rst>`__ for details.

Licenses
--------

This project is compliant with the `REUSE Specification Version 3.0`__.

__ https://git.fsfe.org/reuse/docs/src/commit/d173a27231a36e1a2a3af07421f5e557ae0fec46/spec.md

Copyright DB Netz AG, licensed under Apache 2.0 (see full text in
`<LICENSES/Apache-2.0.txt>`__)

Dot-files are licensed under CC0-1.0 (see full text in
`<LICENSES/CC0-1.0.txt>`__)

To provide the same look and feel across platforms, we distribute our library
bundled with the OpenSans font (``capellambse/OpenSans-Regular.ttf``). The
OpenSans font is Copyright 2020 `The Open Sans Project Authors`__, licensed
under OFL-1.1 (see full text in `<LICENSES/OFL-1.1.txt>`__).

__ https://github.com/googlefonts/opensans

.. _Jupyter notebook server: https://jupyter.org/
