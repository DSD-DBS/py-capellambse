# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""Helps loading Capella models (including fragmented variants)."""

from __future__ import annotations

__all__ = [
    "CorruptModelError",
    "FragmentType",
    "MelodyLoader",
    "ModelFile",
]

import collections
import collections.abc as cabc
import contextlib
import enum
import itertools
import logging
import operator
import os
import pathlib
import re
import shutil
import sys
import tempfile
import typing as t
import urllib.parse
import uuid

from lxml import builder, etree

import capellambse._namespaces as _n
from capellambse import filehandler, helpers
from capellambse.loader import exs
from capellambse.loader.modelinfo import ModelInfo

E = builder.ElementMaker()
LOGGER = logging.getLogger(__name__)
PROJECT_NATURE = "org.polarsys.capella.project.nature"
VISUAL_EXTS = frozenset(
    {
        ".aird",
        ".airdfragment",
    }
)
SEMANTIC_EXTS = frozenset(
    {
        ".capella",
        ".capellafragment",
        ".melodyfragment",
        ".melodymodeller",
    }
)
VALID_EXTS = VISUAL_EXTS | SEMANTIC_EXTS | {".afm"}

IDTYPES = frozenset({"id", "uid", "xmi:id"})
IDTYPES_RESOLVED = frozenset(helpers.resolve_namespace(t) for t in IDTYPES)
IDTYPES_PER_FILETYPE: t.Final[dict[str, frozenset]] = {
    ".afm": frozenset(),
    ".aird": frozenset({"uid", helpers.resolve_namespace("xmi:id")}),
    ".airdfragment": frozenset({"uid", helpers.resolve_namespace("xmi:id")}),
    ".capella": frozenset({"id"}),
    ".capellafragment": frozenset({"id"}),
    ".melodymodeller": frozenset({"id"}),
    ".melodyfragment": frozenset({"id"}),
}
RE_VALID_ID = re.compile(
    r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
)
CAP_VERSION = re.compile(r"Capella_Version_([\d.]+)")
METADATA_TAG = f"{{{_n.NAMESPACES['metadata']}}}Metadata"
ROOT_XT = (
    "org.polarsys.capella.core.data.capellamodeller:Project",
    "org.polarsys.capella.core.data.capellamodeller:Library",
)


def _derive_entrypoint(
    path: str | os.PathLike | filehandler.FileHandler,
    entrypoint: str | pathlib.PurePosixPath | None = None,
    **kwargs: t.Any,
) -> tuple[filehandler.FileHandler, pathlib.PurePosixPath]:
    if entrypoint:
        if not isinstance(path, filehandler.FileHandler):
            path = filehandler.get_filehandler(path, **kwargs)
        entrypoint = helpers.normalize_pure_path(entrypoint)
        return path, entrypoint

    if not isinstance(path, filehandler.FileHandler):
        path = os.fspath(path)
        protocol, nested_path = filehandler.split_protocol(path)
        if protocol == "file":
            assert isinstance(nested_path, pathlib.Path)
            if nested_path.suffix == ".aird":
                entrypoint = pathlib.PurePosixPath(nested_path.name)
                path = nested_path.parent
                return filehandler.get_filehandler(path, **kwargs), entrypoint
            if nested_path.is_file():
                raise ValueError(
                    f"Invalid entrypoint: Not an .aird file: {nested_path}"
                )
        path = filehandler.get_filehandler(path, **kwargs)

    aird_files = [i for i in path.iterdir() if i.name.endswith(".aird")]
    if not aird_files:
        raise ValueError("No .aird file found, specify entrypoint")
    if len(aird_files) > 1:
        raise ValueError("Multiple .aird files found, specify entrypoint")
    entrypoint = pathlib.PurePosixPath(aird_files[0])

    return path, entrypoint


def _find_refs(root: etree._Element) -> cabc.Iterable[str]:
    return itertools.chain(
        (x.split("#")[0] for x in root.xpath(".//referencedAnalysis/@href")),
        root.xpath(".//semanticResources/text()"),
    )


def _unquote_ref(ref: str) -> str:
    ref = urllib.parse.unquote(ref)
    prefix = "platform:/resource/"
    if ref.startswith(prefix):
        ref = ref.replace(prefix, "../")
    return ref


def _round_version(v: str, prec: int) -> str:
    """Round a version number.

    Parameters
    ----------
    v
        The version number.
    prec
        Precision to round to, i.e. the number of leading non-zero
        parts. Remaining parts will be set to zero.

    Returns
    -------
    str
        The rounded version number.
    """
    assert prec > 0
    pos = dots = 0
    while pos < len(v) and dots < prec:
        try:
            pos = v.index(".", pos) + 1
        except ValueError:
            return v
        else:
            dots += 1
    return v[:pos] + re.sub(r"[^.]+", "0", v[pos:])


class FragmentType(enum.Enum):
    """The type of an XML fragment."""

    SEMANTIC = enum.auto()
    VISUAL = enum.auto()
    OTHER = enum.auto()


class MissingResourceLocationError(KeyError):
    """Raised when a model needs an additional resource location."""


class CorruptModelError(Exception):
    """Raised when the model is corrupted and cannot be processed safely.

    In addition to the short description in the exception's arguments,
    some validators may also produce additional information in the form
    of CRITICAL log messages just before this exception is raised.
    """


class ResourceLocationManager(dict):
    def __missing__(self, key: str) -> t.NoReturn:
        raise MissingResourceLocationError(key)


class ModelFile:
    """Represents a single file in the model (i.e. a fragment)."""

    __xtypecache: dict[str, dict[int, etree._Element]]
    __idcache: dict[str, etree._Element | None]
    __hrefsources: dict[str, etree._Element]

    @property
    def fragment_type(self) -> FragmentType:
        if self.filename.suffix in SEMANTIC_EXTS:
            return FragmentType.SEMANTIC
        if self.filename.suffix in VISUAL_EXTS:
            return FragmentType.VISUAL
        return FragmentType.OTHER

    def __init__(
        self,
        filename: pathlib.PurePosixPath,
        handler: filehandler.FileHandler,
        *,
        ignore_uuid_dups: bool,
    ) -> None:
        self.filename = filename
        self.filehandler = handler
        self.__ignore_uuid_dups = (
            ignore_uuid_dups or self.fragment_type is FragmentType.VISUAL
        )

        with handler.open(filename) as f:
            tree = etree.parse(
                f, etree.XMLParser(remove_blank_text=True, huge_tree=True)
            )

        self.root = tree.getroot()
        self.idcache_rebuild()

    def __getitem__(self, key: str) -> etree._Element:
        e = self.__idcache.get(key)
        if e is None:
            raise KeyError(key)
        return e

    def enumerate_uuids(self) -> set[str]:
        """Enumerate all UUIDs used in this fragment."""
        return set(self.__idcache)

    def idcache_index(self, subtree: etree._Element) -> None:
        """Index the IDs of ``subtree``."""
        idtypes = IDTYPES_PER_FILETYPE[self.filename.suffix]
        for elm in subtree.iter():
            xtype = helpers.xtype_of(elm)
            if xtype is not None:
                self.__xtypecache[xtype][id(elm)] = elm

            for idtype in idtypes:
                elm_id = elm.get(idtype, None)
                if elm_id is None:
                    continue
                existing = self.__idcache.get(elm_id)
                if existing is not None and existing is not elm:
                    msg = (
                        f"Duplicate UUID {elm_id!r}"
                        f" within fragment {self.filename!s}"
                    )
                    if self.__ignore_uuid_dups:
                        LOGGER.warning(msg)
                    else:
                        raise CorruptModelError(msg)
                self.__idcache[elm_id] = elm

            href = elm.get("href")
            if href is not None:
                self.__hrefsources[href.split("#")[-1]] = elm

    def idcache_remove(self, source: str | etree._Element) -> None:
        """Remove the ID or all IDs below the source from the ID cache."""
        if isinstance(source, str):
            with contextlib.suppress(KeyError):
                del self.__idcache[source]

        else:
            for elm in source.iter():
                xtype = helpers.xtype_of(elm)
                if xtype:
                    del self.__xtypecache[xtype][id(elm)]
                for idtype in IDTYPES_RESOLVED:
                    elm_id = elm.get(idtype, None)
                    if elm_id is None:
                        continue

                    with contextlib.suppress(KeyError):
                        del self.__idcache[elm_id]
                href = elm.get("href")
                if href is not None:
                    del self.__hrefsources[href.split("#")[-1]]

    def idcache_rebuild(self) -> None:
        """Invalidate and rebuild this file's ID cache."""
        LOGGER.debug("Indexing file %s...", self.filename)
        self.__xtypecache = collections.defaultdict(dict)
        self.__idcache = {}
        self.__hrefsources = {}
        self.idcache_index(self.root)
        LOGGER.debug("Cached %d element IDs", len(self.__idcache))

    def idcache_reserve(self, new_id: str) -> None:
        """Reserve the given ID for an element to be inserted later."""
        self.__idcache[new_id] = None

    def update_namespaces(self, viewpoints: cabc.Mapping[str, str]) -> None:
        """Update the current namespace map.

        Parameters
        ----------
        viewpoints
            A mapping from viewpoint names to the version activated in
            the model.

            If an element from a versioned Plugin is encountered, but
            the Plugin's viewpoint is not activated in the model, an
            error is raised and no update is performed.
        """
        new_nsmap: dict[str, str] = {
            "xmi": _n.NAMESPACES["xmi"],
            "xsi": _n.NAMESPACES["xsi"],
        }
        for elem in self.root.iter():
            xtype = helpers.xtype_of(elem)
            if xtype is None:
                continue
            ns, _, _ = xtype.partition(":")
            plugin = _n.NAMESPACES_PLUGINS.get(ns)
            if plugin is None:
                try:
                    uri = elem.nsmap[ns]
                except KeyError:
                    LOGGER.error("Undefined and unknown namespace %s", ns)
                    continue
            else:
                uri = plugin.name.rstrip("/")
                if plugin.version is not None:
                    assert plugin.viewpoint is not None
                    vp_version = viewpoints.get(plugin.viewpoint)
                    if not vp_version:
                        raise CorruptModelError(
                            f"Viewpoint not activated: {plugin.viewpoint}"
                        )
                    vp_version = _round_version(
                        vp_version, plugin.version_precision
                    )
                    uri += f"/{vp_version}"

            assert new_nsmap.get(ns) in (None, uri)
            new_nsmap[ns] = uri

        assert new_nsmap
        LOGGER.debug("New nsmap: %s", new_nsmap)
        if self.root.nsmap == new_nsmap:
            return

        new_root = self.root.makeelement(
            self.root.tag,
            attrib=self.root.attrib,
            nsmap=dict(sorted(new_nsmap.items())),
        )
        new_root.extend(self.root)

        siblings = self.root.itersiblings(preceding=True)
        for i in reversed(list(siblings)):
            new_root.addprevious(i)

        siblings = self.root.itersiblings(preceding=False)
        for i in list(siblings):
            new_root.addnext(i)

        self.root = new_root

    def iterall_xt(
        self, xtypes: cabc.Container[str]
    ) -> cabc.Iterator[etree._Element]:
        """Iterate over all elements in this tree by ``xsi:type``."""
        for xtype, elms in self.__xtypecache.items():
            if xtype in xtypes:
                yield from elms.values()

    def write_xml(
        self,
        file: t.BinaryIO,
        encoding: str = "utf-8",
    ) -> None:
        """Write this file's XML into the file specified by ``path``."""
        if self.fragment_type == FragmentType.SEMANTIC:
            line_length = exs.LINE_LENGTH
        else:
            line_length = sys.maxsize

        exs.write(
            self.root,
            file,
            encoding=encoding,
            line_length=line_length,
            siblings=True,
        )

    def unfollow_href(self, element_id: str) -> etree._Element:
        """Unfollow a fragment link and return the placeholder element.

        If the given UUID is not linked to from this file, None is
        returned.
        """
        return self.__hrefsources[element_id]


class MelodyLoader:
    """Facilitates extensive access to Polarsys / Capella projects."""

    def __init__(
        self,
        path: str | os.PathLike | filehandler.FileHandler,
        entrypoint: str | pathlib.PurePosixPath | None = None,
        *,
        resources: (
            cabc.Mapping[
                str,
                filehandler.FileHandler | str | os.PathLike | dict[str, t.Any],
            ]
            | None
        ) = None,
        ignore_duplicate_uuids_and_void_all_warranties: bool = False,
        **kwargs: t.Any,
    ) -> None:
        """Construct a MelodyLoader.

        Parameters
        ----------
        path
            The ``path`` argument to the primary file handler, or the
            primary file handler itself.
        entrypoint
            The entry point into the model, i.e. the top-level ``.aird``
            file. This must be located within the primary file handler.
        resources
            Additional file handler instances that provide library
            resources that are referenced from the model.
        ignore_duplicate_uuids_and_void_all_warranties
            Ignore corruption due to duplicate UUIDs (see below).
        kwargs
            Additional arguments to the primary file handler, if
            necessary.

        Raises
        ------
        CorruptModelError
            If the model is corrupt.

            Currently the only kind of corruption that is detected is
            duplicated UUIDs (either within a fragment or across
            multiple fragments).

            It is possible to ignore this error and load the model
            anyways by setting the keyword-only argument
            *ignore_duplicate_uuids_and_void_all_warranties* to
            ``True``. However, this *will* lead to strange behavior like
            random exceptions when searching or filtering, or
            accidentally working with the wrong object. If you try to
            make changes to the model, always make sure that you have an
            up to date backup ready. In order to prevent accidental
            overwrites with an even corrupter model, you must therefore
            also set the *i_have_a_recent_backup* keyword argument to
            ``True`` when calling :meth:`save`.
        """
        self.__ignore_uuid_dups: bool = (
            ignore_duplicate_uuids_and_void_all_warranties
        )
        self.__may_be_corrupt = False

        handler, self.entrypoint = _derive_entrypoint(
            path, entrypoint, **kwargs
        )
        if self.entrypoint.suffix != ".aird":
            raise ValueError("Invalid entrypoint, specify the ``.aird`` file")

        self.resources = ResourceLocationManager({"\0": handler})
        for resname, reshdl in (resources or {}).items():
            if not resname:
                raise ValueError("Empty resource name")
            if "/" in resname or "\0" in resname:
                raise ValueError(f"Invalid resource name: {resname!r}")

            if isinstance(reshdl, str | os.PathLike):
                self.resources[resname] = filehandler.get_filehandler(reshdl)
            elif isinstance(reshdl, cabc.Mapping):
                self.resources[resname] = filehandler.get_filehandler(**reshdl)
            else:
                self.resources[resname] = reshdl

        self.trees: dict[pathlib.PurePosixPath, ModelFile] = {}
        self.__load_referenced_files(
            pathlib.PurePosixPath("\0", self.entrypoint)
        )

        self.check_duplicate_uuids()

    @property
    def filehandler(self) -> filehandler.FileHandler:
        r"""The file handler containing the original model.

        This is a shorthand for ``self.resources["\0"]``.
        """
        return self.resources["\0"]

    def check_duplicate_uuids(self) -> None:
        seen_ids = set[str]()
        has_dups = False
        for fragment, tree in self.trees.items():
            tree_ids = set(tree.enumerate_uuids())
            if duplicates := seen_ids & tree_ids:
                LOGGER.critical(
                    "Duplicate UUIDs across fragments (found in %s): %r",
                    fragment,
                    duplicates,
                )
                self.__may_be_corrupt = True
                has_dups = True
        if has_dups and not self.__ignore_uuid_dups:
            raise CorruptModelError(
                "Model has duplicated UUIDs across fragments"
                " - check the 'resources' for duplicate models"
            )

    def __load_referenced_files(
        self, resource_path: pathlib.PurePosixPath
    ) -> None:
        if resource_path in self.trees:
            return

        if resource_path.suffix not in VALID_EXTS:
            LOGGER.warning(
                (
                    "Ignoring file of unknown type,"
                    " loaded model may be incomplete: %s"
                ),
                resource_path.name,
            )
            self.__may_be_corrupt = True
            return

        handler = self.resources[resource_path.parts[0]]
        filename = pathlib.PurePosixPath(*resource_path.parts[1:])
        frag = ModelFile(
            filename, handler, ignore_uuid_dups=self.__ignore_uuid_dups
        )
        self.trees[resource_path] = frag
        for ref in _find_refs(frag.root):
            ref_name = helpers.normalize_pure_path(
                _unquote_ref(ref), base=resource_path.parent
            )
            self.__load_referenced_files(ref_name)

    def save(self, **kw: t.Any) -> None:
        """Save all model files.

        Parameters
        ----------
        kw
            Additional keyword arguments accepted by the file handler in
            use. Please see the respective documentation for more info.

        See Also
        --------
        capellambse.filehandler.local.LocalFileHandler.write_transaction :
            Accepted ``**kw`` when using local directories
        capellambse.filehandler.git.GitFileHandler.write_transaction :
            Accepted ``**kw`` when using ``git://`` and similar URLs

        Notes
        -----
        With a :attr:`filehandler` that contacts a remote location (such
        as the :class:`capellambse.filehandler.git.GitFileHandler` with
        non-local repositories), saving might fail if the local state
        has gone out of sync with the remote state. To avoid this,
        always leave the ``update_cache`` parameter at its default value
        of ``True`` if you intend to save changes.
        """
        self.check_duplicate_uuids()

        overwrite_corrupt = kw.pop("i_have_a_recent_backup", False)
        if self.__may_be_corrupt and not overwrite_corrupt:
            raise CorruptModelError(
                "Refusing to save a corrupt model without having a backup"
                " (hint: pass i_have_a_recent_backup=True)"
            )

        self.update_namespaces()

        LOGGER.debug("Saving model %r", self.get_model_info().title)
        with self.filehandler.write_transaction(**kw) as unsupported_kws:
            if unsupported_kws:
                LOGGER.warning(
                    "Ignoring unsupported transaction parameters: %s",
                    ", ".join(repr(k) for k in unsupported_kws),
                )
            for fname, tree in self.trees.items():
                resname = fname.parts[0]
                fname = pathlib.PurePosixPath(*fname.parts[1:])
                if resname != "\0":
                    continue

                LOGGER.debug("Saving tree %r to file %s", tree, fname)
                with self.resources[resname].open(fname, "wb") as f:
                    tree.write_xml(f)

    def update_namespaces(self) -> None:
        """Update the namespace definitions on each fragment root.

        This method is automatically called while saving to ensure that
        all namespaces necessary for the current model elements are
        registered on the fragment roots.
        """
        vp = dict(self.referenced_viewpoints())
        for fname, fragment in self.trees.items():
            if fragment.fragment_type != FragmentType.SEMANTIC:
                continue

            LOGGER.debug("Updating namespaces on fragment %s", fname)
            fragment.update_namespaces(vp)

    def idcache_index(self, subtree: etree._Element) -> None:
        """Index the IDs of ``subtree``.

        This method must be called after adding ``subtree`` to the XML
        tree.

        Parameters
        ----------
        subtree
            The new element that was just inserted.
        """
        try:
            _, tree = self._find_fragment(subtree)
        except ValueError:
            raise ValueError(
                "Call idcache_index() after adding the subtree"
            ) from None

        tree.idcache_index(subtree)

    def idcache_remove(self, subtree: etree._Element) -> None:
        """Remove the ``subtree`` from the ID cache.

        This method must be called before actually removing ``subtree``
        from the XML tree.

        Parameters
        ----------
        subtree
            The element that is about to be removed.
        """
        try:
            _, tree = self._find_fragment(subtree)
        except ValueError:
            raise ValueError(
                "Call idcache_remove() before removing the subtree"
            ) from None

        tree.idcache_remove(subtree)

    def idcache_rebuild(self) -> None:
        """Rebuild the ID caches of all loaded :class:`ModelFile` instances."""
        for tree in self.trees.values():
            tree.idcache_rebuild()

    def generate_uuid(
        self, parent: etree._Element, *, want: str | None = None
    ) -> str:
        """Generate a unique UUID for a new child of ``parent``.

        The generated ID is guaranteed to be unique across all currently
        loaded fragments.

        Parameters
        ----------
        parent
            The parent element below which the new UUID will be used.
        want
            Try this UUID first, and use it if it satisfies all other
            constraints. If it does not satisfy all constraints (e.g. it
            would be non-unique), a random UUID will be generated as
            normal.

        Returns
        -------
        str
            The new UUID.
        """
        _, tree = self._find_fragment(parent)

        if want:
            try:
                self[want]
            except KeyError:
                tree.idcache_reserve(want)
                return want
            else:
                raise ValueError(f"UUID {want!r} is already in use")

        while True:
            new_id = str(uuid.uuid4())
            try:
                self[new_id]
            except KeyError:
                tree.idcache_reserve(new_id)
                return new_id
        raise AssertionError()

    @contextlib.contextmanager
    def new_uuid(
        self, parent: etree._Element, *, want: str | None = None
    ) -> cabc.Generator[str, None, None]:
        """Context Manager around :meth:`generate_uuid()`.

        This context manager yields a newly generated model-wide unique
        UUID that can be inserted into a new element during the ``with``
        block. It tries to keep the ID cache consistent in some harder
        to manage edge cases, like exceptions being thrown. Additionally
        it checks that the generated UUID was actually used in the tree;
        not using it before the ``with`` block ends is an error and
        provokes an Exception.

        .. note:: You still need to call :meth:`idcache_index()` on the
            newly inserted element!

        Example usage::

            >>> with ldr.new_uuid(parent_elm) as obj_id:
            ...     child_elm = parent_elm.makeelement("ownedObjects")
            ...     child_elm.set("id", obj_id)
            ...     parent_elm.append(child_elm)
            ...     ldr.idcache_index(child_elm)

        If you intend to reserve a UUID that should be inserted later,
        use :meth:`generate_uuid()` directly.

        Parameters
        ----------
        parent
            The parent element below which the new UUID will be used.
        want
            Request this UUID. The request may or may not be fulfilled;
            always use the actual UUID returned by the context manager.
        """
        _, tree = self._find_fragment(parent)
        new_uuid = self.generate_uuid(parent, want=want)

        def cleanup_after_failure() -> None:
            tree.idcache_remove(new_uuid)
            for child in parent:
                for id_attr in IDTYPES_RESOLVED:
                    if child.get(id_attr) == new_uuid:
                        parent.remove(child)

        try:
            yield new_uuid
        except BaseException:
            cleanup_after_failure()
            raise

        if self[new_uuid] is None:
            cleanup_after_failure()
            raise RuntimeError("New UUID was requested but never used")

    def xpath(
        self,
        query: str | etree.XPath,
        *,
        namespaces: cabc.Mapping[str, str] | None = None,
        roots: etree._Element | cabc.Iterable[etree._Element] | None = None,
    ) -> list[etree._Element]:
        """Run an XPath query on all fragments.

        Note that, unlike the ``iter_*`` methods, placeholder elements
        are not followed into their respective fragment.

        Parameters
        ----------
        query
            The XPath query
        namespaces
            Namespaces used in the query. Defaults to all known
            namespaces.
        roots
            A list of XML elements to use as roots for the query.
            Defaults to all tree roots.

        Returns
        -------
        list[lxml.etree._Element]
            A list of all matching elements.
        """
        return list(
            map(
                operator.itemgetter(1),
                self.xpath2(query, namespaces=namespaces, roots=roots),
            )
        )

    def xpath2(
        self,
        query: str | etree.XPath,
        *,
        namespaces: cabc.Mapping[str, str] | None = None,
        roots: etree._Element | cabc.Iterable[etree._Element] | None = None,
    ) -> list[tuple[pathlib.PurePosixPath, etree._Element]]:
        """Run an XPath query and return the fragments and elements.

        Note that, unlike the ``iter_*`` methods, placeholder elements
        are not followed into their respective fragment.

        The tuples have the fragment where the match was found as first
        element, and the LXML element as second one.

        Parameters
        ----------
        query
            The XPath query
        namespaces
            Namespaces used in the query. Defaults to all known
            namespaces.
        roots
            A list of XML elements to use as roots for the query.
            Defaults to all tree roots.

        Returns
        -------
        list[tuple[pathlib.PurePosixPath, lxml.etree._Element]]
            A list of 2-tuples, containing:

            1. The fragment name where the match was found.
            2. The matching element.
        """
        if namespaces is None:
            namespaces = _n.NAMESPACES

        def follow_href(
            tree: pathlib.PurePosixPath, match: etree._Element
        ) -> tuple[pathlib.PurePosixPath, etree._Element]:
            if href := match.get("href"):
                match = self.follow_link(match, href)
                return (self.find_fragment(match), match)
            return (tree, match)

        if not isinstance(query, etree.XPath):
            query = etree.XPath(query, namespaces=namespaces)

        if roots is None:
            roottrees = [(k, t.root) for k, t in self.trees.items()]
        elif isinstance(roots, etree._Element):
            roottrees = [(self._find_fragment(roots)[0], roots)]
        elif isinstance(roots, cabc.Iterable):
            roottrees = [(self._find_fragment(r)[0], r) for r in roots]
        else:
            raise TypeError(
                "`roots` must be an XML element or a list thereof,"
                f" not {type(roots).__name__}"
            )

        ret = []
        for fragment, tree in roottrees:
            ret += [follow_href(fragment, elem) for elem in query(tree)]
        return ret

    def iterall(self, *tags: str) -> cabc.Iterator[etree._Element]:
        """Iterate over all elements in all trees by tags.

        Parameters
        ----------
        tags
            Optionally restrict the iterator to the given tags.
        """
        return itertools.chain.from_iterable(
            t.root.iter(*tags) for t in self.trees.values()
        )

    def iterall_xt(
        self,
        *xtypes: str,
        trees: cabc.Container[pathlib.PurePosixPath] | None = None,
    ) -> cabc.Iterator[etree._Element]:
        r"""Iterate over all elements in all trees by ``xsi:type``\ s.

        Parameters
        ----------
        xtypes
            Optionally restrict the iterator to these ``xsi:type``\ s
        trees
            Optionally restrict the iterator to elements that reside in
            any of the named trees.
        """
        xtset = self._nonempty_hashset(xtypes)
        if trees is None:
            files: cabc.Iterable[ModelFile] = self.trees.values()
        else:
            files = (v for k, v in self.trees.items() if k in trees)
        return itertools.chain.from_iterable(
            map(operator.methodcaller("iterall_xt", xtset), files)
        )

    def iterdescendants(
        self,
        root_elm: etree._Element,
        *tags: str,
    ) -> cabc.Iterator[etree._Element]:
        """Iterate over all descendants of ``root_elm``.

        This method will follow links into different fragment files and
        yield those elements as if they were part of the origin subtree.

        Parameters
        ----------
        root_elm
            The root element of the tree
        tags
            Only yield elements with a matching XML tag. If none are
            given, all elements are yielded.
        """
        tagset = self._nonempty_hashset(tags)
        it_stack = [root_elm.iterdescendants()]
        while it_stack:
            realelm = None
            try:
                elm = next(it_stack[-1])
            except StopIteration:
                it_stack.pop()
                continue

            if "href" in elm.attrib:  # Follow into the fragment
                href = elm.attrib["href"].split()[-1]
                realelm = self[href]
                it_stack.append(realelm.iterdescendants())

            if elm.tag in tagset:
                if realelm is not None:
                    yield realelm
                else:
                    yield elm

    def iterdescendants_xt(
        self,
        element: etree._Element,
        *xtypes: str,
    ) -> cabc.Iterator[etree._Element]:
        r"""Iterate over all descendants of ``element`` by ``xsi:type``.

        This method will follow links into different fragment files and
        yield those elements as if they were part of the origin subtree.

        Parameters
        ----------
        element
            The root element of the tree
        xtypes
            Only yield elements whose ``xsi:type`` matches one of those
            given here. If no types are given, all elements are yielded.
        """
        xtset = self._nonempty_hashset(xtypes)
        return (
            i
            for i in self.iterdescendants(element)
            if helpers.xtype_of(i) in xtset
        )

    def iterancestors(
        self,
        element: etree._Element,
        *tags: str,
    ) -> cabc.Iterator[etree._Element]:
        """Iterate over the ancestors of ``element``.

        This method will follow fragment links back to the origin point.

        Parameters
        ----------
        element
            The element to start at.
        tags
            Only yield elements that have the given XML tag.
        """
        tagset = self._nonempty_hashset(tags)
        visited_elements = []  # Basic protection against reference loops
        while True:
            parent = element.getparent()
            if parent is None:
                possible_sources = []
                for idtype in IDTYPES_RESOLVED:
                    with contextlib.suppress(KeyError):
                        possible_sources.append(
                            self._unfollow_href(element.attrib[idtype])
                        )
                assert 0 <= len(possible_sources) <= 1
                if not possible_sources:
                    break
                parent = possible_sources[0].getparent()
                if parent is None:
                    break
            element = parent

            assert element not in visited_elements
            visited_elements.append(element)
            if element.tag in tagset:
                yield element

    def iterchildren_xt(
        self, element: etree._Element, *xtypes: str
    ) -> cabc.Iterator[etree._Element]:
        r"""Iterate over the children of ``element``.

        This method will follow links into different fragment files and
        yield those elements as if they were direct children.

        Parameters
        ----------
        element
            The parent element under which to search for children.
        xtypes
            Only yield elements whose ``xsi:type`` matches one of those
            given here. If no types are given, all elements are yielded.
        """
        xtset = self._nonempty_hashset(xtypes)
        for child in element.iterchildren():
            child = self._follow_href(child)
            if helpers.xtype_of(child) in xtset:
                yield child

    def create_link(
        self,
        from_element: etree._Element,
        to_element: etree._Element,
        *,
        include_target_type: bool | None = None,
    ) -> str:
        """Create a link to ``to_element`` from ``from_element``.

        Parameters
        ----------
        from_element
            The source element of the link.
        to_element
            The target element of the link.
        include_target_type
            Whether to include the target type in cross-fragment link
            definitions.

            If set to True, it will always be included, False will
            always exclude it. Setting it to None (the default) will use
            a simple heuristic: It will be added *unless* the
            ``from_element`` is in a visual-only fragment (aird /
            airdfragment).

            Regardless of this setting, the target type will never be
            included if the link does not cross fragment boundaries.

        Returns
        -------
        str
            A link in one of the formats described by :meth:`follow_link`.
            Which format is used depends on whether ``from_element`` and
            ``to_element`` live in the the same fragment, and whether the
            ``include_target_type`` parameter is set.
        """
        to_uuids = set(to_element.keys()) & IDTYPES_RESOLVED
        try:
            to_uuid = next(iter(to_uuids))
        except StopIteration:
            raise ValueError(
                "to_element does not have a known ID attribute"
            ) from None
        to_uuid = to_element.attrib[to_uuid]

        from_fragment, _ = self._find_fragment(from_element)
        to_fragment, _ = self._find_fragment(to_element)
        assert from_fragment
        assert to_fragment

        if from_fragment == to_fragment:
            return f"#{to_uuid}"

        if include_target_type is None:
            include_target_type = from_fragment.suffix not in VISUAL_EXTS

        to_fragment = helpers.relpath_pure(to_fragment, from_fragment)
        link = urllib.parse.quote(str(to_fragment))
        if not include_target_type:
            return f"{link}#{to_uuid}"

        if to_type := helpers.xtype_of(to_element):
            return f"{to_type} {link}#{to_uuid}"
        return f"{link}#{to_uuid}"

    def follow_link(
        self,
        from_element: etree._Element | None,
        link: str,
    ) -> etree._Element:
        """Follow a single link and return the target element.

        Valid links have one of the following two formats:

        - Within the same fragment, a reference is the target's UUID
          prepended with a ``#``, for example
          ``#7a5b8b30-f596-43d9-b810-45ab02f4a81c``.

        - A reference to a different fragment contains the target's
          ``xsi:type`` and the path of the fragment, relative to the
          current one. For example, to link from ``main.capella`` into
          ``frag/logical.capellafragment``, the reference could be:
          ``org.polarsys.capella.core.data.capellacore:Constraint
          frag/logical.capellafragment#7a5b8b30-f596-43d9-b810-45ab02f4a81c``.
          To link back to the project root from there, it could look
          like: ``org.polarsys.capella.core.data.pa:PhysicalArchitecture
          ../main.capella#26e187b6-72e7-4872-8d8d-70b96243c96c``.

        Parameters
        ----------
        from_element
            The element at the start of the link. This is needed to verify
            cross-fragment links.
        link
            A string containing a valid link to another model element.

        Raises
        ------
        ValueError
            If the link is malformed
        FileNotFoundError
            If the target fragment is not loaded (only applicable if
            ``from_element`` is not None and ``fragment`` is part of the
            link)
        RuntimeError
            If the expected ``xsi:type`` does not match the actual
            ``xsi:type`` of the found target
        KeyError
            If the target cannot be found
        """
        del from_element

        linkmatch = helpers.CROSS_FRAGMENT_LINK.fullmatch(link)
        if not linkmatch:
            raise ValueError(f"Malformed link: {link!r}")
        xtype, fragment, ref = linkmatch.groups()
        del fragment  # TODO use 'fragment' to disambiguate multiple matches

        matches = []
        for tree in self.trees.values():
            with contextlib.suppress(KeyError):
                matches.append(tree[ref])
        if not matches:
            raise KeyError(link)
        if len(matches) > 1:
            raise KeyError(f"Ambiguous reference: {link!r}")
        if xtype is not None:
            actual_xtype = helpers.xtype_of(matches[0])
            if actual_xtype != xtype:
                raise TypeError(
                    f"Bad XML: Expected a {xtype!r}, got {actual_xtype!r}"
                )
        return matches[0]

    def follow_links(
        self,
        from_element: etree._Element | None,
        links: str,
        *,
        ignore_broken: bool = False,
    ) -> list[etree._Element]:
        """Follow multiple links and return all results as list.

        The format for an individual link is the same as accepted by
        :meth:`follow_link`. Multiple links are separated by a single space.

        If any target cannot be found, ``None`` will be inserted at that
        point in the returned list.

        Parameters
        ----------
        from_element
            The element at the start of the link. This is needed to verify
            cross-fragment links.
        links
            A string containing space-separated links as described in
            :meth:`follow_link`.
        ignore_broken
            Ignore broken references instead of raising a KeyError.

        Raises
        ------
        KeyError
            If any link points to a non-existing target. Can be
            suppressed with ``ignore_broken``.
        ValueError
            If any link is malformed.
        RuntimeError
            If any expected ``xsi:type`` does not match the actual
            ``xsi:type`` of the found target.
        """
        targets = []
        for part in helpers.split_links(links):
            try:
                targets.append(self.follow_link(from_element, part))
            except (KeyError, ValueError):
                if not ignore_broken:
                    raise
        return targets

    def _find_fragment(
        self, element: etree._Element
    ) -> tuple[pathlib.PurePosixPath, ModelFile]:
        root = collections.deque(
            itertools.chain([element], element.iterancestors()), 1
        )[0]
        for fragment, tree in self.trees.items():
            if tree.root is root:
                return (fragment, tree)
        raise ValueError("Element is not contained in any fragment")

    def _follow_href(self, element: etree._Element) -> etree._Element:
        href = element.get("href")
        if href is None:
            return element
        return self[href]

    def _unfollow_href(self, element_id: str) -> etree._Element:
        for tree in self.trees.values():
            element = tree.unfollow_href(element_id)
            if element is not None:
                return element
        raise KeyError(element_id)

    def find_fragment(self, element: etree._Element) -> pathlib.PurePosixPath:
        """Find the name of the fragment that contains ``element``."""
        return self._find_fragment(element)[0]

    def __getitem__(self, key: str) -> etree._Element:
        """Search all loaded fragments for the given UUID."""
        return self.follow_link(None, key)

    @staticmethod
    def _nonempty_hashset(tags: tuple[str, ...]) -> cabc.Container[str]:
        if not tags:
            return helpers.EverythingContainer()
        try:
            return set(tags)
        except TypeError:
            return tags

    def __find_metadata(self) -> etree._Element:
        afm = next(
            (
                f
                for p, f in self.trees.items()
                if p.parts[0] == "\x00" and p.suffix == ".afm"
            ),
            None,
        )
        if afm is None:
            raise RuntimeError("Cannot find .afm file in primary resource")
        metadata = next(afm.root.iter(METADATA_TAG), None)
        if metadata is None:
            raise RuntimeError("Cannot find <Metadata> in primary .afm file")
        LOGGER.debug("Found <Metadata> with ID %s", metadata.get("id"))
        return metadata

    def referenced_viewpoints(self) -> cabc.Iterator[tuple[str, str]]:
        metadata = self.__find_metadata()
        for i in metadata.iterchildren("viewpointReferences"):
            yield (i.attrib["vpId"], i.attrib["version"])

    def activate_viewpoint(self, name: str, version: str) -> None:
        """Activate (reference) a viewpoint in the model."""
        metadata = self.__find_metadata()
        for vpref in metadata.iterchildren("viewpointReferences"):
            if vpref.get("vpId") != name:
                continue

            vpver = vpref.get("version")
            if vpver == version:
                LOGGER.debug("Viewpoint %r v%s already active", name, version)
                return

            raise ValueError(
                f"Viewpoint {name} already active with version {vpver}"
                f" (requested: {version})"
            )

        with self.new_uuid(metadata) as new_id:
            vpref = metadata.makeelement(
                "viewpointReferences",
                attrib={"id": new_id, "vpId": name, "version": version},
            )
            metadata.append(vpref)
            self.idcache_index(vpref)

    def get_model_info(self) -> ModelInfo:
        """Return information about the loaded model."""
        root_handler = self.resources["\x00"].get_model_info()
        modelroot = next(self.iterall_xt(*ROOT_XT), None)
        viewpoints = dict(self.referenced_viewpoints())

        return ModelInfo(
            url=root_handler.url,
            title=getattr(modelroot, "attrib", {}).get("name"),
            entrypoint=self.entrypoint,
            viewpoints=viewpoints,
            resources={
                k: v.get_model_info() for k, v in self.resources.items()
            },
            capella_version=viewpoints.get(
                "org.polarsys.capella.core.viewpoint", "UNKNOWN"
            ),
        )

    @contextlib.contextmanager
    def write_tmp_project_dir(self) -> cabc.Iterator[pathlib.Path]:
        """Create a temporary directory with this model as Capella project.

        This method writes the loaded project files (model and library
        files, if any) into a temporary directory. The main model is
        always placed in a subdirectory called "main_model"; any library
        models are placed in subdirectories named after the resource
        that the library was loaded from. Additionally, a ``.project``
        file is generated in each subdirectory to allow direct import
        into Capella.

        The directory yielded from this method can be directly used as
        the workspace of a Capella instance.
        """
        with tempfile.TemporaryDirectory(prefix="workspace.") as tmp_dir_:
            workspace = pathlib.Path(tmp_dir_)
            LOGGER.debug("Writing project files to: %s", workspace)

            xml = E.projectDescription(
                nameobj := E.name("-"),
                E.comment(),
                E.projects(),
                E.buildSpec(),
                E.natures(E.nature(PROJECT_NATURE)),
            )
            for res in self.resources:
                LOGGER.debug("Generating .project file for resource %r", res)
                if res == "\x00":
                    res = "main_model"
                nameobj.text = res
                workspace.joinpath(res).mkdir()
                workspace.joinpath(res, ".project").write_bytes(
                    etree.tostring(xml, xml_declaration=True, encoding="utf-8")
                )
            for path in self.trees:
                if path.parts[0] == "\x00":
                    resname = "\x00"
                    dirname = "main_model"
                else:
                    resname = dirname = path.parts[0]
                path = pathlib.PurePosixPath(*path.parts[1:])

                dest_path = workspace.joinpath(dirname, path)
                LOGGER.debug(
                    "Copying file %s (%r) to %s", path, resname, dest_path
                )
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with (
                    self.resources[resname].open(path, "rb") as fsrc,
                    dest_path.open("wb") as fdst,
                ):
                    shutil.copyfileobj(fsrc, fdst)
            yield workspace
