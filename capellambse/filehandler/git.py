# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import errno
import hashlib
import logging
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import typing as t
import urllib.parse
import weakref

import capellambse.helpers

from . import abc

LOGGER = logging.getLogger(__name__)
CACHEBASE = pathlib.Path(capellambse.dirs.user_cache_dir, "models")
WTBASE = pathlib.Path(capellambse.dirs.user_cache_dir, "worktrees")

_git_object_name = re.compile("(^|/)([0-9a-fA-F]{4,}|(.+_)?HEAD)$")

_NOT_SPECIFIED = object()


class _TreeEntry(t.NamedTuple):
    mode: str
    type: str
    object: str
    file: str

    @classmethod
    def fromstring(cls, entry: str) -> _TreeEntry:
        info, file = entry.split("\t", maxsplit=1)
        mode, type, object = info.split(" ")
        return cls(mode, type, object, file)

    def tostring(self) -> str:
        return f"{self.mode} {self.type} {self.object}\t{self.file}"


class _WritableGitFile(t.BinaryIO):
    def __init__(
        self,
        tx: _GitTransaction,
        cachedir: pathlib.Path,
        path: pathlib.PurePosixPath,
    ) -> None:
        tx.record_pending_update(path, self)
        self.__tx = tx
        self.__path = path
        self.__file = cachedir.joinpath(path).open("wb")

    @property
    def mode(self) -> str:
        return self.__file.mode

    @property
    def name(self) -> str:
        return str(self.__path)

    def close(self) -> None:
        self.__file.close()
        self.__tx.record_update(self.__path)

    @property
    def closed(self) -> bool:
        return self.__file.closed

    def fileno(self) -> int:
        return self.__file.fileno()

    def flush(self) -> None:
        self.__file.flush()

    def isatty(self) -> bool:
        return self.__file.isatty()

    def read(self, n: int = -1) -> bytes:
        return self.__file.read(n)

    def readable(self) -> bool:
        return self.__file.readable()

    def readline(self, limit: int = -1) -> bytes:
        return self.__file.readline(limit)

    def readlines(self, hint: int = -1) -> list[bytes]:
        return self.__file.readlines(hint)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.__file.seek(offset, whence)

    def seekable(self) -> bool:
        return self.__file.seekable()

    def tell(self) -> int:
        return self.__file.tell()

    def truncate(self, size: int | None = None) -> int:
        return self.__file.truncate(size)

    def writable(self) -> bool:
        return self.__file.writable()

    def write(self, s: bytes) -> int:  # type: ignore[override] # ???
        return self.__file.write(s)

    def writelines(  # type: ignore[override] # ???
        self, lines: t.Iterable[bytes]
    ) -> None:
        self.__file.writelines(lines)

    def __enter__(self) -> _WritableGitFile:
        self.__file.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, exc_trace):
        self.__file.__exit__(exc_type, exc_value, exc_trace)
        self.__tx.record_update(self.__path)

    def __iter__(self) -> _WritableGitFile:
        return self

    def __next__(self) -> bytes:
        return self.readline()


class _GitTransaction:
    __old_sha: str
    __unclosed_error = textwrap.dedent(
        """\
        %d file(s) is/are still opened.

        =======================================================================

        You still have open files when committing a transaction.

        Files that are still open CANNOT be committed and are LOST FOREVER!

        Fix your code to ``close()`` all opened files BEFORE control flows out
        of the ``with:`` block opened by ``write_transaction()``.

        Again: YOU HAVE JUST LOST DATA.

        =======================================================================
        """
    )

    def __init__(
        self,
        outer_transactor: cabc.Callable[..., t.ContextManager],
        filehandler: GitFileHandler,
        /,
        *,
        dry_run: bool,
        author_name: str | None,
        author_email: str | None,
        commit_msg: str,
        ignore_empty: bool,
        remote_branch: str | None,
        push: bool,
        push_options: cabc.Sequence[str],
        **kw: t.Any,
    ) -> None:
        self.__outer_context = outer_transactor(**kw)
        self.__handler = filehandler
        self.__dry_run = dry_run
        self.__commit_msg = commit_msg
        self.__ignore_empty = ignore_empty
        self.__push = push
        self.__push_opts = [f"--push-option={i}" for i in push_options]

        self.__gitenv: dict[str, str] = {}
        if author_name:
            self.__gitenv["GIT_AUTHOR_NAME"] = author_name
        if author_email:
            self.__gitenv["GIT_AUTHOR_EMAIL"] = author_email

        targetref = remote_branch or filehandler.revision

        if targetref == "HEAD":
            targetref = self.__resolve_head() or targetref

        if _git_object_name.search(targetref):
            raise ValueError(
                "Target ref looks like a git object, use a different"
                f" remote_branch: {targetref}"
            )
        if not targetref.startswith("refs/heads/"):
            targetref = "refs/heads/" + targetref

        self.__targetref = targetref
        self.__open_files: cabc.MutableMapping[
            tuple[int, pathlib.PurePosixPath], _WritableGitFile
        ] = weakref.WeakValueDictionary()

    def __enter__(self) -> cabc.Mapping[str, t.Any]:
        self.__old_sha = (
            self.__handler._git("rev-parse", self.__handler.revision)
            .decode("ascii")
            .strip()
        )
        if self.__handler._transaction is not None:
            raise RuntimeError("Another transaction is already open")
        self.__handler._transaction = self

        return self.__outer_context.__enter__()

    def __exit__(self, exc_type, exc_value, exc_trace):
        if exc_value is not None:
            self.__handler._transaction = None
            self.__handler._git("reset", "--hard", self.__old_sha)
            return self.__outer_context.__exit__(
                exc_type, exc_value, exc_trace
            )
        try:
            LOGGER.debug("Writing updated tree to database")
            tree = self.__write_tree()

            if self.__ignore_empty and tree == self.__get_old_tree_hash():
                LOGGER.debug("Not creating empty commit (ignore_empty=True)")
                return None

            LOGGER.debug("Creating commit object with tree %s", tree)
            commit = self.__commit(tree)
            if self.__dry_run:
                LOGGER.debug("Not updating branch pointers (dry_run=True)")
                return None

            LOGGER.debug("Updating ref %r to %s", self.__targetref, commit)
            self.__handler._git("reset", "--soft", commit)
            self.__update_target_ref(commit)

            if not self.__push:
                LOGGER.debug("Not pushing changes to remote (push=False)")
                return None

            LOGGER.debug("Pushing updated ref %r", self.__targetref)
            self.__push_updates("origin")
        finally:
            del self.__old_sha
            self.__handler._transaction = None
            self.__outer_context.__exit__(exc_type, exc_value, exc_trace)
        return None

    def record_update(self, filename: pathlib.PurePosixPath) -> None:
        """Record an updated file in the current transaction.

        Parameters
        ----------
        filename
            The path of the file, relative to the root of the repository.
        """
        assert self.__handler._transaction is self
        self.__handler._git("add", filename)

    def record_pending_update(
        self, filename: pathlib.PurePosixPath, file: _WritableGitFile
    ) -> None:
        self.__open_files[id(file), filename] = file

    def __commit(self, tree: str) -> str:
        """Commit ``tree`` as child commit of ``__target_ref``."""
        commit_hash = self.__handler._git(
            "commit-tree",
            tree,
            "-p",
            self.__old_sha,
            "-m",
            self.__commit_msg,
            env=self.__gitenv,
            encoding="ascii",
        )
        commit_hash = commit_hash.strip()

        LOGGER.debug("Created commit with hash %r", commit_hash)
        return commit_hash

    def __push_updates(self, remote: str) -> None:
        """Push the locally updated ``__target_ref`` to ``remote``."""
        self.__handler._git(
            "-c",
            f"remote.{remote}.mirror=false",
            "push",
            *self.__push_opts,
            "--",
            remote,
            self.__targetref,
        )

    def __resolve_head(self) -> str:
        """Resolve HEAD to a single symbolic name."""
        try:
            name = self.__handler._git(
                "rev-parse", "--symbolic-full-name", "HEAD", silent=True
            )
        except subprocess.CalledProcessError:
            name = b""
        return name.decode("utf-8").strip()

    def __update_target_ref(self, commit: str) -> None:
        """Update the local ``__target_ref``."""
        self.__handler._git(
            "update-ref",
            f"-m[{capellambse.__name__}] Commit by capellambse",
            self.__targetref,
            commit,
        )

    def __write_tree(self) -> str:
        """Write the tree built up in the git index to the database."""
        unclosed_files = 0
        for (_, filename), file in self.__open_files.items():
            if not file.closed:
                unclosed_files += 1
                LOGGER.warning("File is still open: %s", filename)
        if unclosed_files:
            LOGGER.critical(self.__unclosed_error, unclosed_files)

        tree_hash = self.__handler._git("write-tree", encoding="ascii").strip()
        LOGGER.debug("Created tree with hash %r", tree_hash)
        return tree_hash

    def __get_old_tree_hash(self) -> str:
        info = self.__handler._git("cat-file", "commit", self.__old_sha)
        for line in info.splitlines():
            if not line:
                break
            kw, hash = line.split(None, 1)
            if kw == b"tree":
                return hash.decode("ascii")

        raise AssertionError(f"No 'tree' in commit {self.__old_sha!r}")


class GitFileHandler(abc.FileHandler):
    """File handler for ``git://`` and related protocols.

    Parameters
    ----------
    revision
        The Git revision to check out. Either a branch or tag name, a
        full ref name, or the object name (i.e. hash) of a commit-ish.
    username
        The user name for authentication with the Git remote.
    password
        The password for authentication with the Git remote.
    identity_file
        Authenticate against the remote with the private key in this
        file. Defaults to using SSH's algorithm for determining a
        suitable key. (SSH only, ignored otherwise)
    known_hosts_file
        An OpenSSH-style ``known_hosts`` file containing the public key
        of the remote server. (SSH only, ignored otherwise)
    disable_cache
        Wipe the local cache and create a fresh, new clone.
    update_cache
        Contact the remote and make sure that the local cache is up to
        date. Note that setting this to ``False`` does not necessarily
        inhibit all attempts to contact the remote; it just disables the
        initial "fetch" operation. Later operations may still require to
        access the server, for example to download Git-LFS files.

    See Also
    --------
    capellambse.filehandler.abc.FileHandler :
        Documentation of common parameters.
    """

    username: str
    password: str
    identity_file: str
    known_hosts_file: str
    cache_dir: pathlib.Path
    """Path to the temporary work tree created by this file handler."""
    shallow: t.Final = False

    __fnz: object
    __has_lfs: bool
    __lfsfiles: dict[pathlib.PurePosixPath, bool]
    __repo: pathlib.Path
    __lockfile: pathlib.Path

    def __init__(
        self,
        path: str | os.PathLike,
        revision: str = "HEAD",
        username: str = "",
        password: str = "",
        identity_file: str = "",
        known_hosts_file: str = "",
        disable_cache: bool = False,
        update_cache: bool = True,
        *,
        subdir: str | pathlib.PurePosixPath = "/",
    ) -> None:
        super().__init__(path, subdir=subdir)
        self.disable_cache = disable_cache

        if bool(username) != bool(password):
            raise TypeError("Either specify username and password or neither")

        self.username = username
        self.password = password
        self.identity_file = identity_file
        self.known_hosts_file = known_hosts_file
        self.update_cache = update_cache

        self.cache_dir = None  # type: ignore[assignment]
        self.__hash, self.revision = self.__resolve_remote_ref(revision)

        self.__init_cache_dir()
        self.__init_worktree()

        self._transaction: _GitTransaction | None = None

    def open(
        self,
        filename: str | pathlib.PurePosixPath,
        mode: t.Literal["r", "rb", "w", "wb"] = "rb",
    ) -> t.BinaryIO:
        path = capellambse.helpers.normalize_pure_path(
            filename, base=self.subdir
        )
        if "w" in mode:
            if self._transaction is None:
                raise abc.TransactionClosedError(
                    "Writing to git requires a transaction"
                )
            return _WritableGitFile(self._transaction, self.cache_dir, path)
        return open(self.cache_dir / path, "rb")  # noqa: SIM115

    def get_model_info(self) -> abc.HandlerInfo:
        def revparse(*args: str) -> str:
            return (
                self._git("rev-parse", *args, silent=True)
                .decode("utf-8", errors="surrogateescape")
                .strip()
            )

        return GitHandlerInfo(
            branch=revparse("--abbrev-ref", self.revision),
            url=str(self.path),
            revision=self.revision,
            rev_hash=self.__hash,
        )

    def write_transaction(
        self,
        dry_run: bool = False,
        author_name: str | None = None,
        author_email: str | None = None,
        commit_msg: str = "Changes made with python-capellambse",
        ignore_empty: bool = True,
        remote_branch: str | None = None,
        push: bool = True,
        push_options: cabc.Sequence[str] = (),
        **kw: t.Any,
    ) -> t.ContextManager[cabc.Mapping[str, t.Any]]:
        """Create a transaction that records all changes as a new commit.

        Parameters
        ----------
        author_name
            The name of the commit author.
        author_email
            The e-mail address of the commit author.
        commit_msg
            The commit message.
        dry_run
            If True, stop before updating the ``revision`` pointer. The
            commit will be created, but will not be part of any branch
            or tag.
        ignore_empty
            If True and the transaction did not actually change any
            files (i.e. the new commit would be tree-same with its
            parent), do not actually make a new commit.

            .. versionchanged:: 0.5.67
               Previous versions would create empty commits if no files
               changed. If you relied on that behavior (e.g. to trigger
               subsequent CI actions), use this option.
        remote_branch
            An alternative branch name to push to on the remote, instead
            of pushing back to the same branch. This is required if
            ``push`` is ``True`` and the ``revision`` that was passed to
            the constructor does not refer to a branch (or looks like a
            git object).

            Note: For convenience, ``refs/heads/`` will be prepended
            automatically to this name if it isn't already present. This
            also means that it is not possible to create tags or other
            types of refs; passing in something like ``refs/tags/v2.4``
            would result in the full ref name
            ``refs/heads/refs/tags/v2.4``.
        push
            Set to ``False`` to inhibit pushing the changes back.
        push_options
            Additional git push options. See ``--push-option`` in
            ``git-push(1)``. Ignored if ``push`` is ``False``.
        **kw
            Additional arguments are ignored.

        Raises
        ------
        ValueError
            - If a commit hash was used during loading, and no
              ``remote_branch`` was given
            - If the given ``remote_branch`` (or the final part of the
              originally given revision) looks like a git object
        """
        return _GitTransaction(
            super().write_transaction,
            self,
            dry_run=dry_run,
            author_name=author_name,
            author_email=author_email,
            commit_msg=commit_msg,
            ignore_empty=ignore_empty,
            remote_branch=remote_branch,
            push=push,
            push_options=push_options,
            **kw,
        )

    @property
    def rootdir(self) -> GitPath:
        """The root directory of the repository."""
        return GitPath(self, pathlib.PurePosixPath("."))

    def iterdir(
        self, path: str | pathlib.PurePosixPath = "."
    ) -> t.Iterator[GitPath]:
        """Iterate over the files in the given directory.

        Parameters
        ----------
        path
            The path to the directory to iterate over.
        """
        path = capellambse.helpers.normalize_pure_path(path, base=self.subdir)
        for subpath in self.cache_dir.joinpath(*path.parts).iterdir():
            yield GitPath(self, pathlib.PurePosixPath(path, subpath.name))

    @staticmethod
    def __cleanup_worktree(
        repo_root: pathlib.Path, worktree: pathlib.Path, /
    ) -> None:
        LOGGER.debug("Removing worktree at %s", worktree)
        subprocess.run(
            ["git", "worktree", "remove", "-f", str(worktree)],
            check=True,
            cwd=repo_root,
        )

    def __get_git_env(self) -> tuple[dict[str, str], list[str]]:
        git_env = os.environ.copy()
        git_cmd = ["git"]

        if not os.environ.get("GIT_ASKPASS"):
            path_to_askpass = (
                pathlib.Path(__file__).parent / "git_askpass.py"
            ).absolute()

            git_env["GIT_ASKPASS"] = str(path_to_askpass)

            try:
                os.chmod(path_to_askpass, 0o755)
            except OSError:
                LOGGER.info(
                    "Setting permission 755 for GIT_ASKPASS file failed"
                )

        if self.username and self.password:
            git_env["GIT_USERNAME"] = self.username
            git_env["GIT_PASSWORD"] = self.password

            git_cmd += ["-c", "credential.helper="]

        if self.identity_file and self.known_hosts_file:
            ssh_command = [
                "ssh",
                "-i",
                self.identity_file,
                f"-oUserKnownHostsFile={self.known_hosts_file}",
            ]
            git_env["GIT_SSH_COMMAND"] = shlex.join(ssh_command)

            git_cmd += ["-c", "credential.helper="]

        return git_env, git_cmd

    def __is_local_repo(self) -> bool:
        return (
            isinstance(self.path, pathlib.Path)
            or str(self.path).startswith("file://")
            or pathlib.Path(self.path).is_absolute()
        )

    def __init_cache_dir(self) -> None:
        if self.__is_local_repo():
            self.__init_cache_dir_local()
        else:
            self.__init_cache_dir_remote()

    def __init_cache_dir_local(self) -> None:
        if isinstance(self.path, pathlib.Path):
            path = self.path
        elif str(self.path).startswith("file://"):
            urlpath = urllib.parse.urlparse(str(self.path)).path
            urlpath = urllib.parse.unquote(urlpath)
            windows = isinstance(pathlib.Path(), pathlib.WindowsPath)
            path = pathlib.Path(urlpath[1:] if windows else urlpath)
        else:
            path = pathlib.Path(self.path)
        self.__repo = self.cache_dir = path.resolve()
        gitdir = self.__git_nolock("rev-parse", "--git-dir", encoding="utf-8")
        assert isinstance(gitdir, str)
        self.__lockfile = (
            pathlib.Path(self.cache_dir, gitdir.strip())
            .resolve()
            .joinpath("capellambse.lock")
        )

    def __init_cache_dir_remote(self) -> None:
        slug_pattern = '[\x00-\x1f\x7f"*/:<>?\\|]+'
        path_slug = re.sub(slug_pattern, "-", str(self.path))
        hashpath = str(self.path).encode("utf-8", errors="surrogatepass")

        path_hash = hashlib.sha256(hashpath, usedforsecurity=False).hexdigest()
        old_dir = CACHEBASE.joinpath(path_hash, path_slug)

        path_hash = hashlib.blake2s(
            hashpath, digest_size=12, usedforsecurity=False
        ).hexdigest()
        self.__repo = self.cache_dir = CACHEBASE.joinpath(path_hash, path_slug)
        self.__lockfile = self.__repo.joinpath("capellambse.lock")

        if old_dir.exists():
            LOGGER.debug("Moving cache from %s to %s", old_dir, self.cache_dir)
            self.cache_dir.parent.mkdir(parents=True, exist_ok=True)
            os.rename(old_dir, self.cache_dir)
            try:
                old_dir.parent.rmdir()
            except OSError as err:
                if err.errno != errno.ENOTEMPTY:
                    raise

        if self.cache_dir.exists() and self.disable_cache:
            shutil.rmtree(str(self.cache_dir))

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with capellambse.helpers.flock(self.__repo / "capellambse.lock"):
            update_cache = self.update_cache
            if not self.cache_dir.joinpath("config").exists():
                LOGGER.debug("Creating a new git repo in %s", self.cache_dir)
                self.__git_nolock(
                    "-c", "init.defaultBranch=master", "init", "--bare"
                )
                self.__git_nolock(
                    "remote", "add", "--mirror=fetch", "origin", self.path
                )
                update_cache = True

            if update_cache:
                LOGGER.debug("Updating cache at %s", self.cache_dir)
                fetchopts = ["--filter=tree:0"]
                if (self.cache_dir / "shallow").exists():
                    fetchopts.append("--unshallow")
                fetchspec = f"+{self.revision}"
                if not _git_object_name.search(self.revision):
                    fetchspec += f":{self.revision}"
                self.__git_nolock("fetch", *fetchopts, self.path, fetchspec)

            self.__git_nolock("config", "extensions.worktreeConfig", "true")

    def __resolve_default_branch(self) -> tuple[str, str]:
        """Resolve the default branch name and its hash on the remote."""
        LOGGER.debug("Resolving default branch on remote %s", self.path)
        listing = self.__git_nolock(
            "ls-remote", "--symref", self.path, "HEAD", encoding="utf-8"
        )
        assert isinstance(listing, str)
        match = re.search(
            r"ref: (refs/heads/.*)\s+HEAD\s+([0-9a-fA-F]+)", listing
        )
        if match:
            refname = match.group(1)
            hash = match.group(2)
            return hash, refname
        raise ValueError("Failed to resolve default branch on remote")

    def __resolve_remote_ref(self, ref: str) -> tuple[str, str]:
        """Resolve the given ``ref`` on the remote."""
        if ref == "HEAD":
            try:
                return self.__resolve_default_branch()
            except ValueError:
                pass
        LOGGER.debug("Resolving ref %r on remote %s", ref, self.path)
        listing = self.__git_nolock(
            "ls-remote", self.path, ref, encoding="utf-8"
        )
        assert isinstance(listing, str)
        if not listing:
            if not _git_object_name.search(ref):
                raise ValueError(f"Ref does not exist on remote: {ref}")
            LOGGER.debug("Ref %r not found, assuming object name", ref)
            return ref, ref
        refs = [i.split("\t") for i in listing.strip().split("\n")]
        if len(refs) > 1:
            exact = [i for i in refs if i[1] == ref]
            if len(exact) != 1:
                raise ValueError(
                    f"Ambiguous ref name {ref}, found {len(refs)}:"
                    f" {', '.join(i[1] for i in refs)}"
                )
            refs = exact

        hash, refname = refs[0]
        LOGGER.debug(
            "Resolved ref %r as remote ref %r (%s)", ref, refname, hash
        )
        return hash, refname

    def __init_worktree(self) -> None:
        WTBASE.mkdir(0o700, parents=True, exist_ok=True)
        worktree = pathlib.Path(
            tempfile.mkdtemp(None, f"capellambse-{os.getpid()}-", WTBASE)
        )
        LOGGER.debug("Setting up a worktree at %s", worktree)
        try:
            self._git(
                "worktree",
                "add",
                "--detach",
                worktree,
                self.__hash,
            )
        except:
            os.rmdir(worktree)
            raise
        self.cache_dir = worktree
        gitdir = self.__git_nolock("rev-parse", "--git-dir", encoding="utf-8")
        assert isinstance(gitdir, str)
        self.__repo = pathlib.Path(self.cache_dir, gitdir.strip()).resolve()

        self.__fnz = weakref.finalize(
            self, self.__cleanup_worktree, self.__repo, worktree
        )

        if not self.__is_local_repo():
            try:
                self.__git_nolock("lfs", "env", silent=True)
            except subprocess.CalledProcessError:
                LOGGER.debug("LFS not installed, skipping setup")
            else:
                LOGGER.debug("LFS support detected, registering filter")
                self.__git_nolock(
                    "config",
                    "--worktree",
                    "core.hooksPath",
                    self.__repo.joinpath("hooks"),
                )
                self.__git_nolock("lfs", "install", "--worktree", "--force")
                self.__git_nolock("config", "--worktree", "core.bare", "false")
                self._git("lfs", "pull")

    @t.overload
    def _git(
        self,
        *cmd: t.Any,
        encoding: str,
        env: cabc.Mapping[str, str] | None = ...,
        silent: bool = ...,
        **kw: t.Any,
    ) -> str: ...
    @t.overload
    def _git(
        self,
        *cmd: t.Any,
        encoding: None = ...,
        env: cabc.Mapping[str, str] | None = ...,
        silent: bool = ...,
        **kw: t.Any,
    ) -> bytes: ...
    def _git(
        self,
        *cmd: t.Any,
        env: cabc.Mapping[str, str] | None = None,
        silent: bool = False,
        **kw: t.Any,
    ) -> bytes | str:
        with capellambse.helpers.flock(self.__lockfile):
            return self.__git_nolock(*cmd, env=env, silent=silent, **kw)

    def __git_nolock(
        self,
        *cmd: t.Any,
        env: cabc.Mapping[str, str] | None = None,
        silent: bool = False,
        **kw: t.Any,
    ) -> bytes | str:
        LOGGER.debug("Running command %s", cmd)
        returncode = 0
        stderr = None

        git_env, git_cmd = self.__get_git_env()

        try:
            proc = subprocess.run(
                git_cmd + [str(i) for i in cmd],
                capture_output=True,
                check=True,
                cwd=self.cache_dir,
                env={**git_env, **(env or {})},
                **kw,
            )
            returncode = proc.returncode
            stderr = proc.stderr
            return proc.stdout
        except subprocess.CalledProcessError as err:
            returncode = err.returncode
            stderr = err.stderr
            raise
        finally:
            if returncode != 0 and not silent:
                level = logging.ERROR
            else:
                level = logging.DEBUG

            if stderr:
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8")

                for line in stderr.splitlines():
                    LOGGER.getChild("git").log(level, "%s", line)
            LOGGER.log(level, "Exit status: %d", returncode)


class GitPath(abc.FilePath[GitFileHandler]):
    def is_dir(self) -> bool:
        return self._parent.cache_dir.joinpath(self._path).is_dir()

    def is_file(self) -> bool:
        return self._parent.cache_dir.joinpath(self._path).is_file()


@dataclasses.dataclass
class GitHandlerInfo(abc.HandlerInfo):
    branch: str | None
    revision: str
    rev_hash: str
