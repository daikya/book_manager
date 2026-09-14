"""利用者のバックアップ設定をJSONファイルへ保存する。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from book_manager.models.backup_settings import BackupSettings


class BackupSettingsStoreError(RuntimeError):
    """バックアップ設定ファイルを読み書きできない場合。"""


class BackupSettingsStore:
    """バックアップ設定の永続化。保存先は利用者データ領域のパス。"""

    SCHEMA_VERSION = 1

    def __init__(self, settings_path: Path) -> None:
        self._settings_path = Path(settings_path)

    def load(self) -> BackupSettings:
        """ファイルがない場合は既定値を返し、破損時は通知可能な例外を返す。"""
        try:
            with self._settings_path.open(encoding="utf-8") as stream:
                data = json.load(stream)
        except FileNotFoundError:
            # 設定ファイルがない初回起動だけ、既定値で開始する。
            if not self._settings_path.exists() and not self._settings_path.is_symlink():
                return BackupSettings()
            raise BackupSettingsStoreError(
                "バックアップ設定ファイルを読み込めません。"
            ) from None
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise BackupSettingsStoreError(
                "バックアップ設定ファイルを読み込めません。"
            ) from error

        if (
            not isinstance(data, dict)
            or set(data) != {
                "schema_version",
                "backup_interval_hours",
                "max_backups",
            }
            or type(data["schema_version"]) is not int
            or data["schema_version"] != self.SCHEMA_VERSION
        ):
            raise BackupSettingsStoreError(
                "バックアップ設定の形式またはVersionに対応していません。"
            )

        try:
            return BackupSettings(
                backup_interval_hours=data["backup_interval_hours"],
                max_backups=data["max_backups"],
            )
        except ValueError as error:
            raise BackupSettingsStoreError(
                "バックアップ設定の値が不正です。"
            ) from error

    def save(self, settings: BackupSettings) -> None:
        """一時ファイルを同期してから置き換え、失敗時は旧設定を残す。"""
        if not isinstance(settings, BackupSettings):
            raise TypeError("BackupSettingsを指定してください。")

        temporary_path: Path | None = None
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=f".{self._settings_path.name}.",
                suffix=".tmp",
                dir=self._settings_path.parent,
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(
                    {
                        "schema_version": self.SCHEMA_VERSION,
                        "backup_interval_hours": settings.backup_interval_hours,
                        "max_backups": settings.max_backups,
                    },
                    stream,
                    ensure_ascii=False,
                    indent=2,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary_path, self._settings_path)
        except OSError as error:
            raise BackupSettingsStoreError(
                "バックアップ設定を保存できません。"
            ) from error
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    # 主エラーを隠さない。次回のloadは確定ファイルだけ読む。
                    pass
