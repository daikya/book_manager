"""自動バックアップの利用者設定。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class BackupSettings:
    """起動時に適用するバックアップ間隔と保持世代数。"""

    backup_interval_hours: int = 24
    max_backups: int = 10

    MIN_INTERVAL_HOURS = 1
    MAX_INTERVAL_HOURS = 168
    MIN_BACKUPS = 2
    MAX_BACKUPS = 100

    def __post_init__(self) -> None:
        if (
            type(self.backup_interval_hours) is not int
            or not self.MIN_INTERVAL_HOURS
            <= self.backup_interval_hours
            <= self.MAX_INTERVAL_HOURS
        ):
            raise ValueError(
                "自動バックアップ間隔は1～168時間の整数で指定してください。"
            )

        if (
            type(self.max_backups) is not int
            or not self.MIN_BACKUPS
            <= self.max_backups
            <= self.MAX_BACKUPS
        ):
            raise ValueError(
                "バックアップ保持世代数は2～100件の整数で指定してください。"
            )

    @property
    def backup_interval(self) -> timedelta:
        """BackupServiceに渡す間隔を返す。"""
        return timedelta(hours=self.backup_interval_hours)
