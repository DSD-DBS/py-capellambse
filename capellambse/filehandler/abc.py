# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""The abstract FileHandler superclass and utilities."""
from __future__ import annotations

__all__ = [
    "FileHandler",
    "AbstractFilePath",
    "TransactionClosedError",
]

import abc
import collections.abc as cabc
import importlib.abc as iabc
import os
import pathlib
import typing as t

import typing_extensions as te

from capellambse import helpers

if t.TYPE_CHECKING:
    from capellambse.loader import modelinfo


_F = t.TypeVar("_F", bound="FileHandler")


class FileHandler(metaclass=abc.ABCMeta):
    """Abstract super class for file handler implementations.

    Parameters
    ----------
    path
        The location of the remote. The exact accepted forms are
        determined by the specific file handler implementation, for
        example the ``LocalFileHandler`` accepts only local paths, and
        the ``GitFileHandler`` accepts everything that Git accepts.
    subdir
        Consider all paths relative to this subdirectory, instead of the
        root of the file handler's hierarchy.
    """

    path: str | os.PathLike

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        subdir: str | pathlib.PurePosixPath = "/",
        **kw: t.Any,
    ) -> None:
        super().__init__(**kw)
        self.path = path
        self.subdir = subdir

    @abc.abstractmethod
    def get_model_info(self) -> modelinfo.ModelInfo:
        pass

    @abc.abstractmethod
    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        """Open the model file for reading or writing.

        A "file" in this context does not necessarily refer to a
        physical file on disk; it may just as well be streamed in via
        network or other means. Due to this, the file-like returned by
        this method is not required to support random access.

        Parameters
        ----------
        filename
            The name of the file, relative to the ``path`` that was
            given to the constructor.
        mode
            The mode to open the file in. Either ``"r"`` or ``"rb"`` for
            reading, or ``"w"`` or ``"wb"`` for writing a new file. Be
            aware that this method may refuse to open a file for writing
            unless a transaction was started with
            :meth:`write_transaction()` first.
        """

    def write_file(
        self, path: str | pathlib.PurePosixPath, content: bytes, /
    ) -> None:
        """Write a file.

        This method is a convenience wrapper around :meth:`open()`.
        """
        with self.open(path, "wb") as f:
            f.write(content)

    def read_file(self, path: str | pathlib.PurePosixPath, /) -> bytes:
        """Read a file.

        This method is a convenience wrapper around :meth:`open()`.
        """
        with self.open(path, "rb") as f:
            return f.read()

    def write_transaction(
        self, **kw: t.Any
    ) -> t.ContextManager[cabc.Mapping[str, t.Any]]:
        """Start a transaction for writing new model files.

        During a transaction, writable objects returned by
        :meth:`open()` buffer their contents in a temporary location,
        and once the transaction ends, all updated files are committed
        to their destinations at once. If the transaction is aborted,
        for example because an exception was raised, then all changes
        must be rolled back to the state immediately before the
        transaction. If, during a transaction, any relevant file is
        touched without the file handler knowing about it, the behavior
        is undefined.

        Note that :meth:`open()` may refuse to open a file as writable
        if no transaction is currently open. This depends on the needs
        of the underlying abstract file system.

        Transaction arguments
        ---------------------
        A concrete file handler implementation may accept arbitrary
        additional arguments to this method. The implementation should
        however always support the case of no arguments given, in which
        case it should start a transaction with sensible defaults, and
        it should also accept and ignore any arguments it does not
        understand. All additional arguments must be passed in via
        keywords. Positional arguments are not supported.

        The return value of the context manager's ``__enter__()`` method
        is expected to be a mapping of all the keyword arguments that
        were not understood. Client code may use this to react properly
        (e.g. by aborting the transaction early) if a required keyword
        argument is found to be not supported by the underlying file
        handler. If a subclass wishes to call its super class'
        ``write_transaction()`` method, it should remove all the keyword
        arguments that it handles itself and pass on the others
        unchanged.

        Well-known arguments
        --------------------
        The following arguments are considered well-known, and their
        meaning is expected to be the same for all file handlers that
        support them.

        -   ``dry_run`` (``bool``): If set to ``True``, changes made
            during the transaction should be rolled back instead of
            being committed, just as if an exception had been raised.
        -   ``author_name`` (``str``): The name of the author of the
            changes.
        -   ``author_email`` (``str``): The e-mail address to record
            alongside the ``author_name``.
        -   ``commit_msg`` (``str``): A message describing the changes,
            which will be recorded in the version control system.
        -   ``remote_branch`` (``str``): If the model came from a remote
            version control system, changes are normally pushed back to
            the same branch on that remote. This argument specifies an
            alternative branch name to push to (which may not yet exist
            on the remote).
        """

        class EmptyTransaction:
            def __enter__(self):
                return kw

            def __exit__(self, *_):
                pass

        return EmptyTransaction()

    @property
    def rootdir(self) -> AbstractFilePath[te.Self]:  # pragma: no cover
        """The root directory of the file handler."""
        raise TypeError(
            f"{type(self).__name__} does not support listing files"
        )

    def iterdir(  # pragma: no cover
        self, path: str | pathlib.PurePosixPath = ".", /
    ) -> cabc.Iterator[AbstractFilePath[te.Self]]:
        """Iterate over the contents of a directory.

        This method is equivalent to calling
        ``fh.rootdir.joinpath(path).iterdir()``.

        Parameters
        ----------
        path
            The directory to list. If not given, lists the contents of
            the root directory (i.e. the one specified by ``path`` and
            ``subdir``).
        """
        raise TypeError(
            f"{type(self).__name__} does not support listing files"
        )


class AbstractFilePath(os.PathLike[str], iabc.Traversable, t.Generic[_F]):
    """A path to a file in a file handler.

    This is an abstract class with FileHandler-agnostic implementations
    of some of Traversable's methods. It is not meant to be instantiated
    directly, but rather to be used as a base class for concrete file
    path implementations.

    Note that some of these implementations may be inefficient, and
    subclasses are encouraged to override them with more efficient
    implementations if possible.
    """

    def __init__(self, parent: _F, path: pathlib.PurePosixPath):
        self._parent = parent
        self._path = path

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._parent!r}, {self._path!r})"

    def __str__(self) -> str:
        return str(self._path)

    def __truediv__(self, path: str | pathlib.PurePosixPath) -> te.Self:
        return self.joinpath(path)

    def __fspath__(self) -> str:
        return str(self._path)

    def joinpath(self, path: str | pathlib.PurePosixPath) -> te.Self:
        newpath = helpers.normalize_pure_path(path, base=self._path)
        return type(self)(self._parent, newpath)

    @abc.abstractmethod
    def is_dir(self) -> bool:
        ...

    @abc.abstractmethod
    def is_file(self) -> bool:
        ...

    def iterdir(
        self, path: str | pathlib.PurePosixPath = "."
    ) -> cabc.Iterator[te.Self]:
        path = helpers.normalize_pure_path(path, base=self._path)
        return t.cast("cabc.Iterator[te.Self]", self._parent.iterdir(path))

    @property
    def name(self) -> str:
        return self._path.name

    def open(  # type: ignore[override]
        self,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> t.BinaryIO:
        del buffering, errors

        if "b" not in mode:
            raise ValueError("Only binary mode is supported")
        if "r" in mode:
            mode = "rb"
        elif "w" in mode:
            mode = "wb"
        else:
            raise ValueError(f"Unsupported mode: {mode!r}")

        if encoding is not None:
            raise ValueError("Encoding is not supported")
        if newline is not None:
            raise ValueError("Newline is not supported")

        return self._parent.open(self._path, mode)

    def read_bytes(self) -> bytes:
        with self.open("rb") as f:
            return f.read()

    def read_text(self, encoding: str | None = None) -> str:
        with self.open("rb") as f:
            return f.read().decode(encoding or "utf-8")


class TransactionClosedError(RuntimeError):
    """Raised when a transaction must be opened first to write files."""
