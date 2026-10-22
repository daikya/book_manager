"""著者統合の確認・順序・再検査・原子性。"""
from dataclasses import replace
from unittest.mock import patch
import pytest
from book_manager.database.initializer import initialize_database
from book_manager.database.connection import create_connection
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService


@pytest.fixture
def data(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    repo = AuthorRepository(path)
    authors = AuthorService(repo)
    books = BookService(BookRepository(path))
    source = authors.create(name='山田 太郎', aliases=['旧筆名', '共通'], disambiguation_note='統合元メモ')
    target = authors.create(name='山田太郎', aliases=['共通', '別表記'], disambiguation_note='統合先メモ')
    other = authors.create(name='他の人')
    a = books.add_book(title='元だけ', author='原表記', tags=['保持'], author_ids=[other.id,source.id])
    b = books.add_book(title='両方・元が先', author_ids=[source.id,other.id,target.id])
    c = books.add_book(title='両方・先が先', author_ids=[target.id,other.id,source.id])
    d = books.add_book(title='先だけ',author_ids=[target.id])
    return path,repo,authors,books,source,target,other,(a,b,c,d)


def dump(path):
    conn = create_connection(path)
    try:return '\n'.join(conn.iterdump())
    finally:conn.close()


def test_preview_is_read_only_and_merge_preserves_books(data):
    path,repo,authors,books,source,target,other,items = data
    before = dump(path)
    plan = authors.preview_merge(source.id,target.id)
    assert dump(path) == before
    assert plan.aliases == ('共通','別表記','山田 太郎','旧筆名')
    assert '統合元メモ' in plan.suggested_note and '統合先メモ' in plan.suggested_note
    merged = authors.merge(plan,disambiguation_note=plan.suggested_note)
    assert merged.id == target.id and merged.name == target.name
    assert merged.created_at == target.created_at
    assert authors.get(source.id) is None
    assert [repo.book_author_ids(book.id) for book in items] == [
        (other.id,target.id),(target.id,other.id),(target.id,other.id),(target.id,)]
    assert [books.get_book(book.id) for book in items] == list(items)
    assert authors.usage_counts() == {target.id:4,other.id:3}
    assert authors.search('旧筆名')[0].author.id == target.id


@pytest.mark.parametrize('change', ['source','target','new_source_link','new_target_link','reorder','book_title','book_author','delete_book'])
def test_stale_plan_is_rejected_without_partial_changes(data,change):
    path,repo,authors,books,source,target,other,items = data
    plan = authors.preview_merge(source.id,target.id)
    if change in ('source','target'):
        person = source if change=='source' else target
        authors.update(author_id=person.id,name=person.name,aliases=['変更'])
    elif change.startswith('new_'):
        books.add_book(title='追加',author_ids=[source.id if change=='new_source_link' else target.id])
    elif change=='reorder':authors.set_book_authors(items[0].id,[source.id,other.id])
    elif change=='book_title':books.update_book(replace(items[0],title='変更'))
    elif change=='book_author':books.update_book(replace(items[0],author='変更'))
    else:
        conn=create_connection(path)
        with conn:conn.execute('DELETE FROM book_items WHERE id=?',(items[0].id,))
        conn.close()
    before = dump(path)
    with pytest.raises(ValueError,match='変更'):
        authors.merge(plan,disambiguation_note=plan.suggested_note)
    assert dump(path)==before


def test_failure_midway_rolls_back_author_aliases_and_all_links(data):
    path,repo,authors,books,source,target,other,items=data
    plan=authors.preview_merge(source.id,target.id)
    before=dump(path)
    original=repo.set_book_authors
    count=0
    def fail(*args,**kwargs):
        nonlocal count
        original(*args,**kwargs)
        count+=1
        if count==2:raise RuntimeError('途中失敗')
    with patch.object(repo,'set_book_authors',side_effect=fail),pytest.raises(RuntimeError):
        authors.merge(plan,disambiguation_note=plan.suggested_note)
    assert dump(path)==before


def test_overlong_note_cannot_silently_truncate(data):
    path,repo,authors,books,source,target,other,items=data
    plan=authors.preview_merge(source.id,target.id)
    before=dump(path)
    with pytest.raises(ValueError):authors.merge(plan,disambiguation_note='x'*2001)
    assert dump(path)==before


def test_same_id_and_missing_author_rejected(data):
    path,repo,authors,books,source,target,other,items=data
    with pytest.raises(ValueError):authors.preview_merge(source.id,source.id)
    with pytest.raises(ValueError):authors.preview_merge(source.id,999999)


def test_unused_homonyms_can_be_explicitly_merged(data):
    path,repo,authors,books,source,target,other,items=data
    a=authors.create(name='同名',disambiguation_note='A')
    b=authors.create(name='同名',disambiguation_note='B')
    plan=authors.preview_merge(a.id,b.id)
    assert plan.books==()
    result=authors.merge(plan,disambiguation_note='確認したメモ')
    assert result.aliases==() and result.disambiguation_note=='確認したメモ'
    assert authors.get(a.id) is None


def test_tampered_plan_is_rejected(data):
    path,repo,authors,books,source,target,other,items=data
    plan=authors.preview_merge(source.id,target.id)
    with pytest.raises(ValueError):authors.merge(replace(plan,aliases=()),disambiguation_note='')


def test_merged_author_roundtrips_complete_zip(data,tmp_path):
    from book_manager.repositories.csv_data_package_repository import CsvDataPackageRepository
    from book_manager.repositories.csv_data_package_restore_repository import CsvDataPackageRestoreRepository
    from book_manager.services.csv_data_package_export_service import CsvDataPackageExportService
    from book_manager.services.csv_data_package_archive_validator import CsvDataPackageArchiveValidator
    from book_manager.services.csv_data_package_preflight_service import CsvDataPackagePreflightService
    from book_manager.services.csv_data_package_import_service import CsvDataPackageImportService
    from book_manager.services.backup_service import BackupService
    path,repo,authors,books,source,target,other,items=data
    plan=authors.preview_merge(source.id,target.id)
    authors.merge(plan,disambiguation_note=plan.suggested_note)
    archive=tmp_path/'merged.zip'
    CsvDataPackageExportService(CsvDataPackageRepository(path),application_version_provider=lambda:'2.8.0-dev').export(archive)
    expected=CsvDataPackageRepository(path).export_snapshot()
    validator=CsvDataPackageArchiveValidator()
    preview=CsvDataPackagePreflightService(validator).preview(archive)
    assert preview.can_import,preview.errors
    restored=tmp_path/'restored.db';initialize_database(restored)
    service=CsvDataPackageImportService(database_path=restored,
        backup_service=BackupService(database_path=restored,backup_directory=tmp_path/'backups'),
        archive_validator=validator,restore_repository=CsvDataPackageRestoreRepository())
    service.import_preview(preview)
    assert CsvDataPackageRepository(restored).export_snapshot()==expected


def test_source_deleted_after_preview_is_rejected(data):
    path,repo,authors,books,source,target,other,items=data
    unused=authors.create(name='未使用')
    plan=authors.preview_merge(unused.id,target.id)
    authors.delete(unused.id)
    before=dump(path)
    with pytest.raises(ValueError):authors.merge(plan,disambiguation_note='')
    assert dump(path)==before
