# Copyright 2021 DB Netz AG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Helps loading Capella models (including fragmented variants)."""
from __future__ import annotations

import collections
import collections.abc as cabc
import contextlib
import itertools
import logging
import operator
import os.path
import pathlib
import re
import sys
import typing as t
import urllib.parse
import uuid

from lxml import etree

import capellambse
from capellambse import helpers
from capellambse.loader import exs, filehandler
from capellambse.loader.filehandler import localfilehandler
from capellambse.loader.modelinfo import ModelInfo

LOGGER = logging.getLogger(__name__)
VALID_EXTS = frozenset(
    {
        ".afm",
        ".aird",
        ".airdfragment",
        ".capella",
        ".capellafragment",
        ".melodyfragment",
        ".melodymodeller",
    }
)
ERR_BAD_EXT = "Model file {} has an unsupported extension: {}"

IDTYPES = frozenset({"id", "uid", "xmi:id"})
IDTYPES_RESOLVED = frozenset(helpers.resolve_namespace(t) for t in IDTYPES)
CAP_VERSION = re.compile(r"Capella_Version_([\d.]+)")
CROSS_FRAGMENT_LINK = re.compile(
    r"""
    ^
    (?:
        (?:
            (?:(?P<xtype>[^ #]+)\ )?
            (?P<fragment>[^ #]+)
        )?
        \#
    )?
    (?P<uuid>[^ #]+)
    $
    """,
    re.VERBOSE,
)


def _verify_extension(filename: pathlib.PurePosixPath) -> None:
    """Check whether ``filename`` has a valid extension."""
    file = pathlib.PurePosixPath(filename)
    if file.suffix not in VALID_EXTS:
        raise TypeError(ERR_BAD_EXT.format(file, file.suffix))


def _find_refs(root: etree._Element) -> cabc.Iterable[str]:
    return itertools.chain(
        (x.split("#")[0] for x in root.xpath(".//referencedAnalysis/@href")),
        root.xpath(".//semanticResources/text()"),
    )


class ModelFile:
    """Represents a single file in the model (i.e. a fragment)."""

    __xtypecache: dict[str | None, list[etree._Element]]
    __idcache: dict[str, etree._Element]
    __hrefsources: dict[str, etree._Element]

    def __init__(
        self, filename: pathlib.PurePosixPath, handler: filehandler.FileHandler
    ) -> None:
        self.filename = filename
        self.filehandler = handler
        _verify_extension(filename)

        with handler.open(filename) as f:
            self.tree = etree.parse(
                f, etree.XMLParser(remove_blank_text=True, huge_tree=True)
            )

        self.root = self.tree.getroot()
        self.idcache_rebuild()

    def __getitem__(self, key: str) -> etree._Element:
        return self.__idcache[key]

    def idcache_index(self, subtree: etree._Element) -> None:
        """Index the IDs of ``subtree``."""
        for elm in subtree.iter():
            self.__xtypecache[helpers.xtype_of(elm)].append(elm)

            for idtype in IDTYPES_RESOLVED:
                elm_id = elm.get(idtype, None)
                if elm_id is None:
                    continue
                self.__idcache[elm_id] = elm

            href = elm.get("href")
            if href is not None:
                self.__hrefsources[href.split("#")[-1]] = elm

    def idcache_remove(self, source: str | etree._Element) -> None:
        """Remove the ID or all IDs below the source from the ID cache."""
        if isinstance(source, str):
            try:
                del self.__idcache[source]
            except KeyError:
                pass

        else:
            for elm in source.iter():
                self.__xtypecache[helpers.xtype_of(elm)].remove(elm)
                for idtype in IDTYPES_RESOLVED:
                    elm_id = elm.get(idtype, None)
                    if elm_id is None:
                        continue

                    try:
                        del self.__idcache[elm_id]
                    except KeyError:
                        pass
                href = elm.get("href")
                if href is not None:
                    del self.__hrefsources[href.split("#")[-1]]

    def idcache_rebuild(self) -> None:
        """Invalidate and rebuild this file's ID cache."""
        LOGGER.debug("Indexing file %s...", self.filename)
        self.__xtypecache = collections.defaultdict(list)
        self.__idcache = {}
        self.__hrefsources = {}
        self.idcache_index(self.root)
        LOGGER.debug("Cached %d element IDs", len(self.__idcache))

    def idcache_reserve(self, new_id: str) -> None:
        """Reserve the given ID for an element to be inserted later."""
        self.__idcache[new_id] = None

    def iterall_xt(
        self, xtypes: cabc.Container[str]
    ) -> cabc.Iterator[etree._Element]:
        """Iterate over all elements in this tree by ``xsi:type``."""
        for xtype, elms in self.__xtypecache.items():
            if xtype in xtypes:
                yield from elms

    def write_xml(
        self,
        filename: pathlib.PurePosixPath,
        encoding: str = "utf-8",
    ) -> None:
        """Write this file's XML into the file specified by ``path``."""
        LOGGER.debug("Saving tree %r to file %s", self, filename)
        if filename.suffix in {
            ".capella",
            ".capellafragment",
            ".melodyfragment",
            ".melodymodeller",
        }:
            line_length = exs.LINE_LENGTH
        else:
            line_length = sys.maxsize
        with self.filehandler.open(filename, "wb") as file:
            exs.write(
                self.tree, file, encoding=encoding, line_length=line_length
            )

    def unfollow_href(self, element_id: str) -> etree._Element:
        """ "Unfollow" a fragment link and return the placeholder element.

        If the given UUID is not linked to from this file, None is
        returned.
        """
        return self.__hrefsources.get(element_id)


class MelodyLoader:
    """Facilitates extensive access to Polarsys / Capella projects."""

    def __init__(
        self,
        path: str | os.PathLike,
        entrypoint: str | pathlib.PurePosixPath | None = None,
        **kwargs: t.Any,
    ) -> None:
        self.filehandler = filehandler.get_filehandler(path, **kwargs)
        self.entrypoint = self.__derive_entrypoint(entrypoint)

        self.trees: dict[pathlib.PurePosixPath, ModelFile] = {}
        self.__load_referenced_files(
            helpers.normalize_pure_path(pathlib.PurePosixPath(self.entrypoint))
        )

    def __derive_entrypoint(
        self, entrypoint: str | pathlib.PurePosixPath | None
    ) -> pathlib.PurePosixPath:
        if entrypoint:
            return helpers.normalize_pure_path(entrypoint)

        if isinstance(self.filehandler, localfilehandler.LocalFileHandler):
            basedir = self.filehandler.path
            assert isinstance(basedir, pathlib.Path)
            self.filehandler.path = basedir.parent
            return pathlib.PurePosixPath(basedir.name)

        raise ValueError("This type of file handler needs an ``entrypoint``")

    def __load_referenced_files(
        self,
        filename: pathlib.PurePosixPath,
    ) -> None:
        if filename in self.trees:
            return

        frag = ModelFile(filename, self.filehandler)
        self.trees[filename] = frag
        for ref in _find_refs(frag.root):
            ref_name = helpers.normalize_pure_path(
                urllib.parse.unquote(ref), base=filename.parent
            )
            self.__load_referenced_files(ref_name)

    def save(self, **kw: t.Any) -> None:
        """Save all model files back to their original locations.

        Parameters
        ----------
        kw
            Additional keyword arguments accepted by the file handler in
            use. Please see the respective documentation for more info.

        See Also
        --------
        capellambse.loader.filehandler.localfilehandler.LocalFileHandler.write_transaction :
            Accepted ``**kw`` when using local directories
        capellambse.loader.filehandler.gitfilehandler.GitFileHandler.write_transaction :
            Accepted ``**kw`` when using ``git://`` and similar URLs
        """
        LOGGER.debug("Saving model %r", self.get_model_info().title)
        with self.filehandler.write_transaction(**kw) as unsupported_kws:
            if unsupported_kws:
                LOGGER.warning(
                    "Ignoring unsupported transaction parameters: %s",
                    ", ".join(repr(k) for k in unsupported_kws),
                )
            for fname, tree in self.trees.items():
                tree.write_xml(fname)

    def idcache_index(self, subtree: etree._Element) -> None:
        """Index the IDs of ``subtree``.

        This method must be called after adding ``subtree`` to the XML
        tree.
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
        """
        try:
            _, tree = self._find_fragment(subtree)
        except ValueError:
            raise ValueError(
                "Call idcache_remove() before removing the subtree"
            ) from None

        tree.idcache_remove(subtree)

    def idcache_rebuild(self) -> None:
        r"""Rebuild the ID caches of all :class:`ModelFile`\ s."""
        for tree in self.trees.values():
            tree.idcache_rebuild()

    def generate_uuid(self, parent: etree._Element) -> str:
        """Generate a unique UUID for a new child of ``parent``.

        The generated ID is guaranteed to be unique across all currently
        loaded fragments.
        """
        _, tree = self._find_fragment(parent)

        while True:
            new_id = str(uuid.uuid4())
            try:
                self[new_id]
            except KeyError:
                tree.idcache_reserve(new_id)
                return new_id

    @contextlib.contextmanager
    def new_uuid(
        self, parent: etree._Element
    ) -> cabc.Generator[str, None, None]:
        """Context Manager around :meth:`generate_uuid()`.

        This context manager yields a newly generated model-wide unique
        UUID that can be inserted into a new element during the ``with``
        block.  It tries to keep the ID cache consistent in some harder
        to manage edge cases, like exceptions being thrown.
        Additionally it checks that the generated UUID was actually used
        in the tree; not using it before the ``with`` block ends is an
        error and provokes an Exception.

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
        """
        _, tree = self._find_fragment(parent)
        new_uuid = self.generate_uuid(parent)

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

        Parameters
        ----------
        query
            The XPath query
        namespaces
            Namespaces used in the query.  Defaults to all known
            namespaces.
        roots
            A list of XML elements to use as roots for the query.
            Defaults to all tree roots.
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

        The tuples have the fragment where the match was found as first
        element, and the LXML element as second one.

        Parameters
        ----------
        query
            The XPath query
        namespaces
            Namespaces used in the query.  Defaults to all known
            namespaces.
        roots
            A list of XML elements to use as roots for the query.
            Defaults to all tree roots.
        """
        if namespaces is None:
            namespaces = capellambse.NAMESPACES

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
            roots = [(k, t.root) for k, t in self.trees.items()]
        elif isinstance(roots, etree._Element):
            roots = [(self._find_fragment(roots)[0], roots)]
        elif isinstance(roots, cabc.Iterable):
            roots = [(self._find_fragment(r)[0], r) for r in roots]
        else:
            raise TypeError(
                f"`roots` must be an XML element or a list thereof, not {type(roots).__name__}"
            )

        ret = []
        for fragment, tree in roots:
            ret += [follow_href(fragment, elem) for elem in query(tree)]
        return ret

    def find_by_xsi_type(
        self,
        *xsi_types: str,
        roots: etree._Element | cabc.Iterable[etree._Element] = None,
    ) -> list[etree._Element]:
        r"""Find all elements matching any of the given ``xsi:type``\ s.

        Parameters
        ----------
        xsi_types
            ``xsi:type`` strings to match, for example
            "org.polarsys.capella.core.data.cs:InterfacePkg"
        roots
            A list of XML elements to use as roots for the query.
            Defaults to all tree roots.
        """
        if not xsi_types:
            return []

        if roots is None:
            return list(self.iterall_xt(*xsi_types))
        elif isinstance(roots, etree._Element):
            roots = (roots,)

        xtset = self._nonempty_hashset(xsi_types)
        del xsi_types

        return [
            i
            for i in itertools.chain.from_iterable(roots)
            if helpers.xtype_of(i) in xtset
        ]

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
    ) -> cabc.Iterator[etree._Element]:
        r"""Iterate over all elements in all trees by ``xsi:type``\ s.

        Parameters
        ----------
        xtypes
            Optionally restrict the iterator to these ``xsi:type``\ s
        """
        xtset = self._nonempty_hashset(xtypes)
        return itertools.chain.from_iterable(
            map(
                operator.methodcaller("iterall_xt", xtset), self.trees.values()
            )
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
            Element tags to filter for
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
            Elements that have any of these ``xsi:type``\ s will be
            yielded.  If nothing is given here, all elements will be
            yielded.
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
        """
        tagset = self._nonempty_hashset(tags)
        visited_elements = []  # Basic protection against reference loops
        while True:
            parent = element.getparent()
            if parent is None:
                possible_sources = []
                for idtype in IDTYPES_RESOLVED:
                    try:
                        possible_sources.append(
                            self._unfollow_href(element.attrib[idtype])
                        )
                    except KeyError:
                        pass
                assert 0 <= len(possible_sources) <= 1
                if possible_sources:
                    parent = possible_sources[0].getparent()
                else:
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

        If ``xsi:type``\ s are given in ``xtypes``, restrict yielded
        elements to the ones with matching type.
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
    ) -> str:
        """Create a link to ``to_element`` from ``from_element``.

        The resulting link is valid for insertion into ``from_element``
        or any of its children, and will reference ``to_element`` either
        in the same or a different fragment.  It has one of the
        following three formats:

        1.  Within the same fragment: ``#UUID``
        2.  Across different fragments: ``target_xsitype relpath#UUID``
        3.  Across different fragments, if the target does not have an
            ``xsi:type``: ``relpath#UUID``

        Parameters
        ----------
        from_element
            The source element of the link.
        to_element
            The target element of the link.
        """
        to_uuids = set(to_element.keys()) & IDTYPES_RESOLVED
        try:
            to_uuid = next(iter(to_uuids))
        except StopIteration:
            raise ValueError(
                "to_element does not have a known ID attribute"
            ) from None
        to_uuid = to_element.get(to_uuid)

        # Find the fragments corresponding to each tree
        from_fragment, _ = self._find_fragment(from_element)
        to_fragment, _ = self._find_fragment(to_element)
        assert from_fragment and to_fragment

        if from_fragment == to_fragment:
            return f"#{to_uuid}"

        to_fragment = pathlib.PurePosixPath(
            os.path.relpath(to_fragment, from_fragment.parent)
        )
        link = urllib.parse.quote(str(to_fragment))
        to_type = helpers.xtype_of(to_element)
        if to_type is not None:
            return f"{to_type} {link}#{to_uuid}"
        return f"{link}#{to_uuid}"

    def follow_link(
        self,
        from_element: etree._Element | None,
        link: str,
    ) -> etree._Element:
        """Follow a single link and return the target element.

        The link is considered relative to the ``from_element``, if
        given. The accepted formats are as follows::

            xtype fragment#UUID
            fragment#UUID
            #UUID
            UUID

        Where:

        *   ``xtype`` is the target element's ``xsi:type``.  If given
            and it does not match, an exception is raised.
        *   ``fragment`` is the fragment file in which to find the
            target element.  If not given, first the source fragment
            will be searched, and if unsuccessful, the search will be
            extended to all fragments.
        *   ``UUID`` is the unique ``id`` of the target element.

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
        linkmatch = CROSS_FRAGMENT_LINK.fullmatch(link)
        if not linkmatch:
            raise ValueError(f"Malformed link: {link!r}")
        xtype, fragment, ref = linkmatch.groups()
        if fragment is not None:
            fragment = urllib.parse.unquote(fragment)

        def find_trees(
            from_element: etree._Element | None,
            fragment: pathlib.PurePosixPath | None,
        ) -> cabc.Iterable[ModelFile]:
            if fragment and from_element is None:
                return (
                    v for k, v in self.trees.items() if k.name == fragment.name
                )
            elif fragment:
                sourcefragment = self._find_fragment(from_element)[0]
                fragment = capellambse.helpers.normalize_pure_path(
                    fragment, base=sourcefragment.parent
                )
                try:
                    return [self.trees[fragment]]
                except KeyError:  # pragma: no cover
                    raise FileNotFoundError(
                        f"Fragment not loaded: {fragment}"
                    ) from None
            else:
                sourcefragment = pathlib.PurePosixPath("/")
                if from_element is not None:
                    sourcefragment = self._find_fragment(from_element)[0]
                return map(
                    operator.itemgetter(1),
                    sorted(
                        self.trees.items(),
                        key=lambda tree: tree[0].name != sourcefragment.name,
                    ),
                )

        trees = find_trees(
            from_element,
            pathlib.PurePosixPath(fragment) if fragment else None,
        )

        matches = []
        for tree in trees:
            try:
                matches.append(tree[ref])
            except KeyError:
                pass
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
    ) -> list[etree._Element | None]:
        """Follow multiple links and return all results as list.

        The format for an individual link is the same as accepted by
        :meth:`follow_link`.  Multiple links must be given as a single
        space-separated string.

        If any target cannot be found, ``None`` will be inserted at that
        point in the returned list.

        Raises
        ------
        ValueError
            If any link is malformed.
        RuntimeError
            If any expected ``xsi:type`` does not match the actual
            ``xsi:type`` of the found target.
        """
        targets = []
        next_xtype = None
        for part in links.split():
            if "#" not in part:
                if next_xtype is not None:
                    raise ValueError(f"Malformed link definition: {links}")
                next_xtype = part
                continue

            if next_xtype is not None:
                part = f"{next_xtype} {part}"
            try:
                targets.append(self.follow_link(from_element, part))
            except KeyError:
                targets.append(None)
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

    def get_model_info(self) -> ModelInfo:
        """Return the Capella version found in the leading comment."""
        info = self.filehandler.get_model_info()
        info.capella_version = "UNKNOWN"

        for fragment, tree in self.trees.items():
            if fragment.name.endswith((".capella", ".melodymodeller")):
                semantic_tree = tree
                break
        else:
            LOGGER.warning(
                "Cannot find capella version: No main semantic tree found!"
            )
            return info

        try:
            comment = semantic_tree.tree.xpath("/comment()")
            info.capella_version = CAP_VERSION.match(comment[0].text).group(1)  # type: ignore[union-attr]
        except (AttributeError, IndexError):
            LOGGER.warning(
                "Cannot find Capella version: No version comment found"
            )

        return info
