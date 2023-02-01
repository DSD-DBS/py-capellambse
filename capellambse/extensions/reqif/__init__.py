# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

"""Tools for handling ReqIF Requirements.

.. diagram:: [CDB] Requirements ORM
"""
import typing as t

from ._capellareq import *
from ._glue import *
from ._requirements import *

if not t.TYPE_CHECKING:
    _deprecated_names = {
        "EnumDataTypeDefinition": EnumerationDataTypeDefinition,
        "RequirementsFolder": Folder,
        "RequirementsIncRelation": CapellaIncomingRelation,
        "RequirementsIntRelation": InternalRelation,
        "RequirementsModule": CapellaModule,
        "RequirementsOutRelation": CapellaOutgoingRelation,
        "RequirementsTypesFolder": CapellaTypesFolder,
    }

    def __getattr__(name) -> type[ReqIFElement]:
        import warnings

        if cls := _deprecated_names.get(name):
            warnings.warn(
                f"Name {name} is deprecated, use {cls.__name__} instead",
                DeprecationWarning,
                stacklevel=2,
            )

            return cls

        elif name.startswith("XT_"):
            warnings.warn(
                (
                    "XT_* strings are deprecated, use the respective classes"
                    " and 'build_xtype(cls)' instead"
                ),
                DeprecationWarning,
                stacklevel=2,
            )

            from . import elements

            return getattr(elements, name)

        elif name == "elements":
            import importlib

            fullname = f"{__name__}.{name}"
            warnings.warn(
                f"{fullname!r} is deprecated, use {__name__!r} instead",
                DeprecationWarning,
                stacklevel=2,
            )

            return importlib.import_module(fullname)

        else:
            raise NameError(f"No name {name} in module {__name__}")

    __all__: list[str] = ["elements"]
    from ._capellareq import __all__ as _cr_all
    from ._requirements import __all__ as _rq_all
    from .elements import __all__ as _el_all

    __all__ += _cr_all + _rq_all + _el_all
    del _cr_all, _rq_all, _el_all
del t
