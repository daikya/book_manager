"""pyproject.tomlからPyInstaller用Windows Version情報を生成する。"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path
from typing import Sequence


VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\."
    r"(?P<minor>\d+)\."
    r"(?P<patch>\d+)"
    r"(?:[-+][0-9A-Za-z.-]+)?$"
)


def read_project_version(pyproject_path: Path) -> str:
    """pyproject.tomlからproject.versionを取得する。"""
    with Path(pyproject_path).open("rb") as file:
        configuration = tomllib.load(file)

    try:
        version = configuration["project"]["version"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "pyproject.tomlにproject.versionがありません。"
        ) from error

    if not isinstance(version, str) or not version.strip():
        raise ValueError(
            "project.versionは空でない文字列にしてください。"
        )

    normalized_version = version.strip()

    if VERSION_PATTERN.fullmatch(normalized_version) is None:
        raise ValueError(
            "project.versionはX.Y.Z形式にしてください。"
        )

    return normalized_version


def create_numeric_version(version: str) -> tuple[int, int, int, int]:
    """Windows Version資源用の4要素Versionを返す。"""
    match = VERSION_PATTERN.fullmatch(version)

    if match is None:
        raise ValueError(
            "VersionはX.Y.Z形式にしてください。"
        )

    parts = (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        0,
    )

    if any(part > 65535 for part in parts):
        raise ValueError(
            "Windows Versionの各数値は65535以下にしてください。"
        )

    return parts


def create_version_file_content(version: str) -> str:
    """PyInstallerが読み込むVersion資源定義を作成する。"""
    numeric_version = create_numeric_version(version)
    numeric_text = ", ".join(str(part) for part in numeric_version)

    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric_text}),
    prodvers=({numeric_text}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '041104B0',
          [
            StringStruct('CompanyName', 'daikya'),
            StringStruct('FileDescription', 'Book Manager'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('InternalName', 'BookManager'),
            StringStruct('LegalCopyright', 'Copyright (c) daikya'),
            StringStruct('OriginalFilename', 'BookManager.exe'),
            StringStruct('ProductName', 'Book Manager'),
            StringStruct('ProductVersion', '{version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1041, 1200])])
  ]
)
"""


def write_version_file(
    pyproject_path: Path,
    output_path: Path,
) -> str:
    """Version資源定義を書き込み、Version文字列を返す。"""
    version = read_project_version(pyproject_path)
    content = create_version_file_content(version)
    normalized_output_path = Path(output_path)
    normalized_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    normalized_output_path.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )
    return version


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pyproject",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Version資源定義を生成し、Versionを標準出力する。"""
    options = parse_arguments(arguments)
    version = write_version_file(
        options.pyproject,
        options.output,
    )
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
