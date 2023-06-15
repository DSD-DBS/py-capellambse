# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0

import pytest

from capellambse.filehandler import memory


def test_MemoryFileHandler_raises_ValueError_for_invalid_path():
    with pytest.raises(ValueError):
        memory.MemoryFileHandler(path="memory://invalid")


def test_MemoryFileHandler_raises_FileNotFoundError_for_nonexistent_file():
    fh = memory.MemoryFileHandler()
    with pytest.raises(FileNotFoundError):
        fh.open("test.txt")


def test_MemoryFileHandler_preserves_written_data():
    fh = memory.MemoryFileHandler()
    with fh.open("test.txt", "w") as f:
        f.write(b"Hello, World!")

    with fh.open("test.txt", "r") as f:
        assert f.read() == b"Hello, World!"


def test_MemoryFiles_return_bytes_objects_from_read():
    fh = memory.MemoryFileHandler()
    with fh.open("test.txt", "w") as f:
        f.write(b"Hello, World!")

    with fh.open("test.txt", "r") as f:
        assert isinstance(f.read(), bytes)
