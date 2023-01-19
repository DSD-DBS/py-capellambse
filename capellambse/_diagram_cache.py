# SPDX-FileCopyrightText: Copyright DB Netz AG and the capellambse contributors
# SPDX-License-Identifier: Apache-2.0
"""Module to populate the diagram cache with native Capella diagrams."""

from __future__ import annotations

import datetime
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import typing as t

import lxml
from lxml import etree as ET

import capellambse.model.diagram

E = lxml.builder.ElementMaker()
BAD_FILENAMES = frozenset(
    {"AUX", "CON", "NUL", "PRN"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
LOGGER = logging.getLogger(__name__)
VALID_IMG_FMTS = frozenset(
    {
        "bmp",
        "gif",
        "jpg",
        "png",
        "svg",
    }
)


class DiagramCache:
    _cli_cmd: list[str] = []
    _cli_type: t.Literal["exe", "docker"] | None = None
    _index: list[dict[str, str | bool]] = []

    def __init__(
        self,
        capella_cli: str,
        image_format: t.Literal["bmp", "gif", "jpg", "png", "svg"],
        create_index: bool,
        force: t.Literal["exe", "docker"] | None,
        capella_project_name: str,
        diagrams_dir: pathlib.Path,
        diagrams: list[capellambse.model.diagram.Diagram],
    ):
        self.capella_cli = capella_cli
        self.image_format = image_format
        self.create_index = create_index
        self.force = force
        self.capella_project_name = capella_project_name
        self.diagrams_dir = diagrams_dir
        self.diagrams = diagrams
        self._json_index_path = self.diagrams_dir / "index.json"
        self._process_config()

    def _find_exe(self, path: str) -> str | None:
        fpath, _ = os.path.split(path)
        if fpath:
            if pathlib.Path(path).is_file() and os.access(path, os.X_OK):
                return path
        else:
            return shutil.which(path)
        return None

    def _process_config(self) -> None:
        if self.image_format.lower() not in VALID_IMG_FMTS:
            raise ValueError(
                f"Invalid image format {self.image_format!r}, must be one of: "
                + ", ".join(sorted(VALID_IMG_FMTS))
            )
        if self.force not in {"docker", "exe", None}:
            raise ValueError(
                "Invalid value for 'force', must be 'docker' or 'exe': "
                f"{self.force}"
            )
        if self.force != "docker":
            # use of Docker is not forced
            if (exe := self._find_exe(self.capella_cli)) is not None:
                # local exe has been identified
                self._cli_cmd = [str(exe)]
                self._cli_type = "exe"
        if not self._cli_cmd and self.force != "exe":
            # no local exe has been identified and Docker is allowed
            if (exe := self._find_exe("docker")) is not None:
                self._cli_cmd = [exe, "run", "--rm"]
                self._cli_type = "docker"
        if not self._cli_cmd:
            if self.force == "exe":
                raise FileNotFoundError(
                    "Cannot find supplied 'capella_cli' executable: "
                    f"{self.capella_cli}"
                )
            elif self.force == "docker":
                raise FileNotFoundError(
                    "Cannot find the executable 'docker' to run the "
                    f"'capella_cli' image: {self.capella_cli}"
                )
            else:
                raise FileNotFoundError(
                    "Cannot run 'capella_cli': Not an executable and "
                    "'docker' was not found to run it as image: "
                    f"{self.capella_cli}"
                )
        self._cli_common_flags = [
            "-nosplash",
            "-consolelog",
            "-application",
            "org.polarsys.capella.core.commandline.core",
            "-appid",
            "org.polarsys.capella.exportRepresentations",
            "-forceimport",
            "-input",
            "/all",
            "-imageFormat",
            f"{self.image_format.upper()}",
            "-outputfolder",
            "/main_model/output",
            "-forceoutputfoldercreation",
        ]

    def _diagram_2_image_file_name(self, fname) -> str:
        # pylint: disable=line-too-long
        r"""Sanitize the filename.

        This function removes all characters that are illegal in file
        names on Windows operating systems, and prefixes reserved names
        with an underscore.

        Note that this also includes the two common directory separators
        (``/`` and ``\``).

        Notes
        -----
        Refer to the `MSDN article about file names`__ for more details.

        __ https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file?redirectedfrom=MSDN#naming-conventions
        """
        # pylint: enable=line-too-long
        fname = fname.rstrip(" .")
        fname = re.sub(
            '[\x00-\x1f<>:"/\\\\|?*]',
            lambda m: "-"[ord(m.group(0)) < 32 :],
            fname,
        )
        if fname.split(".")[0].upper() in BAD_FILENAMES:
            fname = f"_{fname}"
        return fname

    def _rename_diagram_image_files(self) -> None:
        """Rename diagram image files so that the UUID is the base name."""
        existing_diagrams: list[dict[str, str | bool]] = [
            d for d in self._index if d["success"]
        ]
        for diagram_info in existing_diagrams:
            filename: str = str(diagram_info["name"])
            filename = self._diagram_2_image_file_name(
                f"{filename}.{self.image_format}"
            )
            old_path = self.diagrams_dir / filename
            if not old_path.is_file():
                continue
            old_path.rename(
                self.diagrams_dir
                / (f"{diagram_info['uuid']}." f"{self.image_format}")
            )

    def _build_cli_cmd_exe(
        self, tmp_project_dir: pathlib.Path, workspace: pathlib.Path
    ) -> None:
        self._cli_cmd += [
            "-data",
            str(workspace),
            "-import",
            f"{str(tmp_project_dir / 'main_model')}",
        ] + self._cli_common_flags

    def _build_cli_cmd_docker(
        self, tmp_project_dir: pathlib.Path, workspace: pathlib.Path
    ) -> None:
        self._cli_cmd += [
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{tmp_project_dir}:/model",
            self.capella_cli,
            "-data",
            "/workspace",
            "-import",
            "/model/main_model",
        ] + self._cli_common_flags

    def _create_index_json(self) -> None:
        """Create a diagram name to UUID index file if not already existing.

        Diagram names in Capella are not unique. When there are multiple
        instances for one diagram name the Capella context menu (.aird node)
        function ``Export representations as images`` works with counting
        suffixes in the image file name.

        The first occurrence of a diagram name leads into a file named
        ``<NAME>.<EXT>``, the second occurrence will be named
        ``<NAME>_1.<EXT>`` etc. whereby ``<EXT>`` might be ``"svg"`` for
        instance.

        Luckily the order of the diagrams that are read by the exporter
        matches the order of diagrams we get from
        :meth:`capellambse.model.MelodyModel.diagrams`.
        """
        diagram_names: dict[str, str] = {}  # uuid -> diag.name
        diagram_name_to_uuid_map: dict[str, str] = {}  # uuid -> diagram name
        diagram_name_counts: dict[
            str, int
        ] = {}  # diag.name -> counts of according diagram name
        for diag in self.diagrams:
            if diag.name in diagram_name_counts:
                diagram_name_counts[diag.name] += 1
            else:
                diagram_name_counts[diag.name] = 1
            diagram_names[diag.uuid] = diag.name
            if diagram_name_counts[diag.name] > 1:
                count_suffix = f"_{diagram_name_counts[diag.name] - 1}"
                diagram_name_to_uuid_map[
                    f"{diag.name}{count_suffix}"
                ] = diag.uuid
            else:
                diagram_name_to_uuid_map[f"{diag.name}"] = diag.uuid
        for diagram_name, uuid in sorted(diagram_name_to_uuid_map.items()):
            filename: str = self._diagram_2_image_file_name(
                f"{diagram_name}.{self.image_format}"
            )
            self._index.append(
                {
                    "name": diagram_name,
                    "uuid": uuid,
                    "success": self.diagrams_dir.joinpath(filename).is_file(),
                }
            )

    def _create_index_html_file(self) -> None:
        """Create an ``index.html`` file linking diagram names to images."""
        filepath = pathlib.Path(self.diagrams_dir / "index.html")
        filepath.unlink(missing_ok=True)
        head = E.head(
            E.style(
                "a:active { text-decoration: none; }"
                " a:hover { text-decoration: none; }"
                " a:link { text-decoration: none; }"
                " a:visited { text-decoration: none; }"
                " li.missing {color: red}"
                " ol {font-family: Courier}"
                " span.small {font-size: 10pt}"
                " span.uuid {color: #dddddd; font-size: 8pt}"
            )
        )
        html = E.html()
        html.append(head)
        now = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
        title = f"Capella diagram cache for {self.capella_project_name!r}"
        html.append(
            E.h1(
                title,
                E.span(" created: ", now, {"class": "small"}),
            )
        )
        diaglist = E.ol()
        for diagram in self._index:
            label = diagram["name"]
            uuid = E.span(diagram["uuid"], {"class": "uuid"})
            if diagram["success"]:
                href = f"./{diagram['uuid']}.{self.image_format}"
                diaglist.append(E.li(E.a(label, href=href), " ", uuid))
            else:
                diaglist.append(E.li(label, uuid, {"class": "missing"}))
        html.append(diaglist)
        filepath.write_text(ET.tostring(html).decode("ascii"), encoding="utf8")

    def _post_process_svg(self, path: pathlib.Path) -> None:
        """Post process SVG file.

        Parameters
        ----------
        path
            Absolute path to the SVG file of an exported diagram
        """
        tree = ET.parse(path)

        for elm in tree.iter():
            attrib = elm.attrib
            if "font-family" in attrib:
                attrib[
                    "font-family"
                ] = "'Open Sans','Segoe UI',Arial,sans-serif"
            if "stroke-miterlimit" in attrib:
                del attrib["stroke-miterlimit"]

        path.write_bytes(ET.tostring(tree, pretty_print=True))

    def export_diagrams(self, project_dir: pathlib.Path) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            build_cli_cmd = getattr(self, f"_build_cli_cmd_{self._cli_type}")
            build_cli_cmd(project_dir, workspace)
            try:
                subprocess.check_call(self._cli_cmd)
            except subprocess.CalledProcessError as err:
                raise RuntimeError("Failed to update diagram cache") from err
            for p in pathlib.Path(workspace).glob(
                f"main_model/**/*.{self.image_format}"
            ):
                shutil.copyfile(p, self.diagrams_dir / p.name)
        self._create_index_json()
        self._rename_diagram_image_files()
        if self.image_format == "svg":
            for svg in pathlib.Path(self.diagrams_dir).glob("*.svg"):
                self._post_process_svg(svg)
        if self.create_index:
            self._json_index_path.write_text(json.dumps(self._index, indent=2))
            self._create_index_html_file()
