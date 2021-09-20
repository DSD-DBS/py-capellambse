# capellambse -  a Python 3 headless implementation of Capella modeling tool (almost)

## Intro

***Copyright 2021 DB Netz AG, licensed under Apache 2.0 (see full text in `LICENSE.txt`)***

`capellambse` allows you reading and writing Capella models from python without Java or Capella on any (reasonable) platform. We wanted to "talk" to the Capella models from Python but without any JAVA on the way. We thought this project will help individuals and organisations getting through the MBSE adoption journey with Capella faster and so we decided to make this project public and open-source.

With `capellambse` you can access all (almost all atm) Capella model elements, render diagrams (as SVG and PNG). We made it for automation of Systems Engineering work so it integrates nicely into most of CI/CD toolchains. We also found it at the core of our artifact generation pipelines (model to documents, model to SW interfaces).

The library also works with the PVMT and Requirements extensions without any additional efforts.

It started as a basic library that enables us talking to the model somewhere mid 2019. Since then it was re-architected a few times and now has a full read/write capability for most of the present Capella ontology. We are continuously improving the API (introducing shortcuts) and increasing the meta-model coverage.

## Documentation and examples

We designed the library API such that it is easy to use and discover, however there is also [documentation available here](TODO). Additionally, the [practical examples folder](TODO) provides a collection of Jupyter notebooks with practical examples (like getting traceability matrices, change assessments, BoMs, etc).

## Dependencies on 3rd party components and re-distributions

To provide same look and feel across platforms our diagraming engine uses OpenSans font. And to simplify the library installation and usage we decided to redistribute it in accordance with SIL Open Font License 1.1 that it has at the moment: The bundled OpenSans font (`capellambse/OpenSans-Regular.ttf`) is
Copyright 2020 [The Open Sans Project Authors](https://github.com/googlefonts/opensans), the copy of License text can be seen in `LICENSE-OpenSans.txt`.

We also have some optional functionality (automatic generation of diagrams and layouts) that uses [elk.js](TODO). However we dont re-distribute elk.js with this library so if you like trying the auto-gen features you'll need to:

* make sure you have nodejs available in the PATH (version of node should be compatible with elk.js)
* make sure npm is available in the PATH
* call the generative API first time and the auto-install will trigger

## Current limitations

We are continuously improving coverage of Capella onthology with our [high-level API](TODO) (the current coverage map is available [here](TODO)), however it is still incomplete. It covers most of the commonly used paths but when you need to get to an ontology element that isnt covered yet you may do so by using the [low-level API](TODO).

Also, as we started in mid 2019 and there was no such thing as [Python4Capella](TODO) yet, we are not API compatible with that project. However, we intend to add API compatibility with Python4Capella in later releases.

The generated diagrams (elk.js based) are currently not persisted in .aird files and we are not sure yet if we need this feature. If there is a genuine usecase for that we may re-consider it - feel free to create an issue or add comments to an existing one.

## Contributing

We'd love to see your bug reports and improvement suggestions. Contribution rules will be available soon-ish.
As a basic requirement your code needs to go through [black formatter]() and [isort](TODO)
