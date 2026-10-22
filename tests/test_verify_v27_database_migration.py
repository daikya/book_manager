"""配布版移行検証スクリプトの正常系と不一致検出。"""
import importlib.util
from pathlib import Path
import sqlite3
import pytest
from book_manager.database.initializer import initialize_database

_spec = importlib.util.spec_from_file_location('v27_migration_verifier',
    Path(__file__).resolve().parents[1] / 'scripts' / 'verify_v27_database_migration.py')
verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verifier)


@pytest.fixture
def source(tmp_path):
    path=tmp_path/'original'/'data'/'books.db'
    initialize_database(path)
    with sqlite3.connect(path) as conn:
        conn.execute('DROP TABLE book_item_authors')
        conn.execute('DROP TABLE author_aliases')
        conn.execute('DROP TABLE authors')
        conn.execute("INSERT INTO book_items(title,author,reference_isbn,created_at,updated_at) VALUES ('本','原 著者','9784101010014','a','b')")
        conn.execute("INSERT INTO reading_histories(book_item_id,started_on,completed_on,notes,created_at,updated_at) VALUES (1,'2026-01','2026-02','履歴','a','b')")
        conn.execute("INSERT INTO tags(name,created_at,updated_at) VALUES ('タグ','a','b')")
        conn.execute('INSERT INTO book_item_tags VALUES (1,1)')
        conn.execute('PRAGMA user_version=8')
    return path


def test_prepare_migrate_verify_twice_and_keep_source(source,tmp_path):
    work=tmp_path/'verification'
    covers=source.parent.parent/'cache'/'covers';covers.mkdir(parents=True)
    (covers/'cover.png').write_bytes(b'test cover')
    original=verifier.digest(source)
    verifier.prepare(source,work)
    assert (work/'cache'/'covers'/'cover.png').read_bytes()==b'test cover'
    target=work/'data'/'books.db'
    initialize_database(target)
    first=verifier.verify(work)
    assert first['result']=='PASS' and first['source_unchanged']
    assert first['author_counts']==dict.fromkeys(verifier.AUTHOR_TABLES,0)
    assert first['migration_backup_count']==1
    initialize_database(target)
    assert verifier.verify(work)['result']=='PASS'
    assert verifier.digest(source)==original
    assert (work/'author_migration_verification_report.json').is_file()


def test_wrong_version_refuses_without_creating_work(source,tmp_path):
    initialize_database(source)
    work=tmp_path/'verification'
    with pytest.raises(ValueError,match='schema 8'):verifier.prepare(source,work)
    assert not work.exists()


def test_existing_work_directory_not_overwritten(source,tmp_path):
    work=tmp_path/'verification';work.mkdir();marker=work/'keep';marker.write_text('keep')
    with pytest.raises(ValueError,match='already exists'):verifier.prepare(source,work)
    assert marker.read_text()=='keep'


def test_data_change_detected(source,tmp_path):
    work=tmp_path/'verification';verifier.prepare(source,work)
    target=work/'data'/'books.db';initialize_database(target)
    with sqlite3.connect(target) as conn:conn.execute("UPDATE book_items SET author='変更'")
    result=verifier.verify(work)
    assert result['result']=='FAIL'
    assert 'Original data or autoincrement sequences changed' in result['failures']


def test_source_change_detected(source,tmp_path):
    work=tmp_path/'verification';verifier.prepare(source,work)
    initialize_database(work/'data'/'books.db')
    with sqlite3.connect(source) as conn:conn.execute("UPDATE book_items SET title='変更'")
    assert not verifier.verify(work)['source_unchanged']


def test_missing_backup_detected(source,tmp_path):
    work=tmp_path/'verification';verifier.prepare(source,work)
    target=work/'data'/'books.db';initialize_database(target)
    for backup in (target.parent/'schema_backups').glob('*.db'):backup.unlink()
    assert verifier.verify(work)['result']=='FAIL'


def test_author_registration_during_migration_check_is_reported(source,tmp_path):
    work=tmp_path/'verification';verifier.prepare(source,work)
    target=work/'data'/'books.db';initialize_database(target)
    with sqlite3.connect(target) as conn:
        conn.execute("INSERT INTO authors(name,name_key,created_at,updated_at) VALUES ('追加','追加','a','b')")
    result=verifier.verify(work)
    assert result['result']=='FAIL' and result['author_counts']['authors']==1


def test_nonempty_wal_refused(source,tmp_path):
    with sqlite3.connect(source) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute("UPDATE book_items SET title='変更'");conn.commit()
        with pytest.raises(ValueError,match='WAL'):verifier.prepare(source,tmp_path/'verification')
