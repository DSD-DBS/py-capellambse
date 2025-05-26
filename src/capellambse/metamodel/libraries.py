# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import enum

import capellambse.model as m

from . import namespaces as ns

NS = ns.LIBRARIES


@m.stringy_enum
@enum.unique
class AccessPolicy(enum.Enum):
    READ_ONLY = "readOnly"
    READ_AND_WRITE = "readAndWrite"


class LibraryAbstractElement(m.ModelElement, abstract=True):
    pass


class ModelInformation(LibraryAbstractElement):
    references = m.Containment["LibraryReference"](
        "ownedReferences", (NS, "LibraryReference")
    )
    version = m.Association["ModelVersion"]((NS, "ModelVersion"), "version")


class LibraryReference(LibraryAbstractElement):
    library = m.Single["ModelInformation"](
        m.Association((NS, "ModelInformation"), "library")
    )
    access_policy = m.EnumPOD("accessPolicy", AccessPolicy)
    version = m.Association["ModelVersion"]((NS, "ModelVersion"), "version")


class ModelVersion(LibraryAbstractElement):
    major_version_number = m.IntPOD("majorVersionNumber")
    minor_version_number = m.IntPOD("minorVersionNumber")
    last_modified_file_stamp = m.IntPOD("lastModifiedFileStamp")
