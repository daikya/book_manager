"""BackupServiceのテスト。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_VERSION
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


def _create_restore_source_database(
    database_path: Path,
    *,
    schema_version: int = SCHEMA_VERSION,
) -> None:
    """復元テスト用Book Manager DBを作成する。"""
    connection = sqlite3.connect(
        database_path,
    )

    try:
        connection.execute(
            """
            CREATE TABLE book_items (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO book_items (
                title
            )
            VALUES (?)
            """,
            ("復元テスト書籍",),
        )
        connection.execute(
            f"PRAGMA user_version = {schema_version}"
        )
        connection.commit()
    finally:
        connection.close()


def _create_initialized_book_manager_database(
    database_path: Path,
    *,
    marker: str,
) -> None:
    """実際のスキーマを使った復元テスト用DBを作成する。"""
    initialize_database(
        database_path,
    )

    connection = sqlite3.connect(
        database_path,
    )

    try:
        connection.execute(
            """
            CREATE TABLE restore_test_marker (
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO restore_test_marker (
                value
            )
            VALUES (?)
            """,
            (marker,),
        )
        connection.commit()
    finally:
        connection.close()


def _insert_book_and_reading_history(
    database_path: Path,
    *,
    title: str,
    history_notes: str,
) -> None:
    """書籍と一回分の読書履歴をテスト用DBへ登録する。"""
    connection = sqlite3.connect(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    title,
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO reading_histories (
                    book_item_id,
                    started_on,
                    completed_on,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    book_cursor.lastrowid,
                    "2026-09-01",
                    "2026-09-07",
                    history_notes,
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )
    finally:
        connection.close()


def test_create_backup_creates_backup_without_interval_check(
    tmp_path: Path,
) -> None:
    """時間間隔に関係なくバックアップを作成する。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    backup_directory.mkdir()

    existing_backup = (
        backup_directory
        / "books_20260901_100000.db"
    )
    existing_backup.touch()

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            9,
            1,
            10,
            30,
            0,
        ),
    )

    result = service.create_backup()

    expected_path = (
        backup_directory
        / "books_20260901_103000.db"
    )

    assert result == expected_path
    assert expected_path.is_file()


def test_create_backup_returns_none_when_database_missing(
    tmp_path: Path,
) -> None:
    """元DBが存在しない場合は強制バックアップしない。"""
    backup_directory = tmp_path / "backups"

    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=backup_directory,
    )

    result = service.create_backup()

    assert result is None
    assert not backup_directory.exists()


def test_get_backup_status_reports_empty_directory(tmp_path: Path) -> None:
    """バックアップが存在しない場合の表示値を返す。"""
    directory = tmp_path / "backups"
    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=directory,
    )

    status = service.get_backup_status()

    assert status.backup_directory == directory
    assert status.backup_count == 0
    assert status.latest_backup_path is None
    assert status.latest_backup_datetime is None
    assert not directory.exists()


def test_consecutive_backups_same_second_preserve_both(tmp_path: Path) -> None:
    """同一秒の手動作成でも最初のバックアップを上書きしない。"""
    database_path = tmp_path / "books.db"
    _create_test_database(database_path)
    service = BackupService(
        database_path=database_path,
        backup_directory=tmp_path / "backups",
        now_provider=lambda: datetime(2026, 9, 14, 10, 30, 0),
    )

    first = service.create_backup()
    assert first is not None
    first_contents = first.read_bytes()
    second = service.create_backup()

    assert second is not None
    assert first.name == "books_20260914_103000.db"
    assert second.name == "books_20260914_103000_001.db"
    assert first.read_bytes() == first_contents
    assert second.is_file()
    status = service.get_backup_status()
    assert status.backup_count == 2
    assert status.latest_backup_path == second
    assert status.latest_backup_datetime == datetime(2026, 9, 14, 10, 30, 0)


def test_get_backup_status_excludes_unrecognized_files(tmp_path: Path) -> None:
    """状態表示は管理対象のファイル名だけ数える。"""
    directory = tmp_path / "backups"
    directory.mkdir()
    valid = directory / "books_20260914_103000.db"
    valid.touch()
    (directory / "books_20260914_103000_000.db").touch()
    (directory / "books_20260914_103000_foo.db").touch()
    (directory / "books_20260230_103000.db").touch()
    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=directory,
    )

    status = service.get_backup_status()

    assert status.backup_count == 1
    assert status.latest_backup_path == valid


def test_backup_skips_existing_same_second_file(tmp_path: Path) -> None:
    """既存バックアップの内容は保持し、次の連番に書く。"""
    database_path = tmp_path / "books.db"
    _create_test_database(database_path)
    directory = tmp_path / "backups"
    directory.mkdir()
    original = directory / "books_20260914_103000.db"
    original.write_bytes(b"existing backup")
    service = BackupService(
        database_path=database_path,
        backup_directory=directory,
        now_provider=lambda: datetime(2026, 9, 14, 10, 30, 0),
    )

    created = service.create_backup()

    assert created == directory / "books_20260914_103000_001.db"
    assert original.read_bytes() == b"existing backup"


def test_create_backup_removes_incomplete_file_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """強制バックアップ失敗時に不完全なファイルを削除する。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_test_database(
        database_path,
    )

    fixed_now = datetime(
        2026,
        9,
        1,
        10,
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
        / "books_20260901_103000.db"
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
        service.create_backup()

    assert not expected_backup_path.exists()


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


def test_backup_preserves_reading_histories(
    tmp_path: Path,
) -> None:
    """バックアップ先に書籍と読書履歴が保持される。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"
    initialize_database(database_path)
    _insert_book_and_reading_history(
        database_path,
        title="バックアップ対象書籍",
        history_notes="バックアップ対象の読書履歴",
    )
    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            9,
            7,
            11,
            0,
            0,
        ),
    )

    backup_path = service.create_backup()

    assert backup_path is not None
    connection = sqlite3.connect(backup_path)

    try:
        row = connection.execute(
            """
            SELECT
                b.title,
                rh.started_on,
                rh.completed_on,
                rh.notes
            FROM reading_histories AS rh
            INNER JOIN book_items AS b
                ON b.id = rh.book_item_id
            """
        ).fetchone()
    finally:
        connection.close()

    assert row == (
        "バックアップ対象書籍",
        "2026-09-01",
        "2026-09-07",
        "バックアップ対象の読書履歴",
    )


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


def test_validate_restore_source_accepts_valid_database(
    tmp_path: Path,
) -> None:
    """正常なBook Manager DBを復元元として受け入れる。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "backup.db"

    _create_restore_source_database(
        backup_path,
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=tmp_path / "backups",
    )

    service._validate_restore_source(
        backup_path,
    )


def test_validate_restore_source_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """存在しない復元元ファイルを拒否する。"""
    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=tmp_path / "backups",
    )

    with pytest.raises(
        FileNotFoundError,
        match="存在しません",
    ):
        service._validate_restore_source(
            tmp_path / "missing.db",
        )


def test_validate_restore_source_rejects_non_sqlite_file(
    tmp_path: Path,
) -> None:
    """SQLiteではないファイルを拒否する。"""
    backup_path = tmp_path / "backup.db"
    backup_path.write_text(
        "not a sqlite database",
        encoding="utf-8",
    )

    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=tmp_path / "backups",
    )

    with pytest.raises(
        ValueError,
        match="正常なSQLite",
    ):
        service._validate_restore_source(
            backup_path,
        )


def test_validate_restore_source_rejects_non_book_manager_database(
    tmp_path: Path,
) -> None:
    """book_itemsテーブルがないDBを拒否する。"""
    backup_path = tmp_path / "backup.db"

    _create_test_database(
        backup_path,
    )

    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=tmp_path / "backups",
    )

    with pytest.raises(
        ValueError,
        match="Book Manager",
    ):
        service._validate_restore_source(
            backup_path,
        )


def test_validate_restore_source_accepts_older_schema_version(
    tmp_path: Path,
) -> None:
    """古いスキーマVersionのDBを復元元として受け入れる。"""
    backup_path = tmp_path / "backup.db"

    _create_restore_source_database(
        backup_path,
        schema_version=max(
            0,
            SCHEMA_VERSION - 1,
        ),
    )

    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=tmp_path / "backups",
    )

    service._validate_restore_source(
        backup_path,
    )


def test_validate_restore_source_rejects_newer_schema_version(
    tmp_path: Path,
) -> None:
    """現在より新しいスキーマVersionのDBを拒否する。"""
    backup_path = tmp_path / "backup.db"

    _create_restore_source_database(
        backup_path,
        schema_version=SCHEMA_VERSION + 1,
    )

    service = BackupService(
        database_path=tmp_path / "books.db",
        backup_directory=tmp_path / "backups",
    )

    with pytest.raises(
        RuntimeError,
        match="対応していません",
    ):
        service._validate_restore_source(
            backup_path,
        )


def test_restore_backup_replaces_current_database(
    tmp_path: Path,
) -> None:
    """バックアップの内容で現在DBを置き換える。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "restore_source.db"
    backup_directory = tmp_path / "backups"

    _create_initialized_book_manager_database(
        database_path,
        marker="current-data",
    )
    _create_initialized_book_manager_database(
        backup_path,
        marker="backup-data",
    )

    fixed_now = datetime(
        2026,
        9,
        1,
        11,
        0,
        0,
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: fixed_now,
    )

    service.restore_backup(
        backup_path,
    )

    connection = sqlite3.connect(
        database_path,
    )

    try:
        row = connection.execute(
            """
            SELECT value
            FROM restore_test_marker
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "backup-data"


def test_restore_backup_restores_reading_histories(
    tmp_path: Path,
) -> None:
    """Version 7のバックアップから読書履歴を復元する。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "restore_source.db"
    backup_directory = tmp_path / "backups"
    initialize_database(database_path)
    initialize_database(backup_path)
    _insert_book_and_reading_history(
        database_path,
        title="復元前の書籍",
        history_notes="復元前の履歴",
    )
    _insert_book_and_reading_history(
        backup_path,
        title="復元対象書籍",
        history_notes="復元された読書履歴",
    )
    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            9,
            7,
            12,
            0,
            0,
        ),
    )

    service.restore_backup(backup_path)

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            """
            SELECT
                b.title,
                rh.notes
            FROM reading_histories AS rh
            INNER JOIN book_items AS b
                ON b.id = rh.book_item_id
            """
        ).fetchall()
    finally:
        connection.close()

    assert rows == [
        (
            "復元対象書籍",
            "復元された読書履歴",
        )
    ]


def test_restore_backup_creates_safety_backup(
    tmp_path: Path,
) -> None:
    """復元前の現在DBを安全バックアップとして保存する。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "restore_source.db"
    backup_directory = tmp_path / "backups"

    _create_initialized_book_manager_database(
        database_path,
        marker="current-data",
    )
    _create_initialized_book_manager_database(
        backup_path,
        marker="backup-data",
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            9,
            1,
            11,
            0,
            0,
        ),
    )

    service.restore_backup(
        backup_path,
    )

    safety_backup_path = (
        backup_directory
        / "books_20260901_110000.db"
    )

    assert safety_backup_path.is_file()

    connection = sqlite3.connect(
        safety_backup_path,
    )

    try:
        row = connection.execute(
            """
            SELECT value
            FROM restore_test_marker
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "current-data"


def test_restore_backup_does_not_change_database_when_source_invalid(
    tmp_path: Path,
) -> None:
    """復元元検証失敗時に現在DBを変更しない。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "invalid.db"
    backup_directory = tmp_path / "backups"

    _create_initialized_book_manager_database(
        database_path,
        marker="current-data",
    )

    backup_path.write_text(
        "not a sqlite database",
        encoding="utf-8",
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    with pytest.raises(
        ValueError,
        match="正常なSQLite",
    ):
        service.restore_backup(
            backup_path,
        )

    connection = sqlite3.connect(
        database_path,
    )

    try:
        row = connection.execute(
            """
            SELECT value
            FROM restore_test_marker
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "current-data"
    assert not backup_directory.exists()


def test_restore_backup_does_not_change_database_when_safety_backup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """復元前バックアップ失敗時に現在DBを変更しない。"""
    database_path = tmp_path / "books.db"
    backup_path = tmp_path / "restore_source.db"
    backup_directory = tmp_path / "backups"

    _create_initialized_book_manager_database(
        database_path,
        marker="current-data",
    )
    _create_initialized_book_manager_database(
        backup_path,
        marker="backup-data",
    )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    def raise_backup_error(
        *,
        protected_paths: set[Path] | None = None,
    ) -> Path | None:
        raise RuntimeError(
            "safety backup failed"
        )

    monkeypatch.setattr(
        service,
        "create_backup",
        raise_backup_error,
    )

    with pytest.raises(
        RuntimeError,
        match="safety backup failed",
    ):
        service.restore_backup(
            backup_path,
        )

    connection = sqlite3.connect(
        database_path,
    )

    try:
        row = connection.execute(
            """
            SELECT value
            FROM restore_test_marker
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "current-data"


def test_restore_backup_preserves_selected_oldest_backup_during_cleanup(
    tmp_path: Path,
) -> None:
    """復元元に選択した最古バックアップを世代整理で削除しない。"""
    database_path = tmp_path / "books.db"
    backup_directory = tmp_path / "backups"

    _create_initialized_book_manager_database(
        database_path,
        marker="current-data",
    )

    backup_directory.mkdir()

    restore_source_path = (
        backup_directory
        / "books_20260801_120000.db"
    )

    _create_initialized_book_manager_database(
        restore_source_path,
        marker="restore-data",
    )

    start = datetime(
        2026,
        8,
        2,
        12,
        0,
        0,
    )

    for index in range(9):
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

        _create_initialized_book_manager_database(
            backup_path,
            marker=f"backup-{index}",
        )

    service = BackupService(
        database_path=database_path,
        backup_directory=backup_directory,
        now_provider=lambda: datetime(
            2026,
            9,
            1,
            12,
            0,
            0,
        ),
        max_backups=10,
    )

    service.restore_backup(
        restore_source_path,
    )

    connection = sqlite3.connect(
        database_path,
    )

    try:
        row = connection.execute(
            """
            SELECT value
            FROM restore_test_marker
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == "restore-data"
    assert restore_source_path.is_file()

    backup_files = list(
        backup_directory.glob(
            "books_*.db"
        )
    )

    assert len(backup_files) == 10
