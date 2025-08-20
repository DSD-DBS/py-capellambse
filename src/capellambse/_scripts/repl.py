# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
import textwrap
import typing as t

import click
from lxml import etree

import capellambse
from capellambse import cli_helpers
from capellambse.loader import exs

basedir = pathlib.Path(__file__).parent.resolve()
logger = logging.getLogger("capellambse.repl")

try:
    import readline

    with contextlib.suppress(ImportError):
        import rlcompleter  # noqa: F401

    @contextlib.contextmanager
    def _readline_history(histfile: pathlib.Path, /) -> cabc.Iterator[None]:
        try:
            readline.read_history_file(histfile)
        except FileNotFoundError:
            pass
        except OSError:
            backupfile = histfile.with_suffix(".hist.bak")
            logger.exception(
                "Cannot restore prompt history from %r, renaming to %r and starting fresh",
                os.fspath(histfile),
                backupfile.name,
            )
            try:
                histfile.rename(backupfile)
            except OSError as err:
                logger.error(
                    "Could not rename history file, disabling history saving: %s: %s",
                    type(err).__name__,
                    err,
                )
                histfile = pathlib.Path(os.devnull)

        readline.parse_and_bind("tab: complete")

        try:
            yield
        finally:
            try:
                histfile.parent.mkdir(parents=True, exist_ok=True)
                histfile.open("wb").close()
            except OSError:
                pass
            readline.append_history_file(100_000, histfile)

except ImportError:

    @contextlib.contextmanager
    def _readline_history(_histfile, /) -> cabc.Iterator[None]:
        yield


@click.command()
@click.argument("modelinfo", type=cli_helpers.ModelInfoCLI(), required=False)
@click.option(
    "--disable-diagram-cache",
    is_flag=True,
    help="Disable the diagram cache, if one was defined for the model",
)
@click.option(
    "--dump",
    is_flag=True,
    help="Dump model info as JSON to stdout and exit",
)
@click.option(
    "--hold/--no-hold",
    help="Inhibit automatic model updates (update_cache=False)",
)
@click.option(
    "--wipe/--no-wipe",
    help="Wipe the cache (disable_cache=True)",
)
def main(
    *,
    modelinfo: dict[str, t.Any] | None,
    disable_diagram_cache: bool,
    dump: bool,
    hold: bool,
    wipe: bool,
) -> None:
    """Launch a REPL for exploring Capella models.

    You can use this command to quickly launch an interactive Python
    interpreter and load a model.

    If the ``readline`` module is available, the interpreter spawned
    from this script uses a separate readline history. It is located in
    ``$XDG_STATE_HOME/capellambse`` on proper operating systems and in
    the ``capellambse`` cache directory on others.

    It can be used as simply as:

        capellambse repl <MODEL>

    However, while developing capellambse itself, it may be beneficial
    to additionally set some global interpreter flags:

        python -Xdev -Xfrozen_modules=off -m capellambse repl <MODEL>

    This will ensure that development related warnings like
    DeprecationWarning are enabled, and ensure that attached debuggers
    won't miss any breakpoints.

    In addition to the standard Python builtins, the environment in the
    REPL also provides a few convenience imports and helper functions,
    which will be listed right before the first prompt. Further
    information may be obtained using the `help()` builtin.
    """
    os.chdir(pathlib.Path(capellambse.__file__).parents[2])

    if modelinfo is not None:
        if hold:
            modelinfo["update_cache"] = False
        if wipe:
            modelinfo["disable_cache"] = True
        if disable_diagram_cache and "diagram_cache" in modelinfo:
            del modelinfo["diagram_cache"]

    if dump:
        if modelinfo is None:
            raise SystemExit("No model specified, cannot dump")
        print(json.dumps(modelinfo, indent=2))
        raise SystemExit(0)

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

    if modelinfo is not None:
        logger.debug("Loading model: %r", modelinfo["path"])
        model = capellambse.MelodyModel(**modelinfo)
        interactive_locals["model"] = model
        banner = textwrap.dedent(
            f"""\

            {" Model exploration ":=^80}
            `model` is {model.info.title!r}
            from {modelinfo["path"]}
            """
        )
    else:
        banner = textwrap.dedent(
            f"""\

            {" Model exploration ":=^80}
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
    with _readline_history(history_file), suppress(BrokenPipeError):
        code.interact(banner=banner, local=interactive_locals, exitmsg="")


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
            logger.info("Exception suppressed", exc_info=True)


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
