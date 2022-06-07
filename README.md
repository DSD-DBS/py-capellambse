# capellambse

*A Python 3 headless implementation of the Capella modeling tool*

![CI build](https://github.com/DSD-DBS/py-capella-mbse/actions/workflows/build-test-publish.yml/badge.svg)
![CI lint](https://github.com/DSD-DBS/py-capella-mbse/actions/workflows/lint.yml/badge.svg)

## Intro

***Copyright 2021 DB Netz AG, licensed under Apache 2.0 (see full text in [LICENSE](https://github.com/DSD-DBS/py-capellambse/blob/master/LICENSE))***

`capellambse` allows you reading and writing Capella models from python without Java or [Capella tool](https://www.eclipse.org/capella/) on any (reasonable) platform. We wanted to "talk" to Capella models from Python but without any Java on the way. We thought this project will help individuals and organisations getting through the MBSE adoption journey with Capella faster and so we made it public and open-source.

With `capellambse` you can access all (or almost all) Capella model elements, render diagrams (as SVG and PNG). We made it for automation of Systems Engineering work so it integrates nicely into most of CI/CD toolchains. We also found it at the core of our artifact generation pipelines (model to documents, model to SW interfaces).

The library works with [PVMT](https://www.eclipse.org/capella/addons.html) and [Requirements](https://github.com/eclipse/capella-requirements-vp) extensions without any additional efforts.

It started as a basic library somewhere mid 2019. Since then it was re-architected a few times and now has a full read/write capability for most of the present Capella ontology. We are continuously improving the API (introducing shortcuts), increasing the meta-model coverage and have more engineering automations and improvements in the pipeline to share.

## Documentation and examples

The library is designed to be easy to use and discover, especially in an
interactive environment such as JupyterLab. Additionally, [API documentation]
is automatically generated and published whenever new features and bug fixes
are added.

[API documentation]: https://dsd-dbs.github.io/py-capellambse/

You are encouraged to explore our test models and demo notebooks. Click on the
button below to launch a [Jupyter notebook server] on the public myBinder
service, and get started in seconds:

[Jupyter notebook server]: https://jupyter.org/

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/DSD-DBS/py-capellambse/HEAD?labpath=examples%2F01%20Introduction.ipynb)

*Warning:* [Do not enter confidential information], such as passwords for
non-public models, into a notebook hosted on myBinder. If you want to try out
`capellambse` with those models, please [install and run](#installation) it in
a local, trusted environment!

[Do not enter confidential information]: <https://github.com/alan-turing-institute/the-turing-way/blob/b36c3ac1c78acbbe18441beaa89514544ed12021/workshops/boost-research-reproducibility-binder/workshop-presentations/zero-to-binder-python.md#private-files>

The `examples` directory contains several hands-on example notebooks that you
can immediately run and start experimenting with. Below is a short summary of
each notebook's goal. If you are in the JupyterLab environment, you can click
the notebook names to directly open them in a new lab tab. On Github, you will
be shown a statically rendered preview of the notebook.

- [`01 Introduction.ipynb`](examples/01%20Introduction.ipynb) provides a
  high-level overview of the library features. It visualizes examples like a
  Component - Function allocation table by leveraging Jupyter's and IPython's
  rich display functionality.
- [`02 Intro to Physical
  Architecture.ipynb`](examples/02%20Intro%20to%20Physical%20Architecture%20API.ipynb)
  explores some more advanced concepts on the example of the Physical
  Architecture Layer. It shows how to derive tabular data, like a Bill of
  Materials or a Software to Hardware allocation table, by using `pandas`
  dataframes.
- [`03 Data Values.ipynb`](examples/03%20Data%20Values.ipynb) shows how the API
  can be used to explore classes, class instances and other objects related to
  data modeling.
- [`04 Intro to Jinja
  templating.ipynb`](examples/04%20Intro%20to%20Jinja%20templating.ipynb)
  demonstrates how to effectively combine `capellambse` with the powerful
  [Jinja] templating engine. This enables the creation of all sorts of
  model-derived documents and artifacts, including interactive web pages, PDF
  documents and any other textual representations of your models.
- [`05 Introduction to
  Libraries.ipynb`](examples/05%20Introduction%20to%20Libraries.ipynb) shows
  how to use Capella Library Projects within capellambse. In this example
  you'll learn how the API can be used to open a project that is based on a
  library and find objects in both models.
- [`06 Introduction to Requirement access and
  management.ipynb`](examples/06%20Introduction%20to%20Requirement%20access%20and%20management.ipynb)
  shows how the API can be used to work with requirements objects, introduced
  by the Capella [Requirements Viewpoint]. In this example you'll see how to
  find requirements in the model, see which objects requirements are linked /
  traced to and even export requirements to Excel or ReqIF formats.
- [`07 Code Generation.ipynb`](examples/07%20Code%20Generation.ipynb) shows how
  to generate code from class diagrams. In particular, we focus on Interface
  Descriptive Languages with concrete examples for `Class` to [ROS2 IDL] and
  Google [Protocol Buffers]. We also show how simple Python stubs could be
  generated given a `Class` object.

[Jinja]: https://palletsprojects.com/p/jinja/
[Requirements Viewpoint]: https://www.eclipse.org/capella/addons.html
[ROS2 IDL]: https://docs.ros.org/en/rolling/Concepts/About-ROS-Interfaces.html
[Protocol Buffers]: https://developers.google.com/protocol-buffers

We are constantly working on improving everything shown here, as well as adding
even more useful functionality and helpful demos. If you have any new ideas
that were not mentioned yet, [don't hesitate to contribute](CONTRIBUTING.md)!

## Installation

In order to use private models that are not publicly available, please install
and use `capellambse` in a local, trusted environment.

You can follow these instructions to start a local [Jupyter notebook server]
within minutes:

1. Create a virtual environment.

   ```bash
   python3 -m venv .venv

   # on Linux or Mac:
   source .venv/bin/activate

   # on Windows using cmd.exe:
   .venv\Scripts\activate.bat

   # on Windows using PowerShell:
   .venv/Scripts/activate.ps1
   ```

2. You can install the latest stable version of `capellambse`, as well as the
   Jupyter notebook server from the public PyPI repository.

   ```bash
   pip install jupyter capellambse
   ```

   Alternatively, you can install the latest developmental version straight
   from Github:

   ```basbh
   pip install jupyter git+https://github.com/DSD-DBS/py-capellambse.git
   ```

3. Open the example notebooks.

   ```bash
   cd examples
   jupyter-notebook
   ```

The above steps installed the library and all of its dependencies in a fresh
virtual environment. Then, it has started a jupyter-notebook server right in
the examples folder.

If your browser did not open automatically, follow the instructions in the
terminal to start it manually.

Once in the browser, simply click on the [`01
Introduction.ipynb`](examples/01%20Introduction.ipynb) notebook to start!

## Dependencies on 3rd party components and re-distributions

To provide same look and feel across platforms our diagraming engine uses OpenSans font. And to simplify the library installation and usage we redistribute it in accordance with SIL Open Font License 1.1 that it has at the moment: The bundled OpenSans font (`capellambse/OpenSans-Regular.ttf`) is
Copyright 2020 [The Open Sans Project Authors](https://github.com/googlefonts/opensans), the copy of License text can be seen in `LICENSE-OpenSans.txt`.

## Current limitations

We are continuously improving coverage of Capella onthology with our [high-level API](#TODO) (the current coverage map is available [here](#TODO)), however it is still incomplete. It covers most of the commonly used paths but when you need to get to an ontology element that isnt covered yet you may do so by using the [low-level API](##TODO).

Also, as we started in mid 2019 and there was no such thing as [Python4Capella](https://github.com/labs4capella/python4capella) yet, we are not API compatible with that project. However, we intend to add API compatibility with Python4Capella in later releases.

The generated diagrams are currently not persisted in .aird files and we are not sure yet if we need this feature. If there is a genuine usecase for that we may re-consider it - feel free to create an issue or add comments to an existing one.

### Render diagrams in untrusted jupyter notebooks

The SVG format relies on a stylesheet, however in untrusted notebooks any stylesheets
are stripped. As a workaround we support the PNG format. For this the [cairosvg](https://pypi.org/project/CairoSVG/)
library is needed which requires the following additional setup steps on windows:

- Download and execute the [latest GTK installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/tag/2022-01-04).
- Reboot to add the path to the installed compiled libraries into your system environment PATH

## Contributing

We'd love to see your bug reports and improvement suggestions! Please take a look at [guidelines for contributors](https://github.com/DSD-DBS/py-capellambse/blob/master/CONTRIBUTING.md).
