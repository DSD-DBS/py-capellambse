# SPDX-FileCopyrightText: Copyright DB InfraGO AG
# SPDX-License-Identifier: Apache-2.0
import io
import pathlib
import zipfile

import pytest

from capellambse.filehandler import zip as zipfh

PPP = pathlib.PurePosixPath


@pytest.mark.parametrize("proto", ["file:", "zip:"])
def test_zipfilehandler_can_read_local_files(tmp_path, proto):
    with zipfile.ZipFile(tmp_path / "test.zip", "w") as z:
        z.writestr("test.txt", b"Hello, World!")
    zip_path = tmp_path.joinpath("test.zip").as_uri().replace("file:", proto)

    fh = zipfh.ZipFileHandler(zip_path)

    assert fh.read_file("test.txt") == b"Hello, World!"


def test_zipfilehandler_uses_zip_root_directory_as_subdir(tmp_path):
    with zipfile.ZipFile(tmp_path / "test.zip", "w") as z:
        z.writestr("mydir/test.txt", b"Hello, World!")
    zip_path = tmp_path.joinpath("test.zip").as_uri()

    fh = zipfh.ZipFileHandler(zip_path, subdir=None)

    assert fh.subdir == PPP("mydir")
    assert fh.read_file("test.txt") == b"Hello, World!"


def test_zipfilehandler_doesnt_use_zip_root_directory_if_explicitly_overridden(
    tmp_path,
):
    with zipfile.ZipFile(tmp_path / "test.zip", "w") as z:
        z.writestr("mydir/test.txt", b"Hello, World!")
    zip_path = tmp_path.joinpath("test.zip").as_uri()

    fh = zipfh.ZipFileHandler(zip_path, subdir=".")

    assert fh.subdir == PPP(".")
    assert fh.read_file("mydir/test.txt") == b"Hello, World!"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/test.zip",
        "http://example.com/!test.zip",
        "http://example.com/%s!test.zip",
        "http://example.com/%s?v=1!test.zip",
    ],
)
def test_zipfilehandler_can_load_files_from_other_handlers(requests_mock, url):
    zipio = io.BytesIO()
    with zipfile.ZipFile(zipio, "w") as z:
        z.writestr("test.txt", b"Hello, World!")
    zipdata = zipio.getvalue()
    requests_mock.get("http://example.com/test.zip", content=zipdata)
    requests_mock.get("http://example.com/test.zip?v=1", content=zipdata)

    fh = zipfh.ZipFileHandler(url)

    assert fh.read_file("test.txt") == b"Hello, World!"
