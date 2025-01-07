# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = ["MelodyModel", "ModelInfo"]

import collections.abc as cabc
import dataclasses
import itertools
import logging
import os
import typing as t

from lxml import etree

import capellambse
import capellambse.helpers
from capellambse import _diagram_cache, aird, filehandler, loader

from . import _descriptors, _obj, _xtype, diagram

# `pathlib` is referenced by the `dataclasses` auto-generated init.
# Sphinx-autodoc-typehints needs this import here to resolve the forward ref.
import pathlib  # isort: skip  # noqa: F401

LOGGER = logging.getLogger(__name__)


class MelodyModel:
    """Provides high-level access to a model.

    This class builds upon the lower-level
    :class:`~capellambse.loader.core.MelodyLoader` to provide an
    abstract, high-level interface for easy access to various model
    aspects.
    """

    @property
    def project(self) -> capellambse.metamodel.capellamodeller.Project:
        import capellambse.metamodel as mm

        target_xt = {
            _xtype.build_xtype(mm.capellamodeller.Project),
            _xtype.build_xtype(mm.capellamodeller.Library),
        }
        roots: list[etree._Element] = []
        for fname, frag in self._loader.trees.items():
            if fname.parts[0] != "\x00":
                continue
            elem = frag.root
            if elem.tag == "{http://www.omg.org/XMI}XMI":
                try:
                    elem = next(iter(elem))
                except StopIteration:
                    continue
            if capellambse.helpers.xtype_of(elem) not in target_xt:
                continue
            roots.append(elem)

        if len(roots) < 1:
            raise RuntimeError("No root project or library found")
        if len(roots) > 1:
            raise RuntimeError(f"Found {len(roots)} Project/Library objects")
        obj = _obj.ModelElement.from_model(self, roots[0])
        assert isinstance(obj, mm.capellamodeller.Project)
        return obj

    @property
    def oa(self) -> capellambse.metamodel.oa.OperationalAnalysis:
        return self.project.model_root.oa

    @property
    def sa(self) -> capellambse.metamodel.sa.SystemAnalysis:
        return self.project.model_root.sa

    @property
    def la(self) -> capellambse.metamodel.la.LogicalArchitecture:
        return self.project.model_root.la

    @property
    def pa(self) -> capellambse.metamodel.pa.PhysicalArchitecture:
        return self.project.model_root.pa

    def enumeration_property_types(
        self,
    ) -> _obj.ElementList[
        capellambse.metamodel.capellacore.EnumerationPropertyType
    ]:
        return self.project.model_root.enumeration_property_types

    def property_value_packages(
        self,
    ) -> _obj.ElementList[capellambse.metamodel.capellacore.PropertyValuePkg]:
        return self.project.model_root.property_value_packages

    @property
    def uuid(self) -> str:
        """The unique ID of the model's root element."""
        return self.project.uuid

    @property
    def name(self) -> str:
        """The name of this model."""
        return self.project.name

    @name.setter
    def name(self, value: str) -> None:
        self.project.name = value

    diagrams = diagram.DiagramAccessor(
        None, cacheattr="_MelodyModel__diagram_cache"
    )

    diagram_cache: filehandler.FileHandler | None

    __diagram_cache: t.Any
    """Stores proxy instances for Diagram.

    Not to be confused with the public "diagram_cache", which is where
    the pre-rendered content for those instances is fetched from.
    """

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        diagram_cache: (
            str
            | os.PathLike
            | filehandler.FileHandler
            | dict[str, t.Any]
            | None
        ) = None,
        fallback_render_aird: bool = False,
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
        diagram_cache
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
              :py:class:`~capellambse.filehandler.abc.FileHandler`. The
              dict's ``path`` key will be analyzed to determine the
              correct FileHandler class.
            - An instance of
              :class:`~capellambse.filehandler.abc.FileHandler`, which
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
        fallback_render_aird: bool
            If set to True, enable the internal engine to render
            diagrams that were not found in the pre-rendered cache.
            Defaults to False, which means an exception is raised
            instead. Ignored if no ``diagram_cache`` was specified.
        **kwargs
            Additional arguments are passed on to the underlying
            :class:`~capellambse.loader.core.MelodyLoader`, which in
            turn passes it on to the primary resource's FileHandler.

        See Also
        --------
        capellambse.filehandler.FileHandler :
            Abstract super class for file handlers. Contains information
            needed for implementing custom handlers.
        capellambse.filehandler.local.LocalFileHandler :
            The file handler responsible for local files and
            directories.
        capellambse.filehandler.git.GitFileHandler :
            The file handler implementing the ``git://`` protocol.
        capellambse.filehandler.http.HTTPFileHandler :
            A simple ``http(s)://`` file handler.
        """
        capellambse.load_model_extensions()

        self._loader = loader.MelodyLoader(path, **kwargs)
        self._fallback_render_aird = fallback_render_aird

        if diagram_cache:
            if diagram_cache == path:
                self.diagram_cache = self._loader.filehandler
            elif isinstance(diagram_cache, filehandler.FileHandler):
                self.diagram_cache = diagram_cache
            elif isinstance(diagram_cache, cabc.Mapping):
                self.diagram_cache = filehandler.get_filehandler(
                    **diagram_cache
                )
            else:
                self.diagram_cache = filehandler.get_filehandler(diagram_cache)
        else:
            self.diagram_cache = None

    @property
    def resources(self) -> dict[str, filehandler.FileHandler]:
        return self._loader.resources

    def save(self, **kw: t.Any) -> None:
        """Save the model back to where it was loaded from.

        Parameters
        ----------
        kw
            Additional keyword arguments accepted by the file handler in
            use. Please see the respective documentation for more info.

        See Also
        --------
        capellambse.filehandler.localfilehandler.LocalFileHandler.write_transaction :
            Accepted ``**kw`` when using local directories
        capellambse.filehandler.git.GitFileHandler.write_transaction :
            Accepted ``**kw`` when using ``git://`` and similar URLs

        Notes
        -----
        With a file handler that contacts a remote location (such as the
        :class:`~capellambse.filehandler.git.GitFileHandler`
        with non-local repositories), saving might fail if the local
        state has gone out of sync with the remote state. To avoid this,
        always leave the ``update_cache`` parameter at its default value
        of ``True`` if you intend to save changes.
        """
        self._loader.save(**kw)

    def search(
        self,
        *xtypes: str | type[_obj.ModelObject],
        below: _obj.ModelElement | None = None,
    ) -> _obj.ElementList:
        r"""Search for all elements with any of the given ``xsi:type``\ s.

        If only one xtype is given, the return type will be
        :class:`~capellambse.model.ElementList`, otherwise it will be
        :class:`~capellambse.model.MixedElementList`.

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
        for xtype in xtypes:
            if isinstance(xtype, type):
                xtypes_.append(_xtype.build_xtype(xtype))
            elif ":" in xtype:
                xtypes_.append(xtype)
            elif xtype in {"GenericElement", "ModelElement", "ModelObject"}:
                xtypes_.clear()
                break
            else:
                suffix = ":" + xtype
                matching_types: list[str] = []
                for i in _xtype.XTYPE_HANDLERS.values():
                    matching_types.extend(c for c in i if c.endswith(suffix))
                if not matching_types:
                    raise ValueError(f"Unknown incomplete type name: {xtype}")
                xtypes_.extend(matching_types)

        cls = (_obj.MixedElementList, _obj.ElementList)[len(xtypes_) == 1]

        trees = {
            k
            for k, v in self._loader.trees.items()
            if v.fragment_type is loader.FragmentType.SEMANTIC
        }
        matches = self._loader.iterall_xt(*xtypes_, trees=trees)

        if not xtypes_ or "viewpoint:DRepresentationDescriptor" in xtypes_:
            matches = itertools.chain(
                matches,
                aird.enumerate_descriptors(self._loader),
            )

        if below is not None:
            matches = (
                i
                for i in matches
                if below._element in self._loader.iterancestors(i)
            )
        return cls(self, list(matches), _obj.ModelElement)

    def by_uuid(self, uuid: str) -> t.Any:
        """Search the entire model for an element with the given UUID."""
        return _obj.ModelElement.from_model(self, self._loader[uuid])

    def find_references(
        self, target: _obj.ModelObject | str, /
    ) -> cabc.Iterator[tuple[t.Any, str, int | None]]:
        """Search the model for references to the given object.

        Parameters
        ----------
        target
            The target object to search for.

        Yields
        ------
        tuple[ModelObject, str, int | None]
            A 3-tuple containing the referencing model object, the
            attribute on that object, and an optional index. If the
            attribute contains a list of objects, the index shows the
            index into the list that was found. Otherwise the index is
            None.
        """
        if isinstance(target, str):
            if not capellambse.helpers.is_uuid_string(target):
                raise ValueError(f"Malformed UUID: {target!r}")
            uuid: str = target
            target = self.by_uuid(target)

        else:
            if target._model is not self:
                raise ValueError(
                    "Cannot find references to objects from different models"
                )
            uuid = getattr(target, "uuid", "")
            if not capellambse.helpers.is_uuid_string(uuid):
                raise ValueError(f"Malformed or missing UUID for {target!r}")

        for elem in self._loader.xpath(
            f"//*[@*[contains(., '#{uuid}')] | */@*[contains(., '#{uuid}')]]",
            roots=[
                i.root
                for i in self._loader.trees.values()
                if i.fragment_type != loader.FragmentType.VISUAL
            ],
        ):
            obj = _obj.ModelElement.from_model(self, elem)
            for attr in _reference_attributes(type(obj)):
                if attr.startswith("_"):
                    continue

                try:
                    value = getattr(obj, attr)
                except Exception:
                    continue

                if isinstance(value, _obj.ModelElement) and value == target:
                    yield (obj, attr, None)
                elif isinstance(value, _obj.ElementList):
                    try:
                        idx = value.index(target)
                    except ValueError:
                        continue
                    yield (obj, attr, idx)

    def update_diagram_cache(
        self,
        capella_cli: str,
        image_format: t.Literal["bmp", "gif", "jpg", "png", "svg"] = "svg",
        *,
        create_index: bool = False,
        force: t.Literal["docker", "exe"] | None = None,
        background: bool = True,
    ) -> None:
        r"""Update the diagram cache if one has been specified.

        If a ``diagram_cache`` has been specified while loading a
        Capella model it will be updated when this function is called.

        The diagram cache will be populated by executing the Capella
        function "Export representations as images" which is normally
        accessible via the context menu of an ``.aird`` node in
        Capella's project explorer. The export of diagrams happens with
        the help of Capella's command line interface (CLI).

        The CLI of Capella must be specified by the caller. It is
        possible to work with a local installation or a Docker image of
        an individual Capella bundle.

        At the moment it is supported to run a Docker image using the
        container system Docker and the ``docker`` executable must be in
        the ``PATH`` environment variable.

        Parameters
        ----------
        capella_cli
            The Capella CLI to use when exporting diagrams from the
            given Capella model. The provided string can come with a
            ``"{VERSION}"`` placeholder. If specified, this placeholder
            will be replaced by the x.y.z formatted version of Capella
            that has been used when the given Capella model was last
            saved. After consideration of the optional placeholder this
            function will first check if the value of ``capella_cli``
            points to a local Capella executable (that can be an
            absolute path or an executable/ symbolic link that has been
            made available via the environment variable ``PATH``). If no
            executable can be found it is expected that ``capella_cli``
            represents a Docker image name for an image that behaves
            like the Capella CLI. For the case of passing a Docker image
            name through ``capella_cli`` this means it is assumed that
            something like the following

            .. code-block:: bash

                docker run --rm -it <capella_cli> -nosplash \
                    -consolelog -app APP -appid APPID

            will work.
            The parameter ``force`` can be set to change the described
            behaviour and force the function to treat the
            ``capella_cli`` as a local executable or a Docker image
            only.
        image_format
            Format of the image file(s) for the exported diagram(s).
            This can be set to any value out of ``"bmp"``, ``"gif"``,
            ``"jpg"``, ``"png"``, or ``"svg"``.
        create_index
            If ``True``, two index files ``index.json`` and
            ``index.html`` will be created. The JSON file consists of a
            list of dictionaries, each representing a diagram in the
            model. The dictionaries come with the keys

            - uuid: The unique ID of the diagram
            - name: Name of the diagram as it has been set in Capella
            - type: The diagram type as it was created in Capella
            - viewpoint: The source layer from where the representation
              is loaded from. It is ``Common`` for layerless diagrams.
            - success: A boolean stating if a diagram has been exported
              from Capella

            The HTML file shows a numbered list of diagram names which
            are hyperlinked to the diagram image file. Right beside a
            diagram's name one can also see the diagram's UUID in a
            discreet light gray and tiny font size. The HTML index also
            provides some meta data like a timestamp for the
            update of diagrams.
        force
            If the value of ``capella_cli`` is ambiguous and can match
            both a local executable and a Docker image, this parameter
            can be used to bypass the auto-detection and force the
            choice. A value of ``"exe"`` always interprets
            ``capella_cli`` as local executable, ``"docker"`` always
            interprets it as a docker image name. ``None`` (the default)
            enables automatic detection.
        background
            Add a white background to exported SVG images.

            Ignored if the ``image_format`` is not ``"svg"``.

        Examples
        --------
        **Running a local installation of Capella**

        All the following examples call the method
        :meth:`update_diagram_cache` on a model
        for which a diagram cache has been specified, example:

        >>> import capellambse
        >>> model = capellambse.MelodyModel(
        ...    "/path/to/model.aird",
        ...    diagram_cache="/path/to/diagram_cache",
        ... )

        Passing an executable/ symlink named ``capella`` that is in the
        ``PATH`` environment variable:

        >>> model.update_diagram_cache(
        ...     "capella", "png", True
        ... )

        Passing an absolute path to a local installation of Capella that
        contains the Capella version:

        >>> model.update_diagram_cache(
        ...     "/Applications/Capella_{VERSION}.app/Contents/MacOS/capella"
        ... )

        **Running a Capella container**

        >>> model.update_diagram_cache(
        ...     "ghcr.io/dsd-dbs/capella-dockerimages/capella/base"
        ...     ":{VERSION}-selected-dropins-main"
        ... )
        """
        if self.diagram_cache is None:
            raise TypeError(
                "Cannot update: No diagram_cache was specified for this model"
            )
        _diagram_cache.export(
            capella_cli,
            self,
            format=image_format,
            index=create_index,
            force=force,
            background=background,
        )

    @property
    def info(self) -> ModelInfo:
        upstream_info = self._loader.get_model_info()
        if self.diagram_cache is not None:
            dgcinfo = self.diagram_cache.get_model_info()
        else:
            dgcinfo = None
        return ModelInfo(
            url=upstream_info.url,
            title=upstream_info.title,
            entrypoint=upstream_info.entrypoint,
            resources=upstream_info.resources,
            capella_version=upstream_info.capella_version,
            viewpoints=upstream_info.viewpoints,
            diagram_cache=dgcinfo,
        )

    @property
    def description_badge(self) -> str:
        """Describe model contents distribution with an SVG badge."""
        from capellambse.extensions import metrics

        return metrics.get_summary_badge(self)

    def referenced_viewpoints(self) -> dict[str, str]:
        return dict(self._loader.referenced_viewpoints())

    def activate_viewpoint(self, name: str, version: str) -> None:
        self._loader.activate_viewpoint(name, version)

    if t.TYPE_CHECKING:

        def __getattr__(self, attr: str) -> t.Any:
            """Account for extension attributes in static type checks."""

        def __setattr__(
            self,
            attr: str,
            val: property | cabc.Callable[..., t.Any],
        ) -> None:
            """Allow setting additional properties in static type checks."""


@dataclasses.dataclass
class ModelInfo(loader.ModelInfo):
    diagram_cache: filehandler.abc.HandlerInfo | None


def _reference_attributes(
    objtype: type[_obj.ModelObject], /
) -> tuple[str, ...]:
    ignored_accessors: tuple[type[_descriptors.Accessor], ...] = (
        _descriptors.DeepProxyAccessor,
        _descriptors.DeprecatedAccessor,
        _descriptors.ParentAccessor,
        _descriptors.Backref,
    )

    attrs: list[str] = []
    for i in dir(objtype):
        if i.startswith("_") or i == "parent":
            continue
        acc = getattr(objtype, i, None)
        if isinstance(acc, _descriptors.Accessor) and not isinstance(
            acc, ignored_accessors
        ):
            attrs.append(i)
    return tuple(attrs)
