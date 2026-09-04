"""SQLite connection utilities."""

import sqlite3
from pathlib import Path


def create_connection(database_path: Path | str) -> sqlite3.Connection:
    """指定されたSQLiteデータベースへの接続を生成する。"""
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection
