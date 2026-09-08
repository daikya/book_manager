"""利用者データ移行結果を表すModel。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DataMigrationStatus(str, Enum):
    """利用者データ移行の状態。"""

    NOT_NEEDED = "not_needed"
    NO_LEGACY_DATA = "no_legacy_data"
    MIGRATED = "migrated"
    MIGRATED_WITH_WARNINGS = "migrated_with_warnings"


@dataclass(frozen=True, slots=True)
class DataMigrationResult:
    """利用者データ移行の結果を保持する不変Model。"""

    status: DataMigrationStatus
    source_database_path: Path | None
    destination_database_path: Path
    migrated_backup_count: int = 0
    migrated_cover_count: int = 0
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """件数と警告の整合性を検証する。"""
        if self.migrated_backup_count < 0:
            raise ValueError(
                "移行済みバックアップ数は"
                "0以上である必要があります。"
            )

        if self.migrated_cover_count < 0:
            raise ValueError(
                "移行済み表紙画像数は"
                "0以上である必要があります。"
            )

        if (
            self.status
            is DataMigrationStatus.MIGRATED_WITH_WARNINGS
            and not self.warnings
        ):
            raise ValueError(
                "警告付き移行結果には"
                "警告内容が必要です。"
            )

        if (
            self.status
            is not DataMigrationStatus.MIGRATED_WITH_WARNINGS
            and self.warnings
        ):
            raise ValueError(
                "警告内容がある場合は"
                "警告付き移行状態を指定してください。"
            )
