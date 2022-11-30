# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Implements a high-level interface to Capella projects."""
from __future__ import annotations

__all__ = ["ElementList", "GenericElement", "MelodyModel"]

import collections.abc as cabc
import logging
import os
import pathlib
import typing as t

from lxml import etree

import capellambse
import capellambse.helpers
import capellambse.pvmt
from capellambse import loader
from capellambse.loader import xmltools

from . import common, diagram  # isort:skip

# Architectural Layers
from .layers import oa, ctx, la, pa  # isort:skip

# Exports
from .common import ElementList, GenericElement  # isort:skip

LOGGER = logging.getLogger(__name__)
XT_PROJECT = "org.polarsys.capella.core.data.capellamodeller:Project"
XT_LIBRARY = "org.polarsys.capella.core.data.capellamodeller:Library"
XT_SYSENG = "org.polarsys.capella.core.data.capellamodeller:SystemEngineering"


class MelodyModel:
    """Provides high-level access to a model.

    This class builds upon the lower-level
    :class:`~capellambse.loader.core.MelodyLoader` to provide an
    abstract, high-level interface for easy access to various model
    aspects.
    """

    oa = common.DirectProxyAccessor(oa.OperationalAnalysis, rootelem=XT_SYSENG)
    sa = common.DirectProxyAccessor(ctx.SystemAnalysis, rootelem=XT_SYSENG)
    la = common.DirectProxyAccessor(la.LogicalArchitecture, rootelem=XT_SYSENG)
    pa = common.DirectProxyAccessor(
        pa.PhysicalArchitecture, rootelem=XT_SYSENG
    )
    diagrams = diagram.DiagramAccessor(
        None, cacheattr="_MelodyModel__diagram_cache"
    )

    uuid = xmltools.AttributeProperty(
        "_element",
        "id",
        writable=False,
        __doc__="The unique ID of the model's root element.",
    )
    name = xmltools.AttributeProperty(
        "_element", "name", __doc__="The name of this model."
    )

    _diagram_cache: loader.FileHandler
    _diagram_cache_subdir: pathlib.PurePosixPath

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        diagram_cache: (
            str | os.PathLike | loader.FileHandler | dict[str, t.Any] | None
        ) = None,
        diagram_cache_subdir: str | pathlib.PurePosixPath | None = None,
        jupyter_untrusted: bool = False,
        **kwargs: t.Any,
    ) -> None:
        # pylint: disable=line-too-long
        """Load a project.

        For complete information on which exact ``kwargs`` are
        supported, consult the documentation of the used file handler.
        Refer to the "See Also" section for a collection of links.

        Below are some common parameter names and their usual meanings.
        Not all file handlers support all parameters.

        .. note::
            Passing in arguments that are not accepted by the selected
            file handler will result in an exception being raised.
            Similarly, leaving out arguments that are required by the
            file handler will also result in an exception.

        Parameters
        ----------
        path
            Path or URL to the project. The following formats are
            accepted:

            * A path to a local ``.aird`` file.
            * A path to a local directory (requires ``entrypoint``).
            * An SCP-style short URL, which will be treated as referring
              to a Git repository.

              Example: ``git@github.com:DSD-DBS/py-capellambse.git``
            * A remote URL, with a protocol or prefix that indicates
              which file handler to invoke (requires ``entrypoint``).

              Some examples:

              * ``git://git.example.com/model/coffeemaker.git``
              * ``git+https://git.example.com/model/coffeemaker.git``
              * ``git+ssh://git@git.example.com/model/coffeemaker.git``

              .. note:: Depending on the exact file handler, saving back
                 to a remote location might fail with ``update_cache``
                 set to ``False``. See :meth:`save` for more details.
        entrypoint: str
            Entrypoint from path to the main ``.aird`` file.
        revision: str
            The revision to use, if loading a model from a version
            control system like git. Defaults to the current HEAD. If
            the used VCS does not have a notion of "current HEAD", this
            argument is mandatory.
        disable_cache: bool
            Disable local caching of remote content.
        update_cache: bool
            Update the local cache. Defaults to ``True``, but can be
            disabled to reuse the last cached state.
        identity_file: str | pathlib.Path
            The identity file (private key) to use when connecting via
            SSH.
        known_hosts_file: str | pathlib.Path
            The ``known_hosts`` file to pass to SSH for verifying the
            server's host key.
        username: str
            The username to log in as remotely.
        password: str
            The password to use for logging in. Will be ignored when
            ``identity_file`` is passed as well.
        diagram_cache: str | pathlib.Path | ~capellambse.loader.filehandler.FileHandler | dict[str, ~typing.Any]
            An optional place where to find pre-rendered, cached
            diagrams. When a diagram is found in this cache, it will be
            loaded from there instead of being rendered on access. Note
            that diagrams will only be loaded from there, but not be put
            back, i.e. to use it effectively, the cache has to be
            pre-populated.

            This argument accepts the following values:

            - ``None``, in which case all diagrams will be rendered
              internally the first time they are used.
            - A path to a local directory.
            - A URL just like for the ``path`` argument.
            - A dictionary with the arguments to a
              :py:class:`~capellambse.FileHandler`. The dict's ``path``
              key will be analyzed to determine the correct FileHandler
              class.
            - An instance of :py:class:`~capellambse.FileHandler`, which
              will be used directly.

            .. warning:: When using the diagram cache, always make sure
               that the cached diagrams actually match the model version
               that is being used. There is no way to check this
               automatically.

            The file names looked up in the cache built in the format
            ``uuid.ext``, where ``uuid`` is the UUID of the diagram (as
            reported by ``diag_obj.uuid``) and ``ext`` is the render
            format. Example:

            - Diagram ID: ``_7FWu4KrxEeqOgqWuHJrXFA``
            - Render call: ``diag_obj.as_svg`` or ``diag_obj.render("svg")``
            - Cache file name: ``_7FWu4KrxEeqOgqWuHJrXFA.svg``

            *This argument is **not** passed to the file handler.*
        diagram_cache_subdir: str
            A sub-directory prefix to prepend to diagram UUIDs before
            looking them up in the ``diagram_cache``.

            *This argument is **not** passed to the file handler.*
        jupyter_untrusted: bool
            If set to True, restricts or disables some features that are
            unavailable in an untrusted Jupyter environment. Currently
            this only disables the SVG format as rich display option for
            Ipython, which is needed to avoid rendering issues with
            Github's Jupyter notebook viewer.

        See Also
        --------
        capellambse.loader.filehandler.FileHandler :
            Abstract super class for file handlers. Contains information
            needed for implementing custom handlers.
        capellambse.loader.filehandler.localfilehandler.LocalFileHandler :
            The file handler responsible for local files and
            directories.
        capellambse.loader.filehandler.gitfilehandler.GitFileHandler :
            The file handler implementing the ``git://`` protocol.
        capellambse.loader.filehandler.http.HTTPFileHandler :
            A simple ``http(s)://`` file handler.
        """
        # pylint: enable=line-too-long
        capellambse.load_model_extensions()

        self._loader = loader.MelodyLoader(path, **kwargs)
        self.info = self._loader.get_model_info()
        self.jupyter_untrusted = jupyter_untrusted

        try:
            self._pvext = capellambse.pvmt.load_pvmt_from_model(self._loader)
        except ValueError as err:
            LOGGER.warning(
                "Cannot load PVMT extension: %s: %s", type(err).__name__, err
            )
            LOGGER.warning("Property values are not available in this model")
            self._pvext = None

        if diagram_cache:
            if diagram_cache == path:
                self._diagram_cache = self._loader.filehandler
            elif isinstance(diagram_cache, loader.FileHandler):
                self._diagram_cache = diagram_cache
            elif isinstance(diagram_cache, cabc.Mapping):
                self._diagram_cache = loader.get_filehandler(**diagram_cache)
            else:
                self._diagram_cache = loader.get_filehandler(diagram_cache)
            self._diagram_cache_subdir = pathlib.PurePosixPath(
                diagram_cache_subdir or "/"
            )

    @property
    def _element(self) -> etree._Element:
        for tree in self._loader.trees.values():
            if capellambse.helpers.xtype_of(tree.root) in {
                XT_PROJECT,
                XT_LIBRARY,
            }:
                return tree.root
        raise TypeError("No viable root element found")

    @property
    def _model(self) -> MelodyModel:
        return self

    def save(self, **kw: t.Any) -> None:
        # pylint: disable=line-too-long
        """Save the model back to where it was loaded from.

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

        Notes
        -----
        With a file handler that contacts a remote location (such as the
        :class:`~capellambse.loader.filehandler.gitfilehandler.GitFileHandler`
        with non-local repositories), saving might fail if the local
        state has gone out of sync with the remote state. To avoid this,
        always leave the ``update_cache`` parameter at its default value
        of ``True`` if you intend to save changes.
        """
        # pylint: enable=line-too-long
        self._loader.save(**kw)

    def search(
        self,
        *xtypes: str | type[common.GenericElement],
        below: common.GenericElement | None = None,
    ) -> common.ElementList:
        r"""Search for all elements with any of the given ``xsi:type``\ s.

        If only one xtype is given, the return type will be
        :class:`common.ElementList`, otherwise it will be
        :class:`common.MixedElementList`.

        If no ``xtypes`` are given at all, this method will return an
        exhaustive list of all (semantic) model objects that have an
        ``xsi:type`` set.

        Parameters
        ----------
        xtypes
            The ``xsi:type``\ s to search for, or the classes
            corresponding to them (or a mix of both).
        below
            A model element to constrain the search. If given, only
            those elements will be returned that are (immediate or
            nested) children of this element. This option takes into
            account model fragmentation, but it does not treat link
            elements specially.
        """
        xtypes_: list[str] = []
        for i in xtypes:
            if isinstance(i, type) and issubclass(i, common.GenericElement):
                xtypes_.append(common.build_xtype(i))
            elif ":" in i:
                xtypes_.append(i)
            else:
                suffix = ":" + i
                matching_types: list[str] = []
                for l in common.XTYPE_HANDLERS.values():
                    matching_types.extend(t for t in l if t.endswith(suffix))
                if not matching_types:
                    raise ValueError(f"Unknown incomplete type name: {i}")
                xtypes_.extend(matching_types)

        cls = (common.MixedElementList, common.ElementList)[len(xtypes_) == 1]
        trees = {
            k
            for k, v in self._loader.trees.items()
            if v.fragment_type is loader.FragmentType.SEMANTIC
        }
        matches = self._loader.iterall_xt(*xtypes_, trees=trees)
        if below is not None:
            matches = (
                i for i in matches if below._element in i.iterancestors()
            )
        return cls(self, list(matches), common.GenericElement)

    def by_uuid(self, uuid: str) -> common.GenericElement:
        """Search the entire model for an element with the given UUID."""
        return common.GenericElement.from_model(self, self._loader[uuid])
