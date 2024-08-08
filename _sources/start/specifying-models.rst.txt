..
   SPDX-FileCopyrightText: Copyright DB InfraGO AG
   SPDX-License-Identifier: Apache-2.0

.. _specifying-models:

*****************
Specifying models
*****************

.. currentmodule:: capellambse.cli_helpers

|project| and tools using it generally support multiple ways of specifying a
model to load and use. Which way to use depends on the specific situation. This
page lists all the ways that are commonly supported.

Simple paths
============

A model can be specified by the path to its main ``*.aird`` file.

.. code:: text

  /home/username/models/coffee-machine/coffee-machine.aird
  C:\Capella\workspace\coffee-machine\coffee-machine.aird
  ./model/model.aird
  model.aird

This is equivalent to specifying the *path* and *entrypoint* arguments to the
:class:`~capellambse.model.MelodyModel` constructor, e.g.:

.. code:: python

   model = capellambse.MelodyModel(
       path="/home/username/models/coffee-machine",
       entrypoint="coffee-machine.aird",
   )

Just like how the *entrypoint* argument is optional if there is only one
``*.aird`` file in the given *path*, the file name here may be omitted in this
case as well:

.. code:: text

  /home/username/models/coffee-machine/
  C:\Capella\workspace\coffee-machine
  ./model
  .

Make sure to escape any special characters such as whitespace or backslashes
when specifying paths on the command line.

Remote URLs
===========

Models can also be loaded from various remote locations by specifying a URL in
the form of ``protocol://host.name/path/to/model.aird``. Out of the box,
|project| supports the following protocols:

- :class:`file:///local/folder
  <capellambse.filehandler.local.LocalFileHandler>`
- :class:`git://host.name/repo.git
  <capellambse.filehandler.git.GitFileHandler>` and variants, like:
  ``git+https://host.name/repo``, ``git@host.name:repo``
- :class:`http:// and https:// <capellambse.filehandler.http.HTTPFileHandler>`,
  example: ``https://host.name/path/%s?param=arg``
- :class:`zip://, zip+https:// etc.
  <capellambse.filehandler.zip.ZipFileHandler>`, examples:
  ``zip:///local/file.zip``, ``zip+https://host.name/remote/file.zip``,
  ``zip+https://host.name/remote/%s?param=arg!file.zip``

Click on a protocol to get to the detailed documentation including supported
additional arguments, which can be passed in using JSON (see below).

JSON
====

For more complex cases, like remote models that require credentials, it is
possible to pass a JSON-encoded dictionary. This dictionary can contain any key
that the :class:`~capellambse.model.MelodyModel` constructor and the underlying
:class:`~capellambse.filehandler.FileHandler` understands.

Note that, when passing such JSON as command line argument, it is necessary to
escape the whole JSON string to prevent the Shell from interpreting it,
removing quotes, replacing variables, etc. In bash-like shells, this is usually
accomplished by wrapping it in single quotes, like this:

.. code:: bash

   python -m capellambse.repl '{"path": "git@example.com:demo-model.git", "revision": "dev", ...}'

.. known-models:

Known models
============

A model can be given a short name by placing a JSON file in the user's
'known_models' folder. This is the exact same JSON as described above, just put
into a file instead of passed as string.

Run the following command to find out where to put the files:

.. code:: bash

   python -m capellambse.cli_helpers

This will show the folder for custom 'known_models' files, and list the names
of all files found in either the custom or built-in folder. These names can
then be passed to any CLI command in place of the full model definition.

For example, to start a capellambse REPL using the built-in "coffee-machine"
model definition, you can run:

.. code:: bash

   python -m capellambse.repl coffee-machine

The most common keys to use include ``path`` and ``entrypoint``, as well as
credential-related keys like ``username``, ``password`` or ``identity_file``.
Refer to the documentation of :class:`~capellambse.model.MelodyModel`, as well
as the respective FileHandler class you want to use for more details:

- For local file paths:
  :class:`~capellambse.filehandler.local.LocalFileHandler`
- For Git repositories: :class:`~capellambse.filehandler.git.GitFileHandler`
- For simple HTTP/HTTPS servers, optionally using HTTP Basic Authentication:
  :class:`~capellambse.filehandler.http.HTTPFileHandler`
- For the Gitlab Artifacts service:
  :class:`~capellambse.filehandler.gitlab_artifacts.GitlabArtifactsFiles`

CLI support
===========

In order to make it easy to support model loading from the CLI, |project|
exposes a few functions and classes in the :mod:`capellambse.cli_helpers`
module.

Standalone functions
--------------------

These functions help with loading a model from arbitrary user-supplied strings,
such as command line arguments.

.. autofunction:: loadinfo
   :noindex:

.. autofunction:: loadcli
   :noindex:

.. autofunction:: enumerate_known_models
   :noindex:

Click parameter types
---------------------

There are also Click parameter types available that encapsulate the
``loadinfo`` and ``loadcli`` functions, respectively:

.. autoclass:: ModelInfoCLI
   :noindex:

.. autoclass:: ModelCLI
   :noindex:
