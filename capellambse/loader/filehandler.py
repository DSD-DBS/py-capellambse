# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import warnings

warnings.warn(
    f"{__name__} is deprecated, use capellambse.filehandler instead",
    DeprecationWarning,
    stacklevel=2,
)

del warnings

from capellambse.filehandler import (  # pylint: disable=unused-import
    FileHandler,
    TransactionClosedError,
    __all__,
    get_filehandler,
    load_entrypoint,
    split_protocol,
)
