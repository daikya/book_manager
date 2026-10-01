"""単一CSVの事前検査がDBを変更しないことを確認する。"""

import csv
from unittest.mock import Mock
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



def test_execute_creates_backup_before_registration(tmp_path: Path):
    _, repository, _, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, [{"タグ": "共通"}, {"書籍名": "二冊目"}]))
    backup = Mock()
    def create_backup():
        assert repository.get_all() == []
        path = tmp_path / "backup.db"
        path.write_bytes(b"test backup")
        return path
    backup.create_backup.side_effect = create_backup
    result = service.execute_preview(preview, backup_service=backup)
    assert result.imported_count == 2
    assert len(repository.get_all()) == 2
    assert result.backup_path == tmp_path / "backup.db"
    backup.create_backup.assert_called_once_with()


def test_execute_rejects_changed_csv(tmp_path: Path):
    database, _, _, service = make_service(tmp_path)
    path = write_csv(tmp_path, [{}])
    preview = service.preview_file(path)
    path.write_text(path.read_text(encoding="utf-8-sig") + "\n", encoding="utf-8-sig")
    backup = Mock()
    before = database.read_bytes()
    with pytest.raises(ValueError, match="再検査"):
        service.execute_preview(preview, backup_service=backup)
    backup.create_backup.assert_not_called()
    assert database.read_bytes() == before


def test_execute_rejects_new_duplicate(tmp_path: Path):
    _, repository, books, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, [{"ISBN": "9784065363706"}]))
    books.add_book(title="別の操作で登録", isbn="9784065363706")
    backup = Mock()
    with pytest.raises(ValueError, match="再検査"):
        service.execute_preview(preview, backup_service=backup)
    backup.create_backup.assert_not_called()
    assert len(repository.get_all()) == 1


def test_execute_backup_failure_does_not_register(tmp_path: Path):
    database, repository, _, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, [{}]))
    backup = Mock()
    backup.create_backup.side_effect = OSError("backup failed")
    before = database.read_bytes()
    with pytest.raises(OSError):
        service.execute_preview(preview, backup_service=backup)
    assert repository.get_all() == []
    assert database.read_bytes() == before


def test_execute_missing_backup_does_not_register(tmp_path: Path):
    _, repository, _, service = make_service(tmp_path)
    preview = service.preview_file(write_csv(tmp_path, [{}]))
    backup = Mock()
    backup.create_backup.return_value = None
    with pytest.raises(RuntimeError, match="バックアップ"):
        service.execute_preview(preview, backup_service=backup)
    assert repository.get_all() == []


def test_execute_detects_file_changed_during_backup(tmp_path: Path):
    _, repository, _, service = make_service(tmp_path)
    path = write_csv(tmp_path, [{}])
    preview = service.preview_file(path)
    backup = Mock()
    def create_backup():
        path.write_text("bad header\n", encoding="utf-8")
        saved = tmp_path / "backup.db"
        saved.write_bytes(b"test backup")
        return saved
    backup.create_backup.side_effect = create_backup
    with pytest.raises(ValueError):
        service.execute_preview(preview, backup_service=backup)
    assert repository.get_all() == []
