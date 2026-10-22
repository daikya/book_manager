"""Schema 8→9の全既存データ保持と移行失敗の原子性。"""
import hashlib
import sqlite3
from unittest.mock import patch
import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_STATEMENTS
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.backup_service import BackupService


def create_v8(path):
    initialize_database(path)
    with create_connection(path) as conn:
        conn.execute('DROP TABLE book_item_authors')
        conn.execute('DROP TABLE author_aliases')
        conn.execute('DROP TABLE authors')
        conn.execute("INSERT INTO book_items(id,title,author,reference_isbn,notes,created_at,updated_at) VALUES (7,'本','山田 太郎,1961-','9784101010014','既存備考','a','b')")
        conn.execute("INSERT INTO tags(id,name,created_at,updated_at) VALUES (9,'タグ','a','b')")
        conn.execute('INSERT INTO book_item_tags VALUES (7,9)')
        conn.execute("INSERT INTO reading_histories(id,book_item_id,started_on,completed_on,notes,created_at,updated_at) VALUES (50,7,'2026-01','2026-02','履歴備考','a','b')")
        conn.execute('PRAGMA user_version=8')


def data(path):
    with sqlite3.connect(path) as conn:
        return {table:conn.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                for table in ['book_items','tags','book_item_tags','reading_histories','sqlite_sequence']}


def test_version8_preserved_backup_verified_and_second_start_idempotent(tmp_path):
    path=tmp_path/'books.db';create_v8(path);before=data(path)
    initialize_database(path)
    assert data(path)==before
    with sqlite3.connect(path) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==9
        for table in ['authors','author_aliases','book_item_authors']:
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==0
        assert conn.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    backups=list((tmp_path/'schema_backups').glob('before_v8_to_v9_*.db'))
    assert len(backups)==1 and data(backups[0])==before
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==8
    initialize_database(path)
    assert len(list((tmp_path/'schema_backups').glob('*.db')))==1


def test_ddl_failure_rolls_back_version_tables_and_data(tmp_path):
    path=tmp_path/'books.db';create_v8(path);before=data(path)
    statements=SCHEMA_STATEMENTS+('INSERT INTO nonexistent_table VALUES (1)',)
    with patch('book_manager.database.initializer.SCHEMA_STATEMENTS',statements):
        with pytest.raises(sqlite3.OperationalError): initialize_database(path)
    assert data(path)==before
    with sqlite3.connect(path) as conn:
        assert conn.execute('PRAGMA user_version').fetchone()[0]==8
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name='authors'").fetchall()
    assert len(list((tmp_path/'schema_backups').glob('*.db')))==1


def test_backup_failure_leaves_database_unchanged(tmp_path):
    path=tmp_path/'books.db';create_v8(path)
    original=hashlib.sha256(path.read_bytes()).hexdigest()
    with patch('book_manager.database.initializer._create_migration_backup',side_effect=OSError('blocked')):
        with pytest.raises(OSError):initialize_database(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==original


def test_backup_restore_preserves_author_names_aliases_links(tmp_path):
    path=tmp_path/'books.db';create_v8(path);initialize_database(path)
    service=AuthorService(AuthorRepository(path))
    author=service.create(name='山田太郎',aliases=['山田 太郎'],disambiguation_note='経済学')
    service.set_book_authors(7,[author.id])
    backups=BackupService(database_path=path,backup_directory=tmp_path/'backups')
    backup=backups.create_backup()
    service.update(author_id=author.id,name='変更',aliases=[])
    service.set_book_authors(7,[])
    backups.restore_backup(backup)
    assert service.get(author.id)==author
    assert service.get_book_authors(7)==[author]
