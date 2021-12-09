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

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/DSD-DBS/py-capellambse/HEAD?labpath=examples%2F01_Introduction.ipynb)

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

We designed the library API such that it is easy to use and discover, however there is also [documentation available here](https://dsd-dbs.github.io/py-capellambse/). Additionally, the [practical examples folder](https://github.com/DSD-DBS/py-capellambse/blob/master/examples/) provides a collection of Jupyter notebooks with practical examples (like getting traceability matrices, change assessments, BoMs, etc).

## Dependencies on 3rd party components and re-distributions

To provide same look and feel across platforms our diagraming engine uses OpenSans font. And to simplify the library installation and usage we redistribute it in accordance with SIL Open Font License 1.1 that it has at the moment: The bundled OpenSans font (`capellambse/OpenSans-Regular.ttf`) is
Copyright 2020 [The Open Sans Project Authors](https://github.com/googlefonts/opensans), the copy of License text can be seen in `LICENSE-OpenSans.txt`.

## Current limitations

We are continuously improving coverage of Capella onthology with our [high-level API](#TODO) (the current coverage map is available [here](#TODO)), however it is still incomplete. It covers most of the commonly used paths but when you need to get to an ontology element that isnt covered yet you may do so by using the [low-level API](##TODO).

Also, as we started in mid 2019 and there was no such thing as [Python4Capella](https://github.com/labs4capella/python4capella) yet, we are not API compatible with that project. However, we intend to add API compatibility with Python4Capella in later releases.

The generated diagrams are currently not persisted in .aird files and we are not sure yet if we need this feature. If there is a genuine usecase for that we may re-consider it - feel free to create an issue or add comments to an existing one.

## Contributing

We'd love to see your bug reports and improvement suggestions! Please take a look at [guidelines for contributors](https://github.com/DSD-DBS/py-capellambse/blob/master/CONTRIBUTING.md).
