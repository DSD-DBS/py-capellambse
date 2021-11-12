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
"""Implements a high-level interface to Capella projects."""
from __future__ import annotations

__all__ = ["MelodyModel"]

import logging
import os
import pathlib
import typing as t

from lxml import etree

import capellambse.helpers
import capellambse.pvmt
from capellambse import loader
from capellambse.loader import xmltools

from . import common, diagram  # isort:skip

# Architectural Layers
from .layers import oa, ctx, la, pa  # isort:skip

LOGGER = logging.getLogger(__name__)
XT_PROJECT = "org.polarsys.capella.core.data.capellamodeller:Project"
XT_LIBRARY = "org.polarsys.capella.core.data.capellamodeller:Library"
XT_SYSENG = "org.polarsys.capella.core.data.capellamodeller:SystemEngineering"


class MelodyModel:
    """Provides high-level access to a model.

    This class builds upon the lower-level
    :class:`capellambse.loader.core.MelodyLoader` to provide an
    abstract, high-level interface for easy access to various model
    aspects.
    """

    oa = common.ProxyAccessor(oa.OperationalAnalysis, rootelem=XT_SYSENG)
    sa = common.ProxyAccessor(ctx.SystemAnalysis, rootelem=XT_SYSENG)
    la = common.ProxyAccessor(la.LogicalArchitecture, rootelem=XT_SYSENG)
    pa = common.ProxyAccessor(pa.PhysicalArchitecture, rootelem=XT_SYSENG)
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
        diagram_cache: str | os.PathLike | None = None,
        diagram_cache_subdir: str | pathlib.PurePosixPath | None = None,
        **kwargs: t.Any,
    ) -> None:
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

              Examples:

              * ``git://git.example.com/model/coffeemaker.git``
              * ``git+https://git.example.com/model/coffeemaker.git``
              * ``git+ssh://git@git.example.com/model/coffeemaker.git``
        entrypoint
            Entrypoint from path to the main ``.aird`` file.
        revision
            The revision to use, if loading a model from a version
            control system like git. Defaults to the current HEAD. If
            the used VCS does not have a notion of "current HEAD", this
            argument is mandatory.
        disable_cache
            Disable local caching of remote content.
        update_cache
            Update the local cache. Defaults to ``True``, but can be
            disabled to reuse the last cached state.
        identity_file
            The identity file (private key) to use when connecting via
            SSH.
        known_hosts_file
            The ``known_hosts`` file to pass to SSH for verifying the
            server's host key.
        username
            The username to log in as remotely.
        password
            The password to use for logging in. Will be ignored when
            ``identity_file`` is passed as well.
        diagram_cache
            An optional place where to find pre-rendered, cached
            diagrams. When a diagram is found in this cache, it will be
            loaded from there instead of being rendered on access. Note
            that diagrams will only be loaded from there, but not be put
            back, i.e. to use it effectively, the cache has to be
            pre-populated.

            This argument accepts the same formats as ``path``.

            The file names looked up in the cache built in the format
            ``uuid.ext``, where ``uuid`` is the UUID of the diagram (as
            reported by ``diag_obj.uuid``) and ``ext`` is the render
            format. Example:

            - Diagram ID: ``_7FWu4KrxEeqOgqWuHJrXFA``
            - Render call: ``diag_obj.as_svg`` or ``diag_obj.render("svg")``
            - Cache file name: ``_7FWu4KrxEeqOgqWuHJrXFA.svg``

            *This argument is **not** passed to the file handler.*
        diagram_cache_subdir
            A sub-directory prefix to prepend to diagram UUIDs before
            looking them up in the ``diagram_cache``.

            *This argument is **not** passed to the file handler.*

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
        self._loader = loader.MelodyLoader(path, **kwargs)
        self.info = self._loader.get_model_info()

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
        """
        self._loader.save(**kw)

    def search(
        self, *xtypes: str | type[common.GenericElement]
    ) -> common.ElementList:
        r"""Search for all elements with any of the given ``xsi:type``\ s.

        If only one xtype is given, the return type will be
        :class:`common.ElementList`, otherwise it will be
        :class:`common.MixedElementList`.
        """
        xtypes_: list[str] = []
        for i in xtypes:
            if isinstance(i, type) and issubclass(i, common.GenericElement):
                xtypes_.append(common.build_xtype(i))
            elif ":" in i:
                xtypes_.append(i)
            else:
                for _, l in common.XTYPE_HANDLERS.items():
                    xtypes_.extend(t for t in l if t.endswith(":" + i))

        cls = (common.MixedElementList, common.ElementList)[len(xtypes) == 1]
        return cls(
            self,
            self._loader.find_by_xsi_type(*xtypes_),
            common.GenericElement,
        )

    def by_uuid(self, uuid: str) -> common.GenericElement:
        """Search the entire model for an element with the given UUID."""
        return common.GenericElement.from_model(self, self._loader[uuid])
