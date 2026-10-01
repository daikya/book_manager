"""単一CSV取込に使用する入力検証と一括登録の土台を検証する。"""

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.book_service import BookService


def make_book(**values: object) -> BookItem:
    return BookItem(
        created_at="2026-10-01 00:00:00",
        updated_at="2026-10-01 00:00:00",
        **values,
    )


def make_repository(tmp_path: Path) -> tuple[Path, BookRepository]:
    path = tmp_path / "books.db"
    initialize_database(path)
    return path, BookRepository(path)


def test_prepare_book_validates_without_writing() -> None:
    repository = Mock(spec=BookRepository)
    service = BookService(repository, now_provider=lambda: datetime(2026, 10, 1))
    book = service.prepare_book(title="  書籍  ", tags=("タグ", "タグ"))
    assert book.title == "書籍"
    assert book.tags == ("タグ",)
    assert book.id is None
    assert book.created_at == "2026-10-01 00:00:00"
    repository.add.assert_not_called()
    repository.add_many.assert_not_called()


def test_prepare_book_rejects_invalid_input_without_writing() -> None:
    repository = Mock(spec=BookRepository)
    service = BookService(repository)
    with pytest.raises(ValueError):
        service.prepare_book(title=" ")
    repository.add.assert_not_called()
    repository.add_many.assert_not_called()


def test_add_many_registers_books_and_shared_tags(tmp_path: Path) -> None:
    path, repository = make_repository(tmp_path)
    books = repository.add_many((
        make_book(title="一冊目", tags=("共通",)),
        make_book(title="二冊目", tags=("共通", "二冊目のみ")),
    ))
    assert len(books) == 2
    assert books[0].id != books[1].id
    assert all(book.id is not None for book in books)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM book_items").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM book_item_tags").fetchone()[0] == 3
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_add_many_rolls_back_books_tags_and_links(tmp_path: Path) -> None:
    path, repository = make_repository(tmp_path)
    original = repository.add(make_book(title="既存", tags=("既存タグ",)))
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TRIGGER reject_test_tag BEFORE INSERT ON tags
            WHEN NEW.name = '失敗タグ'
            BEGIN SELECT RAISE(ABORT, 'test failure'); END
        """)
    with pytest.raises(sqlite3.IntegrityError):
        repository.add_many((
            make_book(title="取込一冊目", tags=("新規タグ",)),
            make_book(title="取込二冊目", tags=("失敗タグ",)),
        ))
    assert repository.get_all() == [original]
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT name FROM tags").fetchall() == [("既存タグ",)]
        assert connection.execute("SELECT COUNT(*) FROM book_item_tags").fetchone()[0] == 1
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]


def test_add_many_empty_does_not_create_database(tmp_path: Path) -> None:
    path = tmp_path / "missing.db"
    assert BookRepository(path).add_many(()) == ()
    assert not path.exists()


def test_add_books_delegates_to_atomic_repository() -> None:
    repository = Mock(spec=BookRepository)
    service = BookService(repository)
    books = (make_book(title="書籍"),)
    repository.add_many.return_value = books
    assert service.add_books(books) == books
    repository.add_many.assert_called_once_with(books)
