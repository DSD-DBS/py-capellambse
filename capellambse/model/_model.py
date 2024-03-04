# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
"""The main Model class that's responsible for loading and saving a model."""
from __future__ import annotations

__all__ = [
    "Model",
    "ResourceDef",
]

import collections
import collections.abc as cabc
import contextlib
import logging
import os
import pathlib
import typing as t
import uuid
import weakref

import capellambse
from capellambse import exs, filehandler, helpers

from . import _meta, _obj, _xml

if t.TYPE_CHECKING:
    from capellambse import metamodel as M

ResourceDef = t.Union[
    dict[str, t.Any],
    filehandler.FileHandler,
    os.PathLike,
    str,
]

LOGGER = logging.getLogger(__name__)

_ALIEN_MENACE = """\
Alien Menace

The model at %s
contains undefined elements or attributes, which could not be loaded properly.

Saving the model has been disabled, as it would result in data loss.

Please make sure that all needed extensions are installed.

If you think this is a mistake, please file a bug report:

    https://github.com/DSD-DBS/py-capellambse/issues
"""


def _load_resource(definition: ResourceDef) -> filehandler.FileHandler:
    if isinstance(definition, filehandler.FileHandler):
        return definition
    elif isinstance(definition, cabc.Mapping):
        return filehandler.get_filehandler(
            **{k: v for k, v in definition.items() if k != "entrypoint"}
        )
    elif isinstance(definition, (os.PathLike, str)):
        return filehandler.get_filehandler(path=definition)
    else:
        raise TypeError(f"Invalid backing store definition: {definition!r}")


def _derive_entrypoint(
    path: str | os.PathLike | filehandler.FileHandler,
    entrypoint: str | pathlib.PurePosixPath | None,
    kwargs: dict[str, t.Any],
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
                path = filehandler.get_filehandler(path, **kwargs)
                return path, entrypoint
            elif nested_path.is_file():
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


class Model:
    """The main class that's responsible for loading and saving a model.

    This class is the main entry point for working with a Capella model.
    It provides means for loading and saving the model, and for
    accessing the model's objects.
    """

    diagram_cache: filehandler.FileHandler | None

    def __init__(
        self,
        path: str | os.PathLike | filehandler.FileHandler,
        *,
        entrypoint: str | pathlib.PurePosixPath | None = None,
        diagram_cache: ResourceDef | None = None,
        resources: cabc.Mapping[str, ResourceDef] | None = None,
        fallback_render_aird: bool = False,
        xenophobia: bool = False,
        **kwargs: t.Any,
    ) -> None:
        """Load a model from a file handler.

        The model will be associated with the specified file handler,
        and can be saved back to it by calling :meth:save.

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
        resources
            Specify where to find additional resources, like linked
            models. The keys to this dictionary are the project names
            visible in the Capella Project Explorer, and the values are
            further paths, dictionaries or FileHandler instances
            describing the backing store for that project. Note that the
            ``entrypoint`` argument is ignored for resources.
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
              :class:`~capellambse.filehandler.abc.FileHandler`. The
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
        xenophobia
            If True, treat the presence of Alien objects or unhandled
            XML data as hard errors. If False, ignore them and continue
            loading the model, but disallow saving it back.

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
        if kwargs.pop("diagram_cache_subdir", None) not in (None, ".", "/"):
            raise ValueError(
                "diagram_cache_subdir is no longer supported,"
                " use a FileHandler / dict with a 'subdir' instead"
            )
        if kwargs.pop("ignore_duplicate_uuids_and_void_all_warranties", False):
            raise ValueError("Ignoring duplicate UUIDs is no longer supported")
        xenophobia = xenophobia or "CAPELLAMBSE_XENOPHOBIA" in os.environ

        capellambse.load_model_extensions()

        path, self._entrypoint = _derive_entrypoint(path, entrypoint, kwargs)
        assert isinstance(self._entrypoint, pathlib.PurePosixPath)
        self.resources = {"\x00": path}

        self._by_uuid: weakref.WeakValueDictionary[str, _obj.ModelElement]
        self._by_uuid = weakref.WeakValueDictionary()
        self._by_type: dict[type[_obj.ModelElement], _obj.RefList]
        self._by_type = collections.defaultdict(lambda: _obj.RefList(self))

        self._fallback_render_aird = fallback_render_aird

        for label, res in (resources or {}).items():
            if "/" in label or "\x00" in label:
                raise ValueError(f"Invalid resource label: {label}")
            self.resources[label] = _load_resource(res)

        if diagram_cache:
            self.diagram_cache = _load_resource(diagram_cache)
        else:
            self.diagram_cache = None

        self._has_aliens = False
        self.trees: list[_obj.ModelElement] = []
        _xml.load(self, self._entrypoint)

        if self._has_aliens:
            LOGGER.error(_ALIEN_MENACE, path.path)
            if xenophobia:
                raise RuntimeError(f"Aliens found in model from {path}")

    @property
    def capella_version(self) -> str:
        """Return the Capella version of the model."""
        return self.metadata.capella_version

    @property
    def metadata(self) -> _meta.Metadata:
        """Return the primary metadata object for the model."""
        try:
            return next(
                obj for obj in self.trees if isinstance(obj, _meta.Metadata)
            )
        except StopIteration:
            raise RuntimeError("Model has no metadata object") from None

    @property
    def root(self) -> _obj.ModelElement:
        """Return the object at the root model."""
        for i in self.trees:
            if (
                not isinstance(i, _meta.Metadata)
                and i._fragment is not None
                and i._fragment.resource_label == "\x00"
                and i.parent is None
            ):
                return i
        raise RuntimeError("Cannot determine root element of the model")

    @property
    def project(self) -> M.capellamodeller.Project:
        """Return the main Project element of the model.

        This is the object at the root of the primary semantic model
        tree, i.e. the one that is loaded from the ``.capella`` file
        linked from the entrypoint.
        """
        obj = self.root
        if not isinstance(obj, capellambse.metamodel.capellamodeller.Project):
            raise RuntimeError("Model has no Project or Library at its root")
        return obj

    @property
    def oa(self) -> M.oa.OperationalAnalysis:
        """The Operational Analysis layer of the model root."""
        return self.project.model_root.oa

    @property
    def sa(self) -> M.sa.SystemAnalysis:
        """The System Analysis layer of the model root."""
        return self.project.model_root.sa

    @property
    def la(self) -> M.la.LogicalArchitecture:
        """The Logical Architecture layer of the model root."""
        return self.project.model_root.la

    @property
    def pa(self) -> M.pa.PhysicalArchitecture:
        """The Physical Architecture layer of the model root."""
        return self.project.model_root.pa

    @property
    def epbs(self) -> M.epbs.EPBSArchitecture:
        """The EPBS Architecture layer of the model root."""
        return self.project.model_root.epbs

    def save(self, **kw: t.Any) -> None:
        """Save the model back to where it was loaded from.

        Parameters
        ----------
        kw
            Additional keyword arguments for the file handlers'
            ``write_transaction`` method.

            Currently, the same set of keyword arguments is passed to
            all file handlers.

            If keyword arguments were passed that were not consumed by
            any of the used file handlers, a warning is emitted.

        See Also
        --------
        capellambse.filehandler.localfilehandler.LocalFileHandler.write_transaction :
            Accepted ``**kw`` when using local directories
        capellambse.filehandler.gitfilehandler.GitFileHandler.write_transaction :
            Accepted ``**kw`` when using ``git://`` and similar URLs

        Notes
        -----
        With a file handler that contacts a remote location (such as the
        :class:`~capellambse.filehandler.gitfilehandler.GitFileHandler`
        with non-local repositories), saving might fail if the local
        state has gone out of sync with the remote state. To avoid this,
        always leave the ``update_cache`` parameter at its default value
        of ``True`` if you intend to save changes.
        """
        if self._has_aliens:
            raise TypeError("Cannot save a model with alien elements")

        with contextlib.ExitStack() as stack:
            never_used_kw = set(kw)
            for res, fh in self.resources.items():
                LOGGER.debug("Opening transaction for resource: %s", res)
                unused_kw = stack.enter_context(fh.write_transaction(**kw))
                never_used_kw &= set(unused_kw)
            if never_used_kw:
                LOGGER.warning(
                    (
                        "Some arguments to Model.save were not understood by"
                        " any resource's file handler: %s"
                    ),
                    ", ".join(sorted(never_used_kw)),
                )

            LOGGER.debug("Generating XML for %d trees", len(self.trees))
            trees: dict[
                _obj.ResourceName,
                tuple[dict[str, str], list[etree._Element]],
            ] = collections.defaultdict(lambda: ({}, []))
            for tree in self.trees:
                namespaces, fragtrees = trees[tree._fragment]
                fragtrees.append(tree._to_xml(namespaces=namespaces))

            LOGGER.info("Writing %d fragments", len(trees))
            for fragpath, (_, fragtrees) in trees.items():
                fragtree = _xml.wrap_xmi(
                    *fragtrees, capella_version=self.capella_version
                )
                fh = self.resources[fragpath.resource_label]
                with fh.open(fragpath.filename, "wb") as f:
                    exs.write(fragtree, f, line_length=80, siblings=True)

    def search(
        self,
        *xtypes: str | type[_obj.ModelElement],
        below: _obj.ModelElement | None = None,
    ) -> _obj.ElementList:
        r"""Search for all elements with any of the given types.

        If no ``xtypes`` are given at all, this method will return an
        exhaustive list of all (semantic) model objects.

        Parameters
        ----------
        xtypes
            Classes or names of classes to search for.
        below
            A model element to constrain the search. If given, only
            those elements will be returned that are (immediate or
            nested) children of this element.
        """
        if not xtypes:
            if below is None:
                objs = list(self._by_uuid.values())
            else:
                objs = [
                    i
                    for i in self._by_uuid.values()
                    if below in i._walk_parents()
                ]
            return _obj.ElementList(objs)

        wanted_classes: list[type[_obj.ModelElement]]
        return _obj.ElementList([])

    @t.overload
    def by_uuid(self, uuid: str | uuid.UUID, /) -> t.Any: ...

    @t.overload
    def by_uuid(
        self, uuid: str | uuid.UUID, /, cls: type[_obj._O]
    ) -> _obj._O: ...

    def by_uuid(
        self, id: str | uuid.UUID, /, cls: type[_obj._O] | None = None
    ) -> _obj._O:
        """Search the entire model for an element with the given UUID.

        Parameters
        ----------
        uuid
            The UUID to search for.
        cls
            Check that the found object is an instance of this class.
            If not given, no check will be performed, and the return
            type will be ``Any``.

        Returns
        -------
        ModelElement
            The model object with the given UUID.

        Raises
        ------
        ValueError
            If the given UUID is not a valid UUID string.
        KeyError
            If no object with the given UUID was found.
        TypeError
            If the found object is not an instance of ``cls``.
        """
        if isinstance(id, uuid.UUID):
            id = str(id)
        obj = self._by_uuid[id]
        if cls is not None:
            if not issubclass(cls, _obj.ModelElement):
                raise TypeError("cls must be a subclass of ModelElement")
            if not isinstance(obj, cls):
                raise TypeError(
                    f"Object with UUID {id} is not an instance of {cls}"
                )
        return t.cast(_obj._O, obj)

    @t.overload
    def follow(
        self,
        origin: _obj.ModelElement | str,
        ref: str,
        /,
        nsmap: cabc.Mapping[str, str] = ...,
    ) -> t.Any: ...

    @t.overload
    def follow(
        self,
        origin: _obj.ModelElement | str,
        ref: str,
        /,
        nsmap: cabc.Mapping[str, str],
        cls: type[_obj._O],
    ) -> _obj._O: ...

    def follow(
        self,
        origin: _obj.ModelElement | str,
        ref: str,
        /,
        nsmap: cabc.Mapping[str, str] | None = None,
        cls: type[_obj._O] | None = None,
    ) -> _obj._O:
        """Follow a reference from one model object to another.

        References have one of the following formats:

        - ``#UUID``
        - ``ns:Type fragment#UUID``

        The first format is used for references to objects in the same
        fragment, the second for references to objects in other
        fragments.

        Parameters
        ----------
        origin
            The model object to start from. This can be either the
            object itself or its UUID.
        ref
            The reference to follow, in the format described above.
        nsmap
            The namespace map to use for resolving the reference.
            Required if the reference is in the second format.
        cls
            Used to provide the correct return type at type checking
            time. Not used at runtime.

        Returns
        -------
        ModelElement
            The model object that was referenced.

        Raises
        ------
        ValueError
            If the link is not a valid reference string.
        KeyError
            If no object with the given UUID was found.
        """
        del cls
        del origin  # TODO take fragmentation into account
        orig_ref = ref

        if " " in ref:
            targettype, ref = ref.split(" ", 1)
        else:
            targettype = None
        ref = ref.lstrip("# ")

        obj = self.by_uuid(ref)
        if targettype is not None:
            if not nsmap:
                raise ValueError(
                    "Cannot resolve cross-fragment reference without"
                    " namespace map: {orig_ref!r}"
                )
            tns, tcls = targettype.split(":", 1)
            expected_type = _obj.find_class(nsmap[tns], tcls)
            if not isinstance(obj, expected_type):
                raise TypeError(
                    f"Invalid reference, expected {expected_type.__name__},"
                    f" got {type(obj).__name__}: {orig_ref!r}"
                )

        return obj

    def find_references(
        self, target: _obj.ModelElement | str, /
    ) -> cabc.Iterator[tuple[_obj.ModelElement, str, int | None]]:
        """Search the model for references to the given object.

        This method will not find the implicit backreferences that
        children have to their parents.

        Parameters
        ----------
        target
            The target object to search for.

        Yields
        ------
        tuple[ModelElement, str, int | None]
            A 3-tuple containing the referencing model object, the
            attribute on that object, and an optional index. If the
            attribute contains a list of objects, the index shows the
            index into the list that was found. Otherwise the index is
            None.
        """
        if isinstance(target, str):
            if not capellambse.helpers.is_uuid_string(target):
                raise ValueError(f"Malformed UUID: {target!r}")
            target = self.by_uuid(target)

        else:
            if target._model is not self:
                raise ValueError(
                    "Cannot find references to objects from different models"
                )

        raise NotImplementedError("Finding references is not yet implemented")

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
            something like the following will work:

            .. code-block:: bash

                docker run --rm -it <capella_cli> -nosplash \
                    -consolelog -app APP -appid APPID

            See also ``force`` below.
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

        Raises
        ------
        TypeError
            If no ``diagram_cache`` was specified while loading the
            model.
        RuntimeError
            If an error occurs while diagrams are being exported from
            the Capella model.

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
    def description_badge(self) -> str:
        """Describe model contents distribution with an SVG badge."""
        from capellambse.extensions import metrics

        return metrics.get_summary_badge(self)

    def _register(self, obj: _obj.ModelElement) -> None:
        """Register a new model object.

        This method must be called when inserting an object into the
        model to register it with the lookup tables.
        """
        LOGGER.debug("Registering: %s %s", obj.uuid, type(obj).__name__)
        self._by_uuid[obj.uuid] = obj
        self._by_type[type(obj)].append(obj)

    def _unregister(self, obj: _obj.ModelElement) -> None:
        """Unregister a model object.

        This method must be called when deleting an object from the
        model to remove it from the lookup tables.
        """
        LOGGER.debug("Unregistering: %s %s", obj.uuid, type(obj).__name__)
        del self._by_uuid[obj.uuid]
        self._by_type[type(obj)].delete(obj)

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        path = os.fspath(self.resources["\x00"].path)
        return f"<Model at {id(self):#x} from {path!r}>"

    if t.TYPE_CHECKING:

        def __getattr__(self, attr: str) -> t.Any:
            """Account for extension attributes in static type checks."""
