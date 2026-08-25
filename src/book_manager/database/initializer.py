"""SQLite database initialization utilities."""

from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.database.schema import (
    MIGRATE_VERSION_2_TO_3,
    MIGRATE_VERSION_1_TO_2,
    SCHEMA_STATEMENTS,
    SCHEMA_VERSION,
)

def initialize_database(database_path: Path | str) -> None:
    """SQLiteデータベースを初期化する。

    データベースの親ディレクトリを作成し、テーブル、
    インデックスおよびスキーマVersionを設定する。

    Args:
        database_path:
            初期化するSQLiteデータベースのパス。

    Raises:
        RuntimeError:
            データベースのスキーマVersionが、
            アプリケーションの対応Versionより新しい場合。
    """
    resolved_database_path = Path(database_path)
    resolved_database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = create_connection(resolved_database_path)

    try:
        user_version_row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()

        if user_version_row is None:
            raise RuntimeError(
                "SQLiteスキーマVersionを取得できませんでした。"
            )

        user_version = int(user_version_row[0])

        if user_version > SCHEMA_VERSION:
            raise RuntimeError(
                "このデータベースのスキーマVersionは、"
                "現在のアプリケーションでは対応していません。"
                f" database={user_version}, "
                f"application={SCHEMA_VERSION}"
            )

        with connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)

            if user_version == 1:
                for statement in MIGRATE_VERSION_1_TO_2:
                    connection.execute(statement)

                for statement in MIGRATE_VERSION_2_TO_3:
                    connection.execute(statement)

            elif user_version == 2:
                for statement in MIGRATE_VERSION_2_TO_3:
                    connection.execute(statement)

            if user_version < SCHEMA_VERSION:
                connection.execute(
                    f"PRAGMA user_version = {SCHEMA_VERSION}"
                )

    finally:
        connection.close()