#!/usr/bin/env -S python -Xdev -Xfrozen_modules=off
# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""A simple Python REPL with a Capella model.

You can use this script to quickly launch an interactive Python
interpreter and load a model.

If the ``readline`` module is available, the interpreter spawned from
this script uses a separate readline history. It is located in
``$XDG_STATE_HOME/capellambse`` on proper operating systems and in the
``capellambse`` cache directory on others.

Normally this script is run with something like:

.. code-block:: bash

   python -Xdev -m capellambse.repl test-5.0

However, as that can become quite unwieldy, it is also possible to run
it directly from the source tree with:

.. code-block:: bash

    ./capellambse/repl.py test-5.0

On Unix-like operating systems, this will automatically enable ``-Xdev``
on the Python interpreter.

In order to add custom models for the :ref:`--model <repl.py-model>`
argument, add a JSON file to your user ``known_models`` directory. This
file defines the instantiation parameters for the
:class:`capellambse.model.MelodyModel`:

.. literalinclude:: ../../../capellambse/known_models/test-lib.json
   :language: json
   :lineno-start: 1
   :linenos:

Use the following command to view the path of your ``known_models``
directory, and to see which models are currently available:

.. code-block:: bash

   python -m capellambse.cli_helpers

In addition to the standard Python builtins, he environment in the REPL
also provides the following convenience imports:

- The Python packages ``capellambse``, ``inspect``, ``logging``, ``os``,
  ``pathlib``
- ``importlib`` as ``im``, with its submodules ``importlib.metadata`` as
  ``imm`` and ``importlib.resources`` as ``imr``
- The ``etree`` module from ``lxml``
- The ``pprint`` function from the ``pprint`` module

A few helpful functions specific to working interactively with models
are also available. Use the ``help`` builtin inside the REPL to get more
information and usage examples.

- ``fzf``: Wrapper around the ``fzf`` binary (must be in the PATH) which
  makes it easy to select a model element interactively from a list
- ``logtee``: Context manager that redirects log messages to a file
- ``showxml``: Print the XML representation of a model object
- ``suppress``: Context manager that suppresses exceptions of given type
"""

from __future__ import annotations

import argparse
import code
import collections.abc as cabc
import contextlib
import importlib
import json
import logging
import operator
import os
import os.path
import pathlib
import shutil
import subprocess
import sys
import textwrap
import typing as t

from lxml import etree

import capellambse
from capellambse import cli_helpers
from capellambse.loader import exs

try:
    import readline

    with contextlib.suppress(ImportError):
        import rlcompleter  # noqa: F401

    class _ReadlineHistory:
        def __init__(self, histfile):
            self.histfile = histfile

        def __enter__(self) -> None:
            with contextlib.suppress(FileNotFoundError):
                readline.read_history_file(self.histfile)
            readline.parse_and_bind("tab: complete")

        def __exit__(self, *_) -> None:
            try:
                self.histfile.parent.mkdir(parents=True, exist_ok=True)
                self.histfile.open("wb").close()
            except OSError:
                pass
            readline.append_history_file(100_000, self.histfile)

except ImportError:

    class _ReadlineHistory:  # type: ignore[no-redef]
        def __init__(self, *__, **_):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *_):
            pass


basedir = pathlib.Path(__file__).parent.resolve()
logger = logging.getLogger("capellambse.repl")


def _parse_args() -> dict[str, t.Any] | None:
    known_models = {
        i.name[: -len(".json")]: i
        for i in capellambse.enumerate_known_models()
        if i.name.endswith(".json")
    }
    parser = argparse.ArgumentParser("capellambse/repl.py")
    parser.add_argument(
        "model",
        default=None,
        nargs="?",
        help=(
            "A model name from known_models, an AIRD file, or the path to (or"
            " contents of) a JSON file describing the model. The following"
            " models are known: " + ", ".join(f"``{i}``" for i in known_models)
        ),
    )
    parser.add_argument(
        "--disable-diagram-cache",
        action="store_true",
        help="Disable the diagram cache, if one was defined for the model",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump model info as JSON to stdout and exit",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"capellambse {capellambse.__version__}",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--hold",
        action="store_true",
        help="Inhibit automatic model updates (update_cache=False)",
    )
    group.add_argument(
        "--wipe",
        action="store_true",
        help="Wipe the cache (disable_cache=True)",
    )

    pargs = parser.parse_args(sys.argv[1:])
    if pargs.model is None:
        if pargs.dump:
            raise SystemExit("No model specified, cannot dump")
        return None

    modelinfo = cli_helpers.loadinfo(pargs.model)

    if pargs.hold:
        modelinfo["update_cache"] = False
    if pargs.wipe:
        modelinfo["disable_cache"] = True

    if pargs.disable_diagram_cache and "diagram_cache" in modelinfo:
        del modelinfo["diagram_cache"]

    if pargs.dump:
        print(json.dumps(modelinfo, indent=2))
        raise SystemExit(0)
    return modelinfo


@contextlib.contextmanager
def logtee(
    filename: os.PathLike[str] | str,
    /,
    *,
    append: bool = False,
    catch: bool = False,
    tee: bool = True,
    level: int | str | None = None,
    logger: str = "",
) -> cabc.Generator[None, None, None]:
    """Temporarily write log messages to a file.

    This function adds an additional log handler, meaning that the
    current logging targets (usually stderr) will also still be served.

    Parameters
    ----------
    filename
        The file path to write log messages to.
    append
        Append to the file instead of overwriting it.
    catch
        If ``True``, catches and suppresses exceptions that reach the
        context manager. Only ``Exception`` and subtypes will be
        suppressed. Regardless of this parameter, exceptions (of any
        type) will always be logged (subject to the log level).
    level
        Change the log level during redirection.
    logger
        Attach to this sub-logger instead of the root logger.
    tee
        Keep the original log destination(s) intact as well. If
        ``False``, also inhibits propagation of log messages to parent
        loggers.
    """
    loggerobj = logging.getLogger(logger)
    handler = logging.FileHandler(filename, mode="wa"[bool(append)])

    orig_handlers = loggerobj.handlers
    orig_propagate = loggerobj.propagate
    orig_level = loggerobj.level

    loggerobj.handlers = orig_handlers * bool(tee) + [handler]
    loggerobj.propagate = bool(tee)
    if level is not None:
        loggerobj.setLevel(level)

    try:
        yield
    except BaseException:
        loggerobj.handlers = [handler]
        loggerobj.propagate = False
        loggerobj.exception("Exception reached top of context")
        if not catch:
            raise
    finally:
        loggerobj.handlers = orig_handlers
        loggerobj.propagate = orig_propagate
        loggerobj.level = orig_level
        handler.close()


@contextlib.contextmanager
def suppress(
    *exc_types: type[BaseException], log: bool = True
) -> cabc.Iterator[None]:
    """Prevent the specified types of exceptions from propagating.

    Parameters
    ----------
    exc_types
        The exception types to suppress. Subclasses of these exceptions
        will also be suppressed.
    log
        Print a short warning about the exception to stderr.

    Examples
    --------
    >>> with suppress(ValueError):
    ...     print("Hello")
    ...     raise ValueError("oops")
    ...     print("World")
    ...
    Hello
    """
    try:
        yield
    except exc_types:
        if log:
            logging.info("Exception suppressed", exc_info=True)


def showxml(obj: capellambse.ModelObject | etree._Element) -> None:
    """Show the XML representation of a model object.

    Examples
    --------
    >>> my_obj = model.search("LogicalComponent").by_name("My Component")
    >>> showxml(my_obj)
    <ownedLogicalComponents name="My Component">
      ...
    </ownedLogicalComponents>
    """
    if isinstance(obj, etree._Element):
        elm = obj
    else:
        elm = obj._element
    print(exs.to_string(elm), end="")


def fzf(
    elements: cabc.Iterable[capellambse.ModelObject],
    attr: str = "name",
) -> capellambse.ModelObject | None:
    """Interactively select an element using fzf.

    This function requires the ``fzf`` binary to be installed and in the
    ``$PATH``.

    Examples
    --------
    >>> # Select a LogicalComponent by name
    >>> obj = fzf(model.search("LogicalComponent"))

    >>> # Select a ComponentExchange by the name of its target component
    >>> obj = fzf(model.search("ComponentExchange"), "target.parent.name")
    """

    def repr(obj):
        return getattr(obj, "_short_repr_", obj.__repr__)()

    binary = shutil.which("fzf")
    if not binary:
        raise RuntimeError("fzf is not installed")
    elements = list(elements)

    getter = operator.attrgetter(attr)

    entries = [(str(getter(i)).replace("\0", ""), repr(i)) for i in elements]
    maxlen = max(len(i[0]) for i in entries)
    maxlen = min(maxlen, 40)
    fzf_input = "\0".join(
        f"{i} \x1b[97m{s:{maxlen}}  \x1b[36m{e}"
        for i, (s, e) in enumerate(entries)
    )

    try:
        proc = subprocess.run(
            [binary, "--ansi", "--read0", "--with-nth=2.."],
            check=True,
            input=fzf_input,
            text=True,
            stdout=subprocess.PIPE,
        )
    except (Exception, KeyboardInterrupt):
        return None
    else:
        selected = elements[int(proc.stdout.strip().split(" ", 1)[0])]
        print(repr(selected))
        return selected


def main() -> None:
    """Launch a simple Python REPL with a Capella model."""
    os.chdir(pathlib.Path(capellambse.__file__).parents[1])

    interactive_locals = {
        "__doc__": None,
        "__name__": "__console__",
        "etree": etree,
        "fzf": fzf,
        "im": importlib,
        "imm": importlib.import_module("importlib.metadata"),
        "imr": importlib.import_module("importlib.resources"),
        "logtee": logtee,
        "pprint": importlib.import_module("pprint").pprint,
        "showxml": showxml,
        "suppress": suppress,
    }

    for m in ("capellambse", "inspect", "logging", "os", "pathlib"):
        interactive_locals[m] = importlib.import_module(m)

    modelinfo = _parse_args()
    if modelinfo is not None:
        logger.debug("Loading model: %r", modelinfo)
        model = capellambse.MelodyModel(**modelinfo)
        interactive_locals["model"] = model
        banner = textwrap.dedent(
            f"""\

            {' Model exploration ':=^80}
            `model` is {model.info.title!r}
            from {modelinfo['path']}
            """
        )
    else:
        banner = textwrap.dedent(
            f"""\

            {' Model exploration ':=^80}
            Load a model with `model = capellambse.loadcli("model-name")`
            or `model = capellambse.MelodyModel("uri", arg=...)`.
            """
        )

    banner += textwrap.dedent(
        """\

        Convenience imports:
        - `capellambse`, `inspect`, `logging`, `os`, `pathlib`
        - `im` = importlib (`imm` = .metadata, `imr` = .resources)
        - `etree` = lxml.etree, `pprint` = pprint.pprint

        Helpful functions and context managers (use `help(name)`):
        - `fzf`: Select a model element interactively from a list
        - `logtee`: CM that redirects log messages to a file
        - `showxml`: Print the XML representation of a model object
        - `suppress`: CM that suppresses exceptions of given type
        """
    )

    history_file = capellambse.dirs.user_state_path / "model_exploration.hist"
    with _ReadlineHistory(history_file), suppress(BrokenPipeError):
        code.interact(banner=banner, local=interactive_locals, exitmsg="")


if __name__ == "__main__":
    main()
