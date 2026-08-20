"""BackupServiceのテスト。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from book_manager.services.backup_service import BackupService


def _create_test_database(database_path: Path) -> None:
    """テスト用SQLiteデータベースを作成する。"""
    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE sample (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO sample (name)
            VALUES (?)
            """,
            ("test-data",),
        )
        connection.commit()
    finally:
        connection.close()


def test_create_backup_if_needed_creates_first_backup(
    tmp_path: Path,
) -> None:
    """バックアップがない場合は新規作成される。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    fixed_now = datetime(
        2026,
        8,
        18,
        15,
        30,
        0,
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: fixed_now,
    )

    result = service.create_backup_if_needed()

    expected_path = (
        backup_directory
        / "books_20260818_153000.db"
    )

    assert result == expected_path
    assert expected_path.is_file()


def test_backup_preserves_database_contents(
    tmp_path: Path,
) -> None:
    """バックアップ先に元DBの内容が保持される。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            8,
            18,
            15,
            30,
            0,
        ),
    )

    backup_path = service.create_backup_if_needed()

    assert backup_path is not None

    connection = sqlite3.connect(
        backup_path,
    )

    try:
        row = connection.execute(
            """
            SELECT name
            FROM sample
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "test-data"


def test_create_backup_if_needed_skips_within_24_hours(
    tmp_path: Path,
) -> None:
    """最新バックアップから24時間未満なら作成しない。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    backup_directory.mkdir()

    existing_backup = (
        backup_directory
        / "books_20260818_000000.db"
    )
    existing_backup.touch()

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            8,
            18,
            23,
            59,
            59,
        ),
    )

    result = service.create_backup_if_needed()

    assert result is None


def test_create_backup_if_needed_runs_after_24_hours(
    tmp_path: Path,
) -> None:
    """最新バックアップから24時間以上なら作成する。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    backup_directory.mkdir()

    existing_backup = (
        backup_directory
        / "books_20260817_153000.db"
    )
    existing_backup.touch()

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            8,
            18,
            15,
            30,
            0,
        ),
    )

    result = service.create_backup_if_needed()

    assert result is not None
    assert result.name == (
        "books_20260818_153000.db"
    )


def test_create_backup_if_needed_returns_none_when_database_missing(
    tmp_path: Path,
) -> None:
    """元DBが存在しない場合は何もしない。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    result = service.create_backup_if_needed()

    assert result is None
    assert not backup_directory.exists()


def test_backup_keeps_latest_ten_generations(
    tmp_path: Path,
) -> None:
    """11世代目作成時に最古のバックアップを削除する。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    backup_directory.mkdir()

    start = datetime(
        2026,
        8,
        1,
        12,
        0,
        0,
    )

    for index in range(10):
        backup_datetime = (
            start
            + timedelta(days=index)
        )

        backup_path = (
            backup_directory
            / (
                "books_"
                f"{backup_datetime:%Y%m%d_%H%M%S}"
                ".db"
            )
        )
        backup_path.touch()

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            8,
            11,
            12,
            0,
            0,
        ),
    )

    result = service.create_backup_if_needed()

    assert result is not None

    backup_files = sorted(
        backup_directory.glob(
            "books_*.db"
        )
    )

    assert len(backup_files) == 10

    assert not (
        backup_directory
        / "books_20260801_120000.db"
    ).exists()

    assert (
        backup_directory
        / "books_20260811_120000.db"
    ).exists()


@pytest.mark.parametrize(
    "backup_interval",
    [
        timedelta(0),
        timedelta(seconds=-1),
    ],
)
def test_rejects_invalid_backup_interval(
    tmp_path: Path,
    backup_interval: timedelta,
) -> None:
    """0以下のバックアップ間隔を拒否する。"""
    with pytest.raises(
        ValueError,
        match="バックアップ間隔",
    ):
        BackupService(
            database_path=tmp_path / "books.db",
            backup_directory=tmp_path / "backups",
            backup_interval=backup_interval,
        )


@pytest.mark.parametrize(
    "max_backups",
    [
        0,
        -1,
    ],
)
def test_rejects_invalid_max_backups(
    tmp_path: Path,
    max_backups: int,
) -> None:
    """0以下の保持数を拒否する。"""
    with pytest.raises(
        ValueError,
        match="バックアップ保持数",
    ):
        BackupService(
            database_path=tmp_path / "books.db",
            backup_directory=tmp_path / "backups",
            max_backups=max_backups,
        )

def test_failed_backup_removes_incomplete_backup_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """バックアップ失敗時に不完全なファイルを削除する。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    fixed_now = datetime(
        2026,
        8,
        18,
        15,
        30,
        0,
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: fixed_now,
    )

    expected_backup_path = (
        backup_directory
        / "books_20260818_153000.db"
    )

    def raise_backup_error(
        backup_path: Path,
    ) -> None:
        backup_path.touch()

        raise RuntimeError(
            "backup failed"
        )

    monkeypatch.setattr(
        service,
        "_create_backup",
        raise_backup_error,
    )

    with pytest.raises(
        RuntimeError,
        match="backup failed",
    ):
        service.create_backup_if_needed()

    assert not expected_backup_path.exists()