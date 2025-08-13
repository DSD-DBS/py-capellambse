<!--
 ~ SPDX-FileCopyrightText: Copyright DB InfraGO AG
 ~ SPDX-License-Identifier: Apache-2.0
 -->

Python-Capellambse
==================

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/capellambse)
![Code QA](https://github.com/dbinfrago/py-capellambse/actions/workflows/code-qa.yml/badge.svg)
![License: Apache-2.0](https://img.shields.io/github/license/dbinfrago/py-capellambse)
![REUSE status](https://api.reuse.software/badge/github.com/dbinfrago/py-capellambse)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

*A Python 3 headless implementation of the Capella modeling tool*

Intro
-----

`capellambse` allows you reading and writing Capella models from Python without
Java or the [Capella tool](https://www.eclipse.org/capella/) on any
(reasonable) platform. We wanted to "talk" to Capella models from Python, but
without any Java on the way. We thought this project will help individuals and
organisations getting through the MBSE adoption journey with Capella faster and
so we made it public and open-source.

With `capellambse` you can access all (or almost all) Capella model elements,
and render diagrams as SVG and PNG. We made it for automation of Systems
Engineering work, so it integrates nicely into most CI/CD toolchains. We also
found it at the core of our artifact generation pipelines (model to documents,
model to SW interfaces).

The library works with [PVMT](https://www.eclipse.org/capella/addons.html) and
[Requirements](https://github.com/eclipse/capella-requirements-vp) extensions
without any additional efforts.

It started as a basic library somewhere mid 2019. Since then it was
re-architected a few times and now has a full read/write capability for most of
the present Capella ontology. We are continuously improving the API
(introducing shortcuts), increasing the meta-model coverage and have more
engineering automations and improvements in the pipeline to share.

Related projects
----------------

- [`capellambse-context-diagrams`](https://github.com/dbinfrago/capellambse-context-diagrams)
  — A capellambse extension that visualizes the context of Capella objects, and
  exposes it on element attributes like `.context_diagram`, `.tree_view`, etc.

- [`capella-diff-tools`](https://github.com/dbinfrago/capella-diff-tools) — A set
  of tools to compare Capella models.

- [`capella-polarion`](https://github.com/dbinfrago/capella-polarion/) —
  Synchronize information from the Capella model into a
  [Polarion](https://plm.sw.siemens.com/de-DE/polarion/) project

- [`capella-ros-tools`](https://github.com/dbinfrago/capella-ros-tools) — Import
  and export ROS `*.msg` files to/from Capella models, or transform `*.msg`
  files into a declarative YAML file.

Did you make something cool that is using or extending capellambse? [Tell us
about it](https://github.com/dbinfrago/py-capellambse/issues), so we can add it
to this list!

Documentation and examples
--------------------------

The library is designed to be easy to use and discover, especially in an
interactive environment such as JupyterLab. Additionally, [API
documentation](https://dbinfrago.github.io/py-capellambse/) is automatically
generated and published whenever new features and bug fixes are added.

You are encouraged to explore our test models and demo notebooks. Click on the
button below to launch a [Jupyter notebook server] on the public myBinder
service, and get started in seconds:

[![myBinder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/dbinfrago/py-capellambse/HEAD?labpath=docs%2Fsource%2Fexamples%2F01%20Introduction.ipynb)

*Warning:* [Do not enter confidential
information](https://github.com/alan-turing-institute/the-turing-way/blob/b36c3ac1c78acbbe18441beaa89514544ed12021/workshops/boost-research-reproducibility-binder/workshop-presentations/zero-to-binder-python.md#private-files),
such as passwords for non-public models, into a notebook hosted on myBinder. If
you want to try out `capellambse` with those models, please [install and
run](#installation) it in a local, trusted environment!

The `docs/source/examples` directory contains several hands-on example
notebooks that you can immediately run and start experimenting with. Below is a
short summary of each notebook's goal. If you are in the JupyterLab
environment, you can click the notebook names to directly open them in a new
lab tab. On Github, you will be shown a statically rendered preview of the
notebook.

- [01
  Introduction.ipynb](https://dbinfrago.github.io/py-capellambse/examples/01%20Introduction.html)
  provides a high-level overview of the library features. It visualizes
  examples like a Component - Function allocation table by leveraging Jupyter's
  and IPython's rich display functionality.

- [02 Intro to Physical
  Architecture.ipynb](https://dbinfrago.github.io/py-capellambse/examples/02%20Intro%20to%20Physical%20Architecture%20API.html)
  explores some more advanced concepts on the example of the Physical
  Architecture Layer. It shows how to derive tabular data, like a Bill of
  Materials or a Software to Hardware allocation table, by using `pandas`
  dataframes.

- [03 Data
  Values.ipynb](https://dbinfrago.github.io/py-capellambse/examples/03%20Data%20Values.html)
  shows how the API can be used to explore classes, class instances and other
  objects related to data modeling.

- [04 Intro to Jinja
  templating.ipynb](https://dbinfrago.github.io/py-capellambse/examples/04%20Intro%20to%20Jinja%20templating.html)
  demonstrates how to effectively combine `capellambse` with the powerful
  [Jinja](https://palletsprojects.com/p/jinja/) templating engine. This enables
  the creation of all sorts of model-derived documents and artifacts, including
  interactive web pages, PDF documents and any other textual representations of
  your models.

- [05 Introduction to
  Libraries.ipynb](https://dbinfrago.github.io/py-capellambse/examples/05%20Introduction%20to%20Libraries.html)
  shows how to use Capella Library Projects within capellambse. In this example
  you'll learn how the API can be used to open a project that is based on a
  library and find objects in both models.

- [06 Introduction to Requirement access and
  management.ipynb](https://dbinfrago.github.io/py-capellambse/examples/06%20Introduction%20to%20Requirement%20access%20and%20management.html)
  shows how the API can be used to work with requirements objects, introduced
  by the Capella [Requirements
  Viewpoint](https://www.eclipse.org/capella/addons.html). In this example
  you'll see how to find requirements in the model, see which objects
  requirements are linked / traced to and even export requirements to Excel or
  ReqIF formats.

- [07 Code
  Generation.ipynb](https://dbinfrago.github.io/py-capellambse/examples/07%20Code%20Generation.html)
  shows how to generate code from class diagrams. In particular, we focus on
  Interface Descriptive Languages with concrete examples for `Class` to [ROS2
  IDL](https://docs.ros.org/en/rolling/Concepts/About-ROS-Interfaces.html) and
  Google [Protocol Buffers](https://developers.google.com/protocol-buffers). We
  also show how simple Python stubs could be generated given a `Class`
  object.

- [08 Property
  Values.ipynb](https://dbinfrago.github.io/py-capellambse/examples/08%20Property%20Values.html)
  shows how to access property values and property value groups, as well as the
  [Property Value Management (PVMT)](https://eclipse.dev/capella/addons.html)
  extension.

- [09 Context
  Diagrams.ipynb](https://dbinfrago.github.io/py-capellambse/examples/09%20Context%20Diagrams.html)
  shows the [capellambse-context-diagrams
  extension](https://capellambse-context-diagrams.readthedocs.io/) that
  visualizes contexts of Capella objects. The extension is external to the
  capellambse library and needs to be installed separately.

- [10 Declarative
  Modeling.ipynb](https://dbinfrago.github.io/py-capellambse/examples/10%20Declarative%20Modeling.html)
  demonstrates a basic application of the declarative approach to modeling on a
  coffee machine example.

- [11 Complexity
  Assessment.ipynb](https://dbinfrago.github.io/py-capellambse/examples/11%20Complexity%20Assessment.html)
  quickly demonstrates how to use and view the model complexity badge for a
  Capella model.

We are constantly working on improving everything shown here, as well as adding
even more useful functionality and helpful demos. If you have any new ideas
that were not mentioned yet, [don't hesitate to contribute](CONTRIBUTING.md)!

Installation
------------

In order to use private models that are not publicly available, please install
and use `capellambse` in a local, trusted environment.

You can install the latest released version directly from PyPI.

```bash
pip install capellambse
```

On supported platforms, the downloaded wheel includes an optional native
module, which provides faster implementations of some functions. Other
platforms will fall back to a pure Python wheel without this speedup. To build
the native module, a Rust compiler is required.

Development
-----------

For details on how to set up a local development environment, please refer to
the [CONTRIBUTING guide](CONTRIBUTING.md).

Current limitations
-------------------

As we started in mid 2019 and there was no such thing as
[Python4Capella](https://github.com/labs4capella/python4capella) yet, we are
not API compatible with that project.

The generated diagrams are currently not persisted in `.aird` files, and
currently there is no plan to implement this. If there is a genuine usecase for
that we may re-consider it - feel free to create an issue or add comments to an
existing one.

Contributing
------------

We'd love to see your bug reports and improvement suggestions! Please take a
look at our [guidelines for contributors](CONTRIBUTING.md) for details.

Licenses
--------

This project is compliant with the [REUSE Specification Version
3.0](https://git.fsfe.org/reuse/docs/src/commit/d173a27231a36e1a2a3af07421f5e557ae0fec46/spec.md).

Copyright DB InfraGO AG, licensed under Apache 2.0 (see full text in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt))

Dot-files are licensed under CC0-1.0 (see full text in
[LICENSES/CC0-1.0.txt](LICENSES/CC0-1.0.txt))

To provide the same look and feel across platforms, we distribute our library
bundled with the OpenSans font (`capellambse/OpenSans-Regular.ttf`). The
OpenSans font is Copyright 2020 [The Open Sans Project
Authors](https://github.com/googlefonts/opensans), licensed under OFL-1.1 (see
full text in [LICENSES/OFL-1.1.txt](LICENSES/OFL-1.1.txt)).

[Jupyter notebook server]: https://jupyter.org/
