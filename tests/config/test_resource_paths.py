"""静的資源パス解決のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from book_manager.config import resource_paths


def test_get_resource_root_uses_project_root_in_source_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ソース版ではsrcレイアウトのプロジェクトルートを返す。"""
    monkeypatch.delattr(
        resource_paths.sys,
        "frozen",
        raising=False,
    )

    result = resource_paths.get_resource_root()

    assert result == (
        Path(resource_paths.__file__).resolve().parents[3]
    )


def test_get_resource_root_uses_bundle_root_in_frozen_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PyInstaller版では_MEIPASSを資源ルートにする。"""
    bundle_root = tmp_path / "bundle"
    monkeypatch.setattr(
        resource_paths.sys,
        "frozen",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        resource_paths.sys,
        "_MEIPASS",
        str(bundle_root),
        raising=False,
    )

    result = resource_paths.get_resource_root()

    assert result == bundle_root


def test_get_resource_root_rejects_missing_bundle_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配布版で_MEIPASSがなければ明示的に失敗する。"""
    monkeypatch.setattr(
        resource_paths.sys,
        "frozen",
        True,
        raising=False,
    )
    monkeypatch.delattr(
        resource_paths.sys,
        "_MEIPASS",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="資源ルートを取得できません。",
    ):
        resource_paths.get_resource_root()


def test_get_application_icon_path_uses_resource_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """資源ルート配下のWindows用ICOを返す。"""
    monkeypatch.setattr(
        resource_paths,
        "get_resource_root",
        lambda: tmp_path,
    )

    result = resource_paths.get_application_icon_path()

    assert result == (
        tmp_path
        / "assets"
        / "windows"
        / "book_manager.ico"
    )


def test_get_application_icon_path_does_not_create_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """パス解決だけでは資源ファイルを作成しない。"""
    monkeypatch.setattr(
        resource_paths,
        "get_resource_root",
        lambda: tmp_path,
    )

    icon_path = resource_paths.get_application_icon_path()

    assert not icon_path.exists()


def test_get_application_icon_png_path_uses_resource_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """資源ルート配下のPNGアイコンを返す。"""
    monkeypatch.setattr(
        resource_paths,
        "get_resource_root",
        lambda: tmp_path,
    )

    result = resource_paths.get_application_icon_png_path()

    assert result == (
        tmp_path
        / "assets"
        / "windows"
        / "book_manager.png"
    )
