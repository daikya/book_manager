"""実DBと各入出力経路で雑誌コードの互換性を検証する。"""
import csv
from dataclasses import replace
import pytest
from openpyxl import Workbook
from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.book_service import BookService
from book_manager.services.csv_export_service import CsvExportService
from book_manager.services.csv_import_service import CsvImportService
from book_manager.validators.magazine_code_validator import (
    normalize_magazine_code, validate_magazine_code, format_magazine_code,
)


@pytest.mark.parametrize('value', ['17651', '1765107', '17651-07', ' 17651-07 ', '00001-07'])
def test_input_and_display(value):
    validate_magazine_code(value)
    code = normalize_magazine_code(value)
    assert '-' not in code
    assert format_magazine_code(code) == (code[:5] + '-' + code[5:] if len(code) == 7 else code)


@pytest.mark.parametrize('value', ['1765-107', '17651--07', '17651-7', '１７６５１-０７', '17651-0A'])
def test_bad_hyphen_or_non_ascii_input(value):
    with pytest.raises(ValueError):
        validate_magazine_code(value)


def make_books(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    return path, BookRepository(path), BookService(BookRepository(path))


def test_registration_update_search_and_legacy_data(tmp_path):
    db, repo, books = make_books(tmp_path)
    first = books.add_book(title='VIDEO SALON 2020年7月号', magazine_code='17651-07')
    second = books.add_book(title='VIDEO SALON 2021年7月号', magazine_code='1765107')
    assert first.magazine_code == second.magazine_code == '1765107'
    assert books.find_duplicate_candidates(magazine_code='17651-07') == []
    assert {b.id for b in books.find_books_by_magazine_code('17651-07')} == {first.id, second.id}
    assert len(books.search_books(magazine_code='1765107')) == 2
    books.update_book(replace(first, magazine_code='17651-08'))
    assert books.get_book(first.id).magazine_code == '1765108'
    with create_connection(db) as connection:
        connection.execute('UPDATE book_items SET magazine_code = ? WHERE id = ?', ('17651-07', second.id))
    assert books.find_books_by_magazine_code('1765107')[0].id == second.id
    assert books.search_books(magazine_code='17651-07')[0].id == second.id
    books.add_book(title='ISBN対象', isbn='9784101010014')
    assert len(books.find_duplicate_candidates(isbn='9784101010014')) == 1


def test_csv_preview_and_import_allow_repeated_code(tmp_path):
    _, repo, books = make_books(tmp_path)
    books.add_book(title='既存', magazine_code='1765107')
    path = tmp_path / 'books.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=CsvImportService.HEADERS)
        writer.writeheader()
        for code in ('17651-07', '1765107'):
            writer.writerow({'書籍名': code, '雑誌コード': code, 'お気に入り': 'いいえ'})
    importer = CsvImportService(book_service=books)
    preview = importer.preview_file(path)
    assert preview.importable_count == 2
    assert preview.skipped_count == preview.error_count == 0
    result = importer.import_file(path)
    assert result.imported_count == 2
    assert result.skipped_count == result.error_count == 0
    out = tmp_path / 'output.csv'
    CsvExportService().export(repo.get_all(), out)
    with out.open(encoding='utf-8-sig', newline='') as file:
        assert {row['雑誌コード'] for row in csv.DictReader(file)} == {'17651-07'}


def test_complete_zip_roundtrip(tmp_path):
    from book_manager.repositories.csv_data_package_repository import CsvDataPackageRepository
    from book_manager.repositories.csv_data_package_restore_repository import CsvDataPackageRestoreRepository
    from book_manager.services.csv_data_package_export_service import CsvDataPackageExportService
    from book_manager.services.csv_data_package_preflight_service import CsvDataPackagePreflightService
    from book_manager.services.csv_data_package_archive_validator import CsvDataPackageArchiveValidator
    db, _, books = make_books(tmp_path)
    for year in (2020, 2021):
        books.add_book(title=f'VIDEO SALON {year}', magazine_code='17651-07')
    package = tmp_path / 'complete.zip'
    source = CsvDataPackageRepository(db)
    CsvDataPackageExportService(source, application_version_provider=lambda: '2.8.0').export(package)
    preview = CsvDataPackagePreflightService(CsvDataPackageArchiveValidator()).preview(package)
    assert preview.can_import
    assert [b.magazine_code for b in preview.book_items] == ['1765107', '1765107']
    target = tmp_path / 'target.db'
    initialize_database(target)
    with create_connection(target) as connection:
        CsvDataPackageRestoreRepository().restore(connection, preview)
    assert CsvDataPackageRepository(target).export_snapshot() == source.export_snapshot()


def test_excel_preflight_normalizes_code(tmp_path):
    from book_manager.services.excel_import_preflight_service import ExcelImportPreflightService
    from book_manager.models.excel_import import ExcelImportOptions
    _, _, books = make_books(tmp_path)
    path = tmp_path / 'books.xlsx'
    workbook = Workbook()
    workbook.active.append(['書籍名', '雑誌コード'])
    workbook.active.append(['2020年7月', '17651-07'])
    workbook.active.append(['2021年7月', '1765107'])
    workbook.save(path)
    workbook.close()
    preview = ExcelImportPreflightService(book_service=books).preview_file(
        path, options=ExcelImportOptions((('title', 1), ('magazine_code', 2))),
    )
    assert not preview.errors
    assert [r.book.magazine_code for r in preview.records] == ['1765107', '1765107']
