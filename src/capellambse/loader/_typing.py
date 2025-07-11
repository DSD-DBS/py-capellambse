# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0

__all__ = [
    "Element",
    "FragmentType",
    "Loader",
    "ModelInfo",
]

import dataclasses
import enum
import pathlib
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeAlias, TypeVar

from lxml import etree
from typing_extensions import Self

from capellambse import filehandler

_E_co = TypeVar("_E_co", covariant=True, bound="Element")
_E = TypeVar("_E", bound="Element")
_Q = TypeVar("_Q")
Loader: TypeAlias = (
    "_Loader[Element, etree.QName] | _Loader[etree._Element, etree.QName]"
)


class FragmentType(enum.Enum):
    """The type of an XML fragment."""

    SEMANTIC = enum.auto()
    VISUAL = enum.auto()
    OTHER = enum.auto()


@dataclasses.dataclass
class ModelInfo:
    url: str | None
    title: str | None
    entrypoint: pathlib.PurePosixPath
    resources: dict[str, filehandler.abc.HandlerInfo]
    capella_version: str
    viewpoints: dict[str, str]


class _Tree(Protocol[_E_co, _Q]):
    @property
    def root(self) -> _E_co: ...
    @property
    def fragment_type(self) -> FragmentType: ...

    def iterall(self, /) -> Iterator[_E_co]: ...
    def iter_qtypes(self, /) -> Iterator[_Q]: ...
    def iter_qtype(self, qtype: _Q, /) -> Iterator[_E_co]: ...

    def add_namespace(self, uri: str, alias: str, /) -> str: ...


class _Loader(Protocol, Generic[_E, _Q]):
    @property
    def trees(self) -> Mapping[pathlib.PurePosixPath, _Tree[_E, _Q]]: ...
    @property
    def resources(self) -> dict[str, filehandler.FileHandler]: ...

    def get_model_info(self, /) -> ModelInfo: ...

    def find_fragment(self, elem: _E, /) -> pathlib.PurePosixPath: ...
    def iterancestors(self, elem: _E, /) -> Iterator[_E]: ...
    def iterdescendants(self, elem: _E, /) -> Iterator[_E]: ...
    def iterchildren(self, elem: _E, tag: str, /) -> Iterator[_E]: ...
    def find_references(self, target_id: str, /) -> Iterator[_E]: ...

    def create_link(
        self,
        source: _E,
        target: _E,
        *,
        include_target_type: bool | None = None,
    ) -> str: ...
    def follow_link(self, source: _E | None, id: str, /) -> _E: ...
    def follow_links(
        self,
        source: _E,
        id_list: str,
        /,
        *,
        ignore_broken: bool = ...,
    ) -> list[_E]: ...

    def new_uuid(
        self,
        parent: _E,
        /,
        *,
        want: str | None = ...,
    ) -> AbstractContextManager[str]: ...
    def idcache_index(self, subtree: _E, /) -> None: ...
    def idcache_remove(self, subtree: _E, /) -> None: ...
    def idcache_rebuild(self, /) -> None: ...

    def activate_viewpoint(self, name: str, version: str, /) -> None: ...
    def update_namespaces(self, /) -> None: ...
    def save(self, /, **kw: Any) -> None: ...

    def write_tmp_project_dir(
        self, /
    ) -> AbstractContextManager[pathlib.Path]: ...


class Element(Protocol):
    @property
    def tag(self) -> str: ...

    def iterchildren(self, tag: str = ..., /) -> Iterator[Self]: ...


if TYPE_CHECKING:

    def __protocol_compliance_check() -> None:
        from capellambse import loader  # noqa: PLC0415

        tree: _Tree
        tree = loader.ModelFile()  # type: ignore[call-arg]
        del tree

        elm: Element
        elm = etree._Element()
        del elm

        ldr: Loader
        ldr = loader.MelodyLoader()  # type: ignore[call-arg]
        del ldr
