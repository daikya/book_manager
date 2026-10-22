"""配布版の完全ZIP復元の独立照合。"""
import importlib.util
from pathlib import Path
import sqlite3
import pytest
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService
from book_manager.repositories.csv_data_package_repository import CsvDataPackageRepository
from book_manager.repositories.csv_data_package_restore_repository import CsvDataPackageRestoreRepository
from book_manager.services.csv_data_package_export_service import CsvDataPackageExportService
from book_manager.services.csv_data_package_archive_validator import CsvDataPackageArchiveValidator
from book_manager.services.csv_data_package_preflight_service import CsvDataPackagePreflightService
from book_manager.services.csv_data_package_import_service import CsvDataPackageImportService
from book_manager.services.backup_service import BackupService

spec=importlib.util.spec_from_file_location('author_package_verifier',Path(__file__).resolve().parents[1]/'scripts'/'verify_author_package_restore.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


@pytest.fixture
def prepared(tmp_path):
    source=tmp_path/'source';db=source/'data'/'books.db';initialize_database(db)
    authors=AuthorService(AuthorRepository(db));books=BookService(BookRepository(db))
    gone=authors.create(name='削除用');authors.delete(gone.id)
    a=authors.create(name='同名',aliases=['別名'],disambiguation_note='経済学')
    b=authors.create(name='同名',disambiguation_note='小説家')
    books.add_book(title='本',author='原 著者',author_ids=[b.id,a.id],tags=['タグ'])
    work=tmp_path/'verify';verifier.prepare(source,work)
    archive=work/'author_full_data.zip'
    CsvDataPackageExportService(CsvDataPackageRepository(db),application_version_provider=lambda:'test').export(archive)
    target=work/'restore_home'/'data'/'books.db'
    validator=CsvDataPackageArchiveValidator()
    preview=CsvDataPackagePreflightService(validator).preview(archive)
    CsvDataPackageImportService(database_path=target,
        backup_service=BackupService(database_path=target,backup_directory=work/'backups'),
        archive_validator=validator,restore_repository=CsvDataPackageRestoreRepository()).import_preview(preview)
    return db,work,target


def test_roundtrip_with_reassigned_ids_passes(prepared):
    db,work,target=prepared
    assert verifier.verify(work)['result']=='PASS'
    with sqlite3.connect(db) as conn:original=conn.execute('SELECT id FROM authors ORDER BY id').fetchall()
    with sqlite3.connect(target) as conn:restored=conn.execute('SELECT id FROM authors ORDER BY id').fetchall()
    assert original!=restored


@pytest.mark.parametrize('sql,table',[
    ("UPDATE authors SET disambiguation_note='変更'",'authors'),
    ("UPDATE author_aliases SET name='変更'",'author_aliases'),
    ("UPDATE book_items SET author='変更'",'book_items'),
    ('DELETE FROM book_item_authors WHERE position=0','book_item_authors'),
])
def test_field_or_relation_change_detected(prepared,sql,table):
    db,work,target=prepared
    with sqlite3.connect(target) as conn:conn.execute(sql)
    report=verifier.verify(work)
    assert 'Restored data mismatch: '+table in report['failures']


def test_cover_cache_path_is_excluded_but_url_is_checked(prepared):
    db,work,target=prepared
    with sqlite3.connect(target) as conn:conn.execute("UPDATE book_items SET cover_image_path='cache/covers/new.png'")
    assert verifier.verify(work)['result']=='PASS'
    with sqlite3.connect(target) as conn:conn.execute("UPDATE book_items SET cover_image_url='https://changed'")
    assert verifier.verify(work)['result']=='FAIL'


def test_source_change_and_missing_zip_detected(prepared):
    db,work,target=prepared
    with sqlite3.connect(db) as conn:conn.execute("UPDATE book_items SET title='変更'")
    (work/'author_full_data.zip').unlink()
    report=verifier.verify(work)
    assert not report['source_unchanged'] and report['package_sha256'] is None
    assert report['result']=='FAIL'


def test_coauthor_order_change_detected_with_same_counts(prepared):
    db,work,target=prepared
    with sqlite3.connect(target) as conn:
        conn.execute('UPDATE book_item_authors SET position=position+10')
        conn.execute('UPDATE book_item_authors SET position=11-position')
    result=verifier.verify(work)
    assert result['restored']['book_item_authors']['count']==result['expected']['book_item_authors']['count']
    assert 'Restored data mismatch: book_item_authors' in result['failures']


def test_different_physical_book_column_order_has_same_snapshot(prepared):
    from book_manager.database.schema import CREATE_BOOK_ITEMS_TABLE
    db,work,target=prepared
    with sqlite3.connect(target) as conn:
        conn.execute('PRAGMA foreign_keys=OFF')
        conn.execute('PRAGMA legacy_alter_table=ON')
        columns=[row[1] for row in conn.execute('PRAGMA table_info(book_items)')]
        conn.execute('ALTER TABLE book_items RENAME TO old_book_items')
        sql=CREATE_BOOK_ITEMS_TABLE.replace('    reference_isbn TEXT,\n','').replace(
            '    updated_at TEXT NOT NULL\n','    updated_at TEXT NOT NULL,\n    reference_isbn TEXT\n')
        conn.execute(sql)
        names=','.join('"'+name+'"' for name in columns)
        conn.execute(f'INSERT INTO book_items ({names}) SELECT {names} FROM old_book_items')
        conn.execute('DROP TABLE old_book_items')
        assert [row[1] for row in conn.execute('PRAGMA table_info(book_items)')][-1]=='reference_isbn'
    assert verifier.verify(work)['result']=='PASS'


def test_current_comparison_preserves_original_evidence(prepared):
    db,work,target=prepared
    original=(work/'author_package_baseline.json').read_bytes()
    for path in (db,target):
        with sqlite3.connect(path) as conn:conn.execute("UPDATE book_items SET notes='基準作成後の変更'")
    assert verifier.verify(work)['result']=='FAIL'
    old_report=(work/'author_package_verification_report.json').read_bytes()
    result=verifier.verify(work,compare_current=True)
    assert result['result']=='PASS' and result['source_unchanged']
    assert result['comparison_basis']=='current_source'
    assert not result['original_baseline_source_unchanged']
    assert (work/'author_package_baseline.json').read_bytes()==original
    assert (work/'author_package_verification_report.json').read_bytes()==old_report
    assert (work/'author_package_current_verification_report.json').is_file()


def test_current_comparison_still_detects_real_field_difference(prepared):
    db,work,target=prepared
    with sqlite3.connect(target) as conn:conn.execute("UPDATE book_items SET author='違う著者'")
    assert verifier.verify(work,compare_current=True)['result']=='FAIL'
