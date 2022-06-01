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

## Getting started

Click on this button to launch a Binder instance and start exploring our test models within seconds:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/DSD-DBS/py-capellambse/HEAD?labpath=examples%2F01%20Introduction.ipynb)

*Warning:* [Do not enter confidential information], such as passwords for non-public models, into a notebook hosted on myBinder. If you want to try out `capellambse` with those models, please install and run it in a local, trusted environment (see below)!

[Do not enter confidential information]: <https://github.com/alan-turing-institute/the-turing-way/blob/b36c3ac1c78acbbe18441beaa89514544ed12021/workshops/boost-research-reproducibility-binder/workshop-presentations/zero-to-binder-python.md#private-files>

Alternatively, to start using the project on your local machine, follow these steps:

1. Clone the repository.

   ```bash
   git clone https://github.com/DSD-DBS/py-capellambse.git
   cd py-capellambse
   ```

2. Create a virtual environment.

   ```bash
   python3 -m venv .venv

   # on Linux or Mac:
   source .venv/bin/activate

   # on Windows using cmd.exe:
   .venv\Scripts\activate.bat

   # on Windows using PowerShell:
   .venv/Scripts/activate.ps1
   ```

3. Install `capellambse` and `Jupyter`.

   ```bash
   pip install -e .
   pip install jupyter
   ```

4. Open the example notebooks.

   ```bash
   cd examples
   jupyter-notebook
   ```

The above code should clone the library and install it and all of its dependencies in a fresh virtual environment. Then, it should have started a jupyter-notebook server right in the examples folder. If your browser did not open automatically, follow the instructions in the terminal to start it manually.

Once in the browser, simply click on the [`01_Introduction.ipynb`](examples/01_Introduction.ipynb) notebook to start!

## Documentation and examples

The library is designed to be easy to use and discover, especially in an
interactive environment such as JupyterLab. Additionally, [API documentation]
is automatically generated and published whenever new features and bug fixes
are added.

[API documentation]: https://dsd-dbs.github.io/py-capellambse/

You are encouraged to explore our test models and demo notebooks on either a
public myBinder instance or by installing the library locally ([see
above](#getting-started)).

The `examples` directory contains several hands-on example notebooks that you
can immediately run and start experimenting with. Below is a short summary of
each notebook's goal. If you are in the JupyterLab environment, you can click
the notebook names to directly open them in a new lab tab. On Github, you will
be shown a statically rendered preview of the notebook.

- [`01 Introduction.ipynb`](examples/01%20Introduction.ipynb) provides a
  high-level overview of the library features, with some visual examples
  leveraging Jupyter's and IPython's rich display functionality.
- [`02 Intro to Physical
  Architecture.ipynb`](examples/02%20Intro%20to%20Physical%20Architecture%20API.ipynb)
  explores some more advanced concepts on the example of the Physical
  Architecture Layer. It also showcases how to use `pandas` dataframes to
  effectively manage and search through large numbers of model elements.
- [`03 Data Values.ipynb`](examples/03%20Data%20Values.ipynb) introduces the
  data value classes from the `information.datavalue` package, which are used
  in several places throughout a Capella model.
- [`04 Intro to Jinja
  templating.ipynb`](examples/04%20Intro%20to%20Jinja%20templating.ipynb)
  demonstrates how to effectively combine `capellambse` with the powerful
  [Jinja templating engine](https://palletsprojects.com/p/jinja/).
- [`05 Introduction to
  Libraries.ipynb`](examples/05%20Introduction%20to%20Libraries.ipynb) shows
  how to use Capella Library Projects within capellambse. These allow multiple
  collaborators to work on different parts of a project, or on derived
  projects, independently from one another.
- [`06 Introduction to Requirement access and management with ReqIF
  extension.ipynb`](examples/06%20Introduction%20to%20Requirement%20access%20and%20management%20with%20ReqIF%20extension.ipynb)
  introduces the optional ReqIF extension. If this extension is installed and
  activated in Capella, Requirement objects can be managed right in a model,
  and linked up with other model elements. Based on this functionality,
  `capellambse` also provides a basic exporter for `.reqif` and `.reqifz`
  files.

We are constantly working on improving everything shown here, as well as adding
even more useful functionality and helpful demos. If you have any new ideas
that were not mentioned yet, [don't hesitate to contribute](CONTRIBUTING.md)!

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
