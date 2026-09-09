"""Windows Version情報生成スクリプトのテスト。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_MODULE_NAME = "generate_windows_version_info_script"
SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "generate_windows_version_info.py"
)
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    SCRIPT_MODULE_NAME,
    SCRIPT_PATH,
)

assert SCRIPT_SPEC is not None
assert SCRIPT_SPEC.loader is not None

script_module = importlib.util.module_from_spec(SCRIPT_SPEC)
sys.modules[SCRIPT_MODULE_NAME] = script_module
SCRIPT_SPEC.loader.exec_module(script_module)


def write_pyproject(path: Path, version: str) -> None:
    """テスト用pyproject.tomlを書き込む。"""
    path.write_text(
        (
            "[project]\n"
            'name = "book-manager"\n'
            f'version = "{version}"\n'
        ),
        encoding="utf-8",
    )


def test_read_project_version_returns_version(
    tmp_path: Path,
) -> None:
    """project.versionを取得する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    write_pyproject(pyproject_path, "2.0.0")

    result = script_module.read_project_version(pyproject_path)

    assert result == "2.0.0"


def test_read_project_version_strips_outer_spaces(
    tmp_path: Path,
) -> None:
    """Version文字列の前後空白を除去する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    write_pyproject(pyproject_path, " 2.0.0 ")

    result = script_module.read_project_version(pyproject_path)

    assert result == "2.0.0"


def test_read_project_version_rejects_missing_version(
    tmp_path: Path,
) -> None:
    """project.versionがなければ拒否する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        '[project]\nname = "book-manager"\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="project.versionがありません。",
    ):
        script_module.read_project_version(pyproject_path)


@pytest.mark.parametrize(
    "version",
    ["", "2", "2.0", "version-2.0.0", "2.0.x"],
)
def test_read_project_version_rejects_invalid_version(
    tmp_path: Path,
    version: str,
) -> None:
    """X.Y.Z形式でないVersionを拒否する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    write_pyproject(pyproject_path, version)

    with pytest.raises(ValueError):
        script_module.read_project_version(pyproject_path)


def test_create_numeric_version_returns_four_parts() -> None:
    """Windows用に4要素の数値Versionを作成する。"""
    assert script_module.create_numeric_version("2.0.0") == (
        2,
        0,
        0,
        0,
    )


def test_create_numeric_version_accepts_prerelease() -> None:
    """プレリリース表記では数値部分を使用する。"""
    assert script_module.create_numeric_version("2.0.0-rc.1") == (
        2,
        0,
        0,
        0,
    )


def test_create_numeric_version_rejects_large_part() -> None:
    """Windowsの上限を超える数値を拒否する。"""
    with pytest.raises(
        ValueError,
        match="65535以下",
    ):
        script_module.create_numeric_version("65536.0.0")


def test_create_version_file_content_contains_metadata() -> None:
    """必要な製品情報とVersionを含める。"""
    content = script_module.create_version_file_content("2.0.0")

    assert "filevers=(2, 0, 0, 0)" in content
    assert "prodvers=(2, 0, 0, 0)" in content
    assert "StringStruct('ProductName', 'Book Manager')" in content
    assert "StringStruct('OriginalFilename', 'BookManager.exe')" in content
    assert "StringStruct('ProductVersion', '2.0.0')" in content
    assert "VarStruct('Translation', [1041, 1200])" in content


def test_write_version_file_creates_parent_and_file(
    tmp_path: Path,
) -> None:
    """出力先の親ディレクトリとVersion定義を作成する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    output_path = tmp_path / "build" / "version_info.txt"
    write_pyproject(pyproject_path, "2.0.0")

    version = script_module.write_version_file(
        pyproject_path,
        output_path,
    )

    assert version == "2.0.0"
    assert output_path.is_file()
    assert "ProductVersion', '2.0.0'" in output_path.read_text(
        encoding="utf-8"
    )


def test_main_writes_file_and_prints_version(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLIからVersion定義を生成してVersionを表示する。"""
    pyproject_path = tmp_path / "pyproject.toml"
    output_path = tmp_path / "version_info.txt"
    write_pyproject(pyproject_path, "2.0.0")

    exit_code = script_module.main(
        [
            "--pyproject",
            str(pyproject_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "2.0.0"
    assert output_path.is_file()
