"""BackupSettingsのテスト。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from book_manager.models.backup_settings import BackupSettings


def test_defaults_match_existing_backup_service() -> None:
    settings = BackupSettings()

    assert settings.backup_interval_hours == 24
    assert settings.max_backups == 10
    assert settings.backup_interval == timedelta(hours=24)


@pytest.mark.parametrize("hours", [1, 168])
def test_accepts_interval_boundaries(hours: int) -> None:
    assert BackupSettings(backup_interval_hours=hours).backup_interval == (
        timedelta(hours=hours)
    )


@pytest.mark.parametrize("count", [2, 100])
def test_accepts_retention_boundaries(count: int) -> None:
    assert BackupSettings(max_backups=count).max_backups == count


@pytest.mark.parametrize("hours", [0, -1, 169, 1.5, "24", True, None])
def test_rejects_invalid_interval(hours: object) -> None:
    with pytest.raises(ValueError, match="1～168時間"):
        BackupSettings(backup_interval_hours=hours)  # type: ignore[arg-type]


@pytest.mark.parametrize("count", [0, 1, -1, 101, 2.5, "10", False, None])
def test_rejects_invalid_retention(count: object) -> None:
    with pytest.raises(ValueError, match="2～100件"):
        BackupSettings(max_backups=count)  # type: ignore[arg-type]


def test_settings_are_immutable() -> None:
    settings = BackupSettings()

    with pytest.raises(FrozenInstanceError):
        settings.max_backups = 2  # type: ignore[misc]
