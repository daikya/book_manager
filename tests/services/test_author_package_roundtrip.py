"""著者を含む形式3の全項目往復と不正入力・旧形式の互換性。"""
import csv
import io
import zipfile
from pathlib import Path
from dataclasses import replace
import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.models.csv_data_package import CURRENT_REQUIRED_FILE_NAMES, AUTHOR_MANIFEST_COUNT_KEYS, AUTHOR_FILE_NAMES
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.services.author_service import AuthorService
from book_manager.repositories.csv_data_package_repository import CsvDataPackageRepository
from book_manager.repositories.csv_data_package_restore_repository import CsvDataPackageRestoreRepository
from book_manager.services.csv_data_package_export_service import CsvDataPackageExportService
from book_manager.services.csv_data_package_archive_validator import CsvDataPackageArchiveValidator
from book_manager.services.csv_data_package_preflight_service import CsvDataPackagePreflightService
from book_manager.services.csv_data_package_import_service import CsvDataPackageImportService
from book_manager.services.backup_service import BackupService


def seed(path):
    initialize_database(path)
    stamp = '2026-10-01 00:00:00'
    with create_connection(path) as conn:
        conn.execute('INSERT INTO book_items(id,title,author,created_at,updated_at) VALUES (10,?,?,?,?)', ('本','取得時の 著者',stamp,stamp))
    service = AuthorService(AuthorRepository(path))
    a = service.create(name='山田太郎', aliases=['山田 太郎', '筆名Ａ'], disambiguation_note='経済学\n○○大学')
    b = service.create(name='山田太郎', aliases=['山田 太郎'], disambiguation_note='小説家')
    unused = service.create(name='未関連著者')
    service.set_book_authors(10, [b.id, a.id])
    return service


def exported(tmp_path):
    source = tmp_path / 'source.db'; seed(source)
    package = tmp_path / 'package.zip'
    CsvDataPackageExportService(CsvDataPackageRepository(source), application_version_provider=lambda: '2.8.0-dev').export(package)
    return source, package


def preview(package):
    return CsvDataPackagePreflightService(CsvDataPackageArchiveValidator()).preview(package)


def rewrite(package, change):
    with zipfile.ZipFile(package) as archive:
        rows = {name: list(csv.reader(io.StringIO(archive.read(name).decode('utf-8-sig')))) for name in archive.namelist()}
    change(rows)
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, records in rows.items():
            output = io.StringIO(newline='');csv.writer(output).writerows(records)
            archive.writestr(name, output.getvalue().encode('utf-8-sig'))


def test_full_roundtrip_preserves_homonyms_aliases_order_and_unused_author(tmp_path):
    source, package = exported(tmp_path)
    expected = CsvDataPackageRepository(source).export_snapshot()
    p = preview(package)
    assert p.can_import, p.errors
    assert p.manifest.format_version == 3
    assert p.manifest.author_count == 3
    assert len(p.author_aliases) == 3 and len(p.book_item_authors) == 2
    target = tmp_path / 'target.db';initialize_database(target)
    service = CsvDataPackageImportService(database_path=target,
        backup_service=BackupService(database_path=target, backup_directory=tmp_path/'backups'),
        archive_validator=CsvDataPackageArchiveValidator(), restore_repository=CsvDataPackageRestoreRepository())
    result = service.import_preview(p)
    assert result.author_count == 3 and result.author_alias_count == 3 and result.book_item_author_count == 2
    assert result.backup_path.is_file()
    assert CsvDataPackageRepository(target).export_snapshot() == expected
    with create_connection(target) as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


@pytest.mark.parametrize('file_name,column,value', [
    ('authors.csv',0,'A000000'), ('authors.csv',1,''), ('authors.csv',1,'a'*201),
    ('authors.csv',2,'a'*2001), ('authors.csv',3,'not-a-date'),
    ('author_aliases.csv',0,'A999999'), ('author_aliases.csv',1,''),
    ('book_item_authors.csv',0,'B999999'), ('book_item_authors.csv',1,'A999999'),
    ('book_item_authors.csv',2,'-1'), ('book_item_authors.csv',2,'True'),
    ('book_item_authors.csv',2,'1.0'), ('book_item_authors.csv',2,'９'),
    ('book_item_authors.csv',2,'999999999999999999999999999'),
])
def test_rejects_invalid_author_rows(tmp_path, file_name, column, value):
    source, package = exported(tmp_path)
    rewrite(package, lambda rows: rows[file_name][1].__setitem__(column, value))
    assert not preview(package).can_import


@pytest.mark.parametrize('file_name', ['authors.csv','author_aliases.csv','book_item_authors.csv'])
def test_duplicate_keys_or_relations_are_rejected(tmp_path, file_name):
    source, package = exported(tmp_path)
    rewrite(package, lambda rows: rows[file_name].append(rows[file_name][1][:]))
    assert not preview(package).can_import


def test_duplicate_position_is_rejected(tmp_path):
    source, package = exported(tmp_path)
    rewrite(package, lambda rows: rows['book_item_authors.csv'][2].__setitem__(2, rows['book_item_authors.csv'][1][2]))
    assert not preview(package).can_import


@pytest.mark.parametrize('missing', AUTHOR_MANIFEST_COUNT_KEYS)
def test_required_author_counts_are_checked(tmp_path, missing):
    source, package = exported(tmp_path)
    rewrite(package, lambda rows: rows.__setitem__('manifest.csv', [row for row in rows['manifest.csv'] if row[0] != missing]))
    assert not preview(package).can_import


def test_author_only_database_is_not_empty_for_restore(tmp_path):
    source, package = exported(tmp_path)
    target = tmp_path / 'target.db'; initialize_database(target)
    author = AuthorService(AuthorRepository(target)).create(name='既存著者')
    with create_connection(target) as conn:
        assert not CsvDataPackageRestoreRepository.is_database_empty(conn)
        with pytest.raises(ValueError): CsvDataPackageRestoreRepository().restore(conn, preview(package))
    assert AuthorService(AuthorRepository(target)).get(author.id) == author


@pytest.mark.parametrize('version', [1,2])
def test_legacy_five_file_packages_read_without_managed_authors(tmp_path, version):
    source, package = exported(tmp_path)
    def downgrade(rows):
        for name in AUTHOR_FILE_NAMES: del rows[name]
        rows['manifest.csv'] = [row for row in rows['manifest.csv'] if row[0] not in AUTHOR_MANIFEST_COUNT_KEYS]
        for row in rows['manifest.csv']:
            if row[0]=='format_version': row[1]=str(version)
        if version==1:
            column=rows['book_items.csv'][0].index('参照ISBN')
            for row in rows['book_items.csv']: del row[column]
    rewrite(package,downgrade)
    p=preview(package)
    assert p.can_import, p.errors
    assert p.authors == p.author_aliases == p.book_item_authors == ()
    target=tmp_path/'target.db';initialize_database(target)
    with create_connection(target) as conn: CsvDataPackageRestoreRepository().restore(conn,p)
    assert CsvDataPackageRepository(target).export_snapshot().authors == ()


def test_old_version_cannot_silently_ignore_author_files(tmp_path):
    source, package = exported(tmp_path)
    def change(rows):
        for row in rows['manifest.csv']:
            if row[0]=='format_version':row[1]='2'
            if row[0] in AUTHOR_MANIFEST_COUNT_KEYS:row[1]='0'
    rewrite(package,change)
    assert not preview(package).can_import


@pytest.mark.parametrize('count_key', AUTHOR_MANIFEST_COUNT_KEYS)
def test_manifest_author_count_mismatch_is_error(tmp_path, count_key):
    source, package=exported(tmp_path)
    def change(rows):
        for row in rows['manifest.csv']:
            if row[0]==count_key:row[1]='999'
    rewrite(package,change)
    p=preview(package)
    assert not p.can_import
    assert any(issue.column_name==count_key for issue in p.errors)


def test_format3_requires_author_files_even_when_counts_are_zero(tmp_path):
    source, package=exported(tmp_path)
    def change(rows):
        for name in AUTHOR_FILE_NAMES:del rows[name]
        for row in rows['manifest.csv']:
            if row[0] in AUTHOR_MANIFEST_COUNT_KEYS:row[1]='0'
    rewrite(package,change)
    assert not preview(package).can_import


def test_partial_author_file_set_is_rejected_by_archive_validator(tmp_path):
    source, package=exported(tmp_path)
    rewrite(package,lambda rows:rows.pop('author_aliases.csv'))
    with pytest.raises(ValueError):preview(package)


def test_restore_failure_rolls_back_all_data_and_keeps_backup(tmp_path):
    source, package=exported(tmp_path)
    p=preview(package)
    # Simulate an internal error after book/author inserts but before final validation.
    target=tmp_path/'target.db';initialize_database(target)
    from unittest.mock import patch
    service=CsvDataPackageImportService(database_path=target,
        backup_service=BackupService(database_path=target,backup_directory=tmp_path/'backups'),
        archive_validator=CsvDataPackageArchiveValidator(),restore_repository=CsvDataPackageRestoreRepository())
    with patch.object(service,'_validate_restored_database',side_effect=RuntimeError('simulated')):
        with pytest.raises(RuntimeError):service.import_preview(p)
    with create_connection(target) as conn:
        assert CsvDataPackageRestoreRepository.is_database_empty(conn)
    assert len(list((tmp_path/'backups').glob('*.db')))==1


def test_existing_author_prevents_import_before_backup(tmp_path):
    source,package=exported(tmp_path)
    target=tmp_path/'target.db';initialize_database(target)
    AuthorService(AuthorRepository(target)).create(name='既存著者')
    from unittest.mock import Mock
    backup=Mock()
    service=CsvDataPackageImportService(database_path=target,backup_service=backup,
        archive_validator=CsvDataPackageArchiveValidator(),restore_repository=CsvDataPackageRestoreRepository())
    with pytest.raises(ValueError):service.import_preview(preview(package))
    backup.create_backup.assert_not_called()


def test_export_then_export_again_retains_same_author_snapshot(tmp_path):
    source,package=exported(tmp_path)
    before=CsvDataPackageRepository(source).export_snapshot()
    with zipfile.ZipFile(package) as archive:
        assert tuple(archive.namelist())==CURRENT_REQUIRED_FILE_NAMES
    assert CsvDataPackageRepository(source).export_snapshot()==before
