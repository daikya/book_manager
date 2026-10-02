"""単一CSVの事前検査がDBを変更しないことを確認する。"""

import csv
from pathlib import Path

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.book_service import BookService
from book_manager.services.csv_import_service import CsvImportService


def make_service(tmp_path: Path):
    database = tmp_path / "books.db"
    initialize_database(database)
    repository = BookRepository(database)
    books = BookService(repository)
    return database, repository, books, CsvImportService(book_service=books)


def write_csv(tmp_path: Path, values, *, legacy=False):
    path = tmp_path / "input.csv"
    headers = CsvImportService.LEGACY_HEADERS if legacy else CsvImportService.HEADERS
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for overrides in values:
            row = {name: "" for name in headers}
            row.update({"書籍名": "書籍", "お気に入り": "いいえ"})
            row.update(overrides)
            writer.writerow([row[name] for name in headers])
    return path


def test_preview_validates_all_rows_without_db_changes(tmp_path: Path):
    database, repository, _, service = make_service(tmp_path)
    path = write_csv(tmp_path, [
        {"書籍名": " 正常 ", "タグ": "新規|共通", "評価": "5"},
        {"書籍名": " ", "タグ": "登録されないタグ"},
        {"書籍名": "後半正常"},
    ])
    before = database.read_bytes()
    preview = service.preview_file(path)
    assert preview.importable_count == 2
    assert preview.error_count == 1
    assert preview.errors[0].row_number == 3
    assert preview.books[0].title == "正常"
    assert preview.books[0].tags == ("共通", "新規")
    assert preview.books[0].rating == 5
    assert preview.books[1].reading_status is None
    assert repository.get_all() == []
    assert repository.get_all_tags() == []
    assert database.read_bytes() == before


def test_preview_skips_existing_and_csv_duplicate_isbn(tmp_path: Path):
    database, _, books, service = make_service(tmp_path)
    books.add_book(title="既存", isbn="9784065363706")
    path = write_csv(tmp_path, [
        {"ISBN": "978-4-06-536370-6"},
        {"ISBN": "9784101010014"},
        {"ISBN": "978-4-10-101001-4"},
    ])
    before = database.read_bytes()
    preview = service.preview_file(path)
    assert preview.importable_count == 1
    assert preview.skipped_count == 2
    assert preview.error_count == 0
    assert [issue.row_number for issue in preview.skipped] == [2, 4]
    assert "既存データ" in preview.skipped[0].message
    assert "CSV内" in preview.skipped[1].message
    assert database.read_bytes() == before


def test_preview_accepts_legacy_header(tmp_path: Path):
    _, _, _, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, [{}], legacy=True))
    assert preview.importable_count == 1
    assert preview.books[0].tags == ()
    assert preview.errors == ()


def test_preview_reports_column_and_value_errors(tmp_path: Path):
    _, _, _, service = make_service(tmp_path)
    path = write_csv(tmp_path, [{"評価": "6"}, {"読書状態": "不正"}])
    with path.open("a", encoding="utf-8", newline="") as file:
        csv.writer(file).writerow(["列不足"])
    preview = service.preview_file(path)
    assert preview.importable_count == 0
    assert preview.error_count == 3
    assert [issue.row_number for issue in preview.errors] == [2, 3, 4]


def test_preview_rejects_invalid_header(tmp_path: Path):
    database, _, _, service = make_service(tmp_path)
    path = tmp_path / "bad.csv"
    path.write_text("タイトル\n書籍\n", encoding="utf-8")
    before = database.read_bytes()
    with pytest.raises(ValueError, match="ヘッダー"):
        service.preview_file(path)
    assert database.read_bytes() == before


def test_preview_empty_data(tmp_path: Path):
    _, _, _, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, []))
    assert preview.importable_count == preview.skipped_count == preview.error_count == 0


def test_reference_isbn_preview_normalizes_shares_and_reports_errors(tmp_path: Path):
    database, repository, books, service = make_service(tmp_path)
    books.add_book(title="紙版", isbn="9784101010014")
    path = write_csv(tmp_path, [
        {"書籍名": "音声版", "参照ISBN": "4101010013"},
        {"書籍名": "電子版", "参照ISBN": "978-4-10-101001-4"},
        {"参照ISBN": "invalid", "タグ": "作成されないタグ"},
    ])
    before = database.read_bytes()
    preview = service.preview_file(path)
    assert preview.importable_count == 2
    assert preview.skipped_count == 0
    assert preview.error_count == 1
    assert preview.errors[0].row_number == 4
    assert all(book.reference_isbn == "9784101010014" and book.isbn is None for book in preview.books)
    assert len(repository.get_all()) == 1
    assert repository.get_all_tags() == []
    assert database.read_bytes() == before


@pytest.mark.parametrize("headers", [CsvImportService.V26_HEADERS, CsvImportService.LEGACY_HEADERS])
def test_old_csv_preview_defaults_reference_isbn_to_none(tmp_path: Path, headers):
    _, _, _, service = make_service(tmp_path)
    path = tmp_path / "old.csv"
    values = {header: "" for header in headers}
    values.update({"書籍名": "旧形式", "お気に入り": "いいえ"})
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerow([values[h] for h in headers])
    preview = service.preview_file(path)
    assert preview.importable_count == 1
    assert preview.books[0].reference_isbn is None
