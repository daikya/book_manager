"""アプリケーション設定Modelのテスト。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime
from pathlib import Path

import pytest

from book_manager.models.application_settings import (
    ApplicationSettingsSnapshot,
    BackupSettingsSnapshot,
)
from book_manager.models.backup_settings import BackupSettings


def create_snapshot(
    tmp_path: Path,
) -> ApplicationSettingsSnapshot:
    """テスト用の設定Snapshotを生成する。"""
    root_directory = tmp_path / "book_manager"

    return ApplicationSettingsSnapshot(
        google_books_api_key_is_configured=True,
        application_name="Book Manager",
        application_version="2.1.0",
        root_directory=root_directory,
        database_path=root_directory / "data" / "books.db",
        backup_directory=root_directory / "backups",
        cover_cache_directory=(
            root_directory
            / "cache"
            / "covers"
        ),
        log_path=(
            root_directory
            / "logs"
            / "book_manager.log"
        ),
    )


def test_application_settings_snapshot_holds_values(
    tmp_path: Path,
) -> None:
    """設定画面に必要な値を保持できる。"""
    snapshot = create_snapshot(tmp_path)
    root_directory = tmp_path / "book_manager"

    assert snapshot.google_books_api_key_is_configured is True
    assert snapshot.application_name == "Book Manager"
    assert snapshot.application_version == "2.1.0"
    assert snapshot.root_directory == root_directory
    assert (
        snapshot.database_path
        == root_directory / "data" / "books.db"
    )
    assert (
        snapshot.backup_directory
        == root_directory / "backups"
    )
    assert (
        snapshot.cover_cache_directory
        == root_directory / "cache" / "covers"
    )
    assert (
        snapshot.log_path
        == root_directory / "logs" / "book_manager.log"
    )


def test_application_settings_snapshot_accepts_unconfigured_key(
    tmp_path: Path,
) -> None:
    """APIキー未設定の状態を保持できる。"""
    configured_snapshot = create_snapshot(tmp_path)

    snapshot = ApplicationSettingsSnapshot(
        google_books_api_key_is_configured=False,
        application_name=configured_snapshot.application_name,
        application_version=(
            configured_snapshot.application_version
        ),
        root_directory=configured_snapshot.root_directory,
        database_path=configured_snapshot.database_path,
        backup_directory=configured_snapshot.backup_directory,
        cover_cache_directory=(
            configured_snapshot.cover_cache_directory
        ),
        log_path=configured_snapshot.log_path,
    )

    assert snapshot.google_books_api_key_is_configured is False


def test_application_settings_snapshot_compares_by_value(
    tmp_path: Path,
) -> None:
    """同じ設定内容を持つSnapshotは等価になる。"""
    first = create_snapshot(tmp_path)
    second = create_snapshot(tmp_path)

    assert first == second


def test_application_settings_snapshot_is_immutable(
    tmp_path: Path,
) -> None:
    """生成後に設定表示内容を変更できない。"""
    snapshot = create_snapshot(tmp_path)

    with pytest.raises(FrozenInstanceError):
        snapshot.application_version = (  # type: ignore[misc]
            "2.2.0"
        )


def test_application_settings_snapshot_uses_slots(
    tmp_path: Path,
) -> None:
    """設定Snapshotが動的属性を持たない。"""
    snapshot = create_snapshot(tmp_path)

    assert not hasattr(snapshot, "__dict__")


def test_application_settings_snapshot_does_not_hold_api_key(
    tmp_path: Path,
) -> None:
    """SnapshotがAPIキーの実値を保持しない。"""
    snapshot = create_snapshot(tmp_path)
    field_names = {
        field.name
        for field in fields(snapshot)
    }

    assert "google_books_api_key" not in field_names
    assert field_names == {
        "google_books_api_key_is_configured",
        "application_name",
        "application_version",
        "root_directory",
        "database_path",
        "backup_directory",
        "cover_cache_directory",
        "log_path",
    }


def test_backup_snapshot_distinguishes_active_from_saved(tmp_path: Path) -> None:
    """保存値の再起動待ちを表示できる。"""
    snapshot = BackupSettingsSnapshot(
        active_settings=BackupSettings(),
        saved_settings=BackupSettings(48, 2),
        backup_directory=tmp_path,
        backup_count=1,
        latest_backup_path=tmp_path / "books_20260914_090000.db",
        latest_backup_datetime=datetime(2026, 9, 14, 9, 0, 0),
    )

    assert snapshot.changes_pending_restart is True
    assert snapshot.backup_count == 1
    assert snapshot.latest_backup_datetime == datetime(2026, 9, 14, 9)


def test_backup_snapshot_empty_and_no_pending_change(tmp_path: Path) -> None:
    """バックアップなしの状態も保持できる。"""
    snapshot = BackupSettingsSnapshot(
        active_settings=BackupSettings(),
        saved_settings=BackupSettings(),
        backup_directory=tmp_path,
        backup_count=0,
        latest_backup_path=None,
        latest_backup_datetime=None,
    )

    assert snapshot.changes_pending_restart is False
    assert snapshot.latest_backup_path is None
