"""バックアップ設定の保存処理を検証する。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from book_manager.config.backup_settings_store import (
    BackupSettingsStore,
    BackupSettingsStoreError,
)
from book_manager.models.backup_settings import BackupSettings


def test_missing_file_uses_defaults_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / "backup_settings.json"

    assert BackupSettingsStore(path).load() == BackupSettings()
    assert not path.exists()


def test_save_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "settings" / "backup_settings.json"
    settings = BackupSettings(backup_interval_hours=48, max_backups=3)

    BackupSettingsStore(path).save(settings)

    assert BackupSettingsStore(path).load() == settings
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "backup_interval_hours": 48,
        "max_backups": 3,
    }


def test_save_replaces_existing_settings(tmp_path: Path) -> None:
    path = tmp_path / "backup_settings.json"
    store = BackupSettingsStore(path)
    store.save(BackupSettings())

    store.save(BackupSettings(1, 2))

    assert store.load() == BackupSettings(1, 2)
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "contents",
    [
        "{",
        "[]",
        "null",
        '{"schema_version": 2, "backup_interval_hours": 24, "max_backups": 10}',
        '{"schema_version": true, "backup_interval_hours": 24, "max_backups": 10}',
        '{"schema_version": 1, "backup_interval_hours": 24}',
        '{"schema_version": 1, "backup_interval_hours": 24, "max_backups": 10, "api_key": "secret"}',
        '{"schema_version": 1, "backup_interval_hours": "24", "max_backups": 10}',
        '{"schema_version": 1, "backup_interval_hours": 24, "max_backups": 1}',
    ],
)
def test_rejects_invalid_file_without_overwriting(
    tmp_path: Path, contents: str
) -> None:
    path = tmp_path / "backup_settings.json"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(BackupSettingsStoreError):
        BackupSettingsStore(path).load()

    assert path.read_text(encoding="utf-8") == contents


def test_rejects_non_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "backup_settings.json"
    path.write_bytes(b"\xff")

    with pytest.raises(BackupSettingsStoreError):
        BackupSettingsStore(path).load()


def test_replace_failure_preserves_previous_settings(tmp_path: Path) -> None:
    path = tmp_path / "backup_settings.json"
    store = BackupSettingsStore(path)
    store.save(BackupSettings())
    old_content = path.read_bytes()

    with patch(
        "book_manager.config.backup_settings_store.os.replace",
        side_effect=PermissionError("access denied"),
    ):
        with pytest.raises(BackupSettingsStoreError, match="保存できません"):
            store.save(BackupSettings(48, 5))

    assert path.read_bytes() == old_content
    assert store.load() == BackupSettings()
    assert not list(tmp_path.glob(".backup_settings.json.*.tmp"))


def test_rejects_wrong_save_type(tmp_path: Path) -> None:
    path = tmp_path / "backup_settings.json"
    with pytest.raises(TypeError):
        BackupSettingsStore(path).save(None)  # type: ignore[arg-type]
    assert not path.exists()
