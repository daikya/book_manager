"""SQLite database initialization and transactional schema migration."""

from pathlib import Path
import sqlite3
from uuid import uuid4

from book_manager.database.connection import create_connection
from book_manager.database.schema import (
    CREATE_READING_HISTORIES_TABLE,
    CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX,
    MIGRATE_VERSION_1_TO_2,
    MIGRATE_VERSION_2_TO_3,
    MIGRATE_VERSION_3_TO_4,
    MIGRATE_VERSION_4_TO_5,
    MIGRATE_VERSION_5_TO_6,
    MIGRATE_VERSION_6_TO_7,
    SCHEMA_STATEMENTS,
    SCHEMA_VERSION,
)


def _create_migration_backup(database_path: Path, version: int) -> Path:
    """通常バックアップの世代整理対象外へ移行前DBを保存する。"""
    directory = database_path.parent / "schema_backups"
    directory.mkdir(parents=True, exist_ok=True)
    backup_path = directory / f"before_v{version}_to_v{SCHEMA_VERSION}_{uuid4().hex}.db"
    # Backup APIによりWALにあるコミット済みデータも保存する。
    source = sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)
    destination = None
    try:
        with backup_path.open("xb"):
            pass
        destination = sqlite3.connect(backup_path)
        source.backup(destination)
        if destination.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("移行前バックアップの整合性検査に失敗しました。")
        if destination.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("移行前バックアップの外部キー検査に失敗しました。")
        if destination.execute("PRAGMA user_version").fetchone()[0] != version:
            raise RuntimeError("移行前バックアップのVersionが一致しません。")
    except Exception:
        if destination is not None:
            destination.close()
            destination = None
        backup_path.unlink(missing_ok=True)
        raise
    finally:
        if destination is not None:
            destination.close()
        source.close()
    return backup_path


def _migrate_version_7_to_8(connection: sqlite3.Connection) -> None:
    """参照ISBN列を追加し、年月を比較できる履歴テーブルへ移行する。"""
    connection.execute("ALTER TABLE book_items ADD COLUMN reference_isbn TEXT")
    sequence_row = connection.execute(
        "SELECT seq FROM sqlite_sequence WHERE name = 'reading_histories'"
    ).fetchone()
    sequence = int(sequence_row[0]) if sequence_row is not None else None
    connection.execute(
        CREATE_READING_HISTORIES_TABLE.replace(
            "IF NOT EXISTS reading_histories", "reading_histories_v8"
        )
    )
    columns = "id, book_item_id, started_on, completed_on, notes, created_at, updated_at"
    connection.execute(
        f"INSERT INTO reading_histories_v8 ({columns}) "
        f"SELECT {columns} FROM reading_histories"
    )
    # 内容・件数とも確認してから元テーブルを置き換える。
    for source, target in (
        ("reading_histories", "reading_histories_v8"),
        ("reading_histories_v8", "reading_histories"),
    ):
        if connection.execute(
            f"SELECT {columns} FROM {source} EXCEPT SELECT {columns} FROM {target}"
        ).fetchone() is not None:
            raise RuntimeError("読書履歴の移行内容が一致しません。")
    connection.execute("DROP TABLE reading_histories")
    connection.execute("ALTER TABLE reading_histories_v8 RENAME TO reading_histories")
    connection.execute(CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX)
    if sequence is not None:
        connection.execute(
            "UPDATE sqlite_sequence SET seq = ? WHERE name = 'reading_histories'",
            (sequence,),
        )


def initialize_database(database_path: Path | str) -> None:
    """新規DBを初期化する。旧DBはバックアップ後、1トランザクションで移行する。

    移行前バックアップはDBと同じディレクトリのschema_backupsに残す。
    Version 8→9では既存の著者名を保持し、著者・別名・関連を空で追加する。
    バックアップ失敗・移行失敗時は処理を中止する。
    """
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = create_connection(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                "このデータベースのスキーマVersionは、"
                "現在のアプリケーションでは対応していません。"
                f" database={version}, application={SCHEMA_VERSION}"
            )
        # BEGIN IMMEDIATEで他の接続による書込みを止めてから、別接続で保存する。
        if 0 < version < SCHEMA_VERSION:
            _create_migration_backup(path, version)
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        migrations = {
            1: MIGRATE_VERSION_1_TO_2,
            2: MIGRATE_VERSION_2_TO_3,
            3: MIGRATE_VERSION_3_TO_4,
            4: MIGRATE_VERSION_4_TO_5,
            5: MIGRATE_VERSION_5_TO_6,
            6: MIGRATE_VERSION_6_TO_7,
        }
        if version > 0:
            for old_version in range(version, 7):
                for statement in migrations[old_version]:
                    connection.execute(statement)
            if version < 8:
                _migrate_version_7_to_8(connection)
        if version < SCHEMA_VERSION:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("移行後DBの整合性検査に失敗しました。")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("移行後DBの外部キー検査に失敗しました。")
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
