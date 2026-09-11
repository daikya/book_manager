"""Windows配布版のパッケージメタデータ設定を検証する。"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    PROJECT_ROOT
    / "packaging"
    / "pyinstaller"
    / "book_manager.spec"
)
BUILD_SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "build_windows.ps1"
)


def read_text(path: Path) -> str:
    """設定ファイルをUTF-8で読み込む。"""
    return path.read_text(encoding="utf-8")


def test_spec_collects_book_manager_metadata() -> None:
    """配布物へbook-managerのメタデータを収集する。"""
    content = read_text(SPEC_PATH)

    assert "from PyInstaller.utils.hooks import copy_metadata" in content
    assert 'copy_metadata("book-manager")' in content


def test_spec_adds_metadata_to_analysis_datas() -> None:
    """収集したメタデータをAnalysisのdatasへ追加する。"""
    content = read_text(SPEC_PATH)

    assert "datas=application_assets + application_metadata" in content


def test_build_script_installs_project_metadata() -> None:
    """ビルド前にプロジェクトを編集可能インストールする。"""
    content = read_text(BUILD_SCRIPT_PATH)

    assert "python -m pip install `" in content
    assert "--no-deps `" in content
    assert "--editable `" in content
    assert "$projectRoot" in content


def test_build_script_reads_installed_metadata_version() -> None:
    """インストールしたメタデータからVersionを取得する。"""
    content = read_text(BUILD_SCRIPT_PATH)

    assert "$metadataVersion = python -c `" in content
    assert "from importlib.metadata import version" in content
    assert "version('book-manager')" in content


def test_build_script_rejects_version_mismatch() -> None:
    """pyproject.tomlとメタデータのVersion不一致を拒否する。"""
    content = read_text(BUILD_SCRIPT_PATH)

    assert "if ($metadataVersion -ne $version)" in content
    assert (
        "pyproject.tomlとパッケージメタデータのVersionが一致しません。"
        in content
    )
