#!/usr/bin/env -S python -Xdev
# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""A simple Python REPL with a Capella model.

You can use this script to quickly launch an interactive Python
interpreter and load a model.

If the ``readline`` module is available, the interpreter spawned from
this script uses a separate readline history. It is located in
``$XDG_STATE_HOME/capellambse`` on proper operating systems and in the
``capellambse`` cache directory on others.

Normally this script is run with something like ``python -Xdev -m
capellambse.repl test-5.0``. However, as that can become quite unwieldy,
it is also possible to run it as ``./capellambse/repl.py 5.0`` from the
source tree – on Unix-like operating systems, this will automatically
enable ``-Xdev`` on the Python interpreter. Requirement is a
sufficiently recent version of ``env``, which by now even Debian should
have.

In order to add custom models for the :ref:`model <repl.py-model>`
argument, add a JSON file to the ``capellambse/known_models`` directory.
This file defines the instantiation parameters for the
:class:`capellambse.model.MelodyModel`:

.. literalinclude:: ../../../capellambse/known_models/test-lib.json
   :language: json
   :lineno-start: 1
   :linenos:
"""
from __future__ import annotations

import argparse
import code
import collections.abc as cabc
import contextlib
import importlib
import importlib.resources as imr
import json
import logging
import os
import os.path
import pathlib
import sys
import textwrap
import typing as t

from lxml import etree

import capellambse
from capellambse.loader import exs

try:
    import readline

    try:
        import rlcompleter  # pylint: disable=unused-import
    except ImportError:
        pass

    class _ReadlineHistory:
        def __init__(self, histfile):
            self.histfile = histfile

        def __enter__(self) -> None:
            try:
                readline.read_history_file(self.histfile)
            except FileNotFoundError:
                pass
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


_ModelInfo = t.Dict[str, t.Union[str, t.Dict[str, str]]]

basedir = pathlib.Path(__file__).parent.resolve()
logger = logging.getLogger("capellambse.repl")


def _load_model_info(datapath: str | importlib.abc.Traversable) -> _ModelInfo:
    if isinstance(datapath, str):
        datapath = imr.files(capellambse) / "known_models" / f"{datapath}.json"
    with datapath.open("r", encoding="utf-8") as file:
        return json.load(file)


def _parse_args(args: list[str] | None = None) -> dict[str, t.Any]:
    known_models = list(
        i.name[: -len(".json")]
        for i in capellambse.enumerate_known_models()
        if i.name.endswith(".json")
    )
    parser = argparse.ArgumentParser("capellambse/repl.py")
    parser.add_argument(
        "model",
        default="5.0",
        nargs=1,
        help=(
            "A model name from repl_models, an AIRD file, or a JSON file"
            " describing the model. The following repl_models are known: "
            + ", ".join(f"``{i}``" for i in known_models)
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

    pargs = parser.parse_args(args or sys.argv[1:])
    assert len(pargs.model) == 1
    (model,) = pargs.model
    modelinfo: dict[str, t.Any]
    if model.endswith(".json"):
        modelinfo = _load_model_info(pathlib.Path(model))
    elif model.endswith(".aird"):
        modelinfo = {"path": model}
    else:
        modelinfo = _load_model_info(model)

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
    logger: str = "",  # pylint: disable=redefined-outer-name
) -> cabc.Generator[None, None, None]:
    """Temporarily write log messages into ``file``.

    Parameters
    ----------
    file
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
    except BaseException as err:
        loggerobj.handlers = [handler]
        loggerobj.propagate = False
        loggerobj.exception("Exception reached top of context")
        if not isinstance(err, Exception) or not catch:
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
    """
    try:
        yield
    except exc_types:
        if log:
            logging.info("Exception suppressed", exc_info=True)


def showxml(obj: capellambse.ModelObject | etree._Element) -> None:
    if isinstance(obj, etree._Element):
        elm = obj
    else:
        elm = obj._element
    print(exs.to_string(elm), end="")


def main() -> None:
    """Launch a simple Python REPL with a Capella model."""
    os.chdir(pathlib.Path(capellambse.__file__).parents[1])

    modelinfo = _parse_args()
    logger.debug("Loading model: %r", modelinfo)
    model = capellambse.MelodyModel(**modelinfo)

    interactive_locals = {
        "__doc__": None,
        "__name__": "__console__",
        "etree": etree,
        "im": importlib,
        "imm": importlib.import_module("importlib.metadata"),
        "imr": importlib.import_module("importlib.resources"),
        "logtee": logtee,
        "model": model,
        "pprint": importlib.import_module("pprint").pprint,
        "showxml": showxml,
        "suppress": suppress,
    }

    for m in ("capellambse", "inspect", "logging", "os", "pathlib"):
        interactive_locals[m] = importlib.import_module(m)

    banner = textwrap.dedent(
        f"""\

        {' Model exploration ':=^80}
        `model` is {model.info.title!r} from {modelinfo['path']}
        """
    )

    history_file = capellambse.dirs.user_state_path / "model_exploration.hist"
    with _ReadlineHistory(history_file), suppress(BrokenPipeError):
        code.interact(banner=banner, local=interactive_locals, exitmsg="")


if __name__ == "__main__":
    main()
