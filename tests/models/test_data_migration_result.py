"""利用者データ移行結果Modelのテスト。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)


def test_data_migration_status_has_expected_values() -> None:
    """移行状態が永続化や表示に利用できる値を持つ。"""
    assert DataMigrationStatus.NOT_NEEDED.value == "not_needed"
    assert (
        DataMigrationStatus.NO_LEGACY_DATA.value
        == "no_legacy_data"
    )
    assert DataMigrationStatus.MIGRATED.value == "migrated"
    assert (
        DataMigrationStatus.MIGRATED_WITH_WARNINGS.value
        == "migrated_with_warnings"
    )


def test_data_migration_status_is_string_enum() -> None:
    """移行状態を文字列として扱える。"""
    assert isinstance(
        DataMigrationStatus.MIGRATED,
        str,
    )
    assert (
        DataMigrationStatus.MIGRATED
        == "migrated"
    )


def test_data_migration_result_uses_default_counts_and_warnings(
    tmp_path: Path,
) -> None:
    """件数と警告の既定値が空の移行結果を生成できる。"""
    destination_path = tmp_path / "books.db"

    result = DataMigrationResult(
        status=DataMigrationStatus.NO_LEGACY_DATA,
        source_database_path=None,
        destination_database_path=destination_path,
    )

    assert result.status is DataMigrationStatus.NO_LEGACY_DATA
    assert result.source_database_path is None
    assert result.destination_database_path == destination_path
    assert result.migrated_backup_count == 0
    assert result.migrated_cover_count == 0
    assert result.warnings == ()


def test_data_migration_result_holds_migrated_values(
    tmp_path: Path,
) -> None:
    """正常な移行結果を保持できる。"""
    source_path = tmp_path / "old" / "books.db"
    destination_path = tmp_path / "new" / "books.db"

    result = DataMigrationResult(
        status=DataMigrationStatus.MIGRATED,
        source_database_path=source_path,
        destination_database_path=destination_path,
        migrated_backup_count=3,
        migrated_cover_count=5,
    )

    assert result.status is DataMigrationStatus.MIGRATED
    assert result.source_database_path == source_path
    assert result.destination_database_path == destination_path
    assert result.migrated_backup_count == 3
    assert result.migrated_cover_count == 5
    assert result.warnings == ()


def test_data_migration_result_holds_warnings(
    tmp_path: Path,
) -> None:
    """警告付きの移行結果を保持できる。"""
    warnings = (
        "バックアップを1件コピーできませんでした。",
        "表紙画像を2件コピーできませんでした。",
    )

    result = DataMigrationResult(
        status=(
            DataMigrationStatus.MIGRATED_WITH_WARNINGS
        ),
        source_database_path=(
            tmp_path
            / "old"
            / "books.db"
        ),
        destination_database_path=(
            tmp_path
            / "new"
            / "books.db"
        ),
        migrated_backup_count=2,
        migrated_cover_count=4,
        warnings=warnings,
    )

    assert result.warnings == warnings


def test_data_migration_result_is_immutable(
    tmp_path: Path,
) -> None:
    """生成した移行結果を変更できない。"""
    result = DataMigrationResult(
        status=DataMigrationStatus.NOT_NEEDED,
        source_database_path=None,
        destination_database_path=tmp_path / "books.db",
    )

    with pytest.raises(FrozenInstanceError):
        result.status = (  # type: ignore[misc]
            DataMigrationStatus.MIGRATED
        )


def test_data_migration_result_rejects_negative_backup_count(
    tmp_path: Path,
) -> None:
    """負のバックアップ件数を拒否する。"""
    with pytest.raises(
        ValueError,
        match="移行済みバックアップ数は0以上",
    ):
        DataMigrationResult(
            status=DataMigrationStatus.MIGRATED,
            source_database_path=tmp_path / "old.db",
            destination_database_path=tmp_path / "new.db",
            migrated_backup_count=-1,
        )


def test_data_migration_result_rejects_negative_cover_count(
    tmp_path: Path,
) -> None:
    """負の表紙画像件数を拒否する。"""
    with pytest.raises(
        ValueError,
        match="移行済み表紙画像数は0以上",
    ):
        DataMigrationResult(
            status=DataMigrationStatus.MIGRATED,
            source_database_path=tmp_path / "old.db",
            destination_database_path=tmp_path / "new.db",
            migrated_cover_count=-1,
        )


def test_warning_status_requires_warning_message(
    tmp_path: Path,
) -> None:
    """警告付き状態には警告内容を必須とする。"""
    with pytest.raises(
        ValueError,
        match="警告付き移行結果には警告内容が必要",
    ):
        DataMigrationResult(
            status=(
                DataMigrationStatus.MIGRATED_WITH_WARNINGS
            ),
            source_database_path=tmp_path / "old.db",
            destination_database_path=tmp_path / "new.db",
        )


def test_warning_messages_require_warning_status(
    tmp_path: Path,
) -> None:
    """警告内容には警告付き状態を必須とする。"""
    with pytest.raises(
        ValueError,
        match="警告付き移行状態を指定してください。",
    ):
        DataMigrationResult(
            status=DataMigrationStatus.MIGRATED,
            source_database_path=tmp_path / "old.db",
            destination_database_path=tmp_path / "new.db",
            warnings=("表紙画像をコピーできませんでした。",),
        )


def test_data_migration_results_with_same_values_are_equal(
    tmp_path: Path,
) -> None:
    """同じ値を持つ移行結果を等価として扱う。"""
    parameters = {
        "status": DataMigrationStatus.MIGRATED,
        "source_database_path": tmp_path / "old.db",
        "destination_database_path": tmp_path / "new.db",
        "migrated_backup_count": 2,
        "migrated_cover_count": 3,
    }

    first = DataMigrationResult(**parameters)
    second = DataMigrationResult(**parameters)

    assert first == second
