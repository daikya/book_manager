"""原著者名を保持し、未関連書籍だけを確認保存する。"""
from dataclasses import replace
import pytest
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    authors = AuthorService(AuthorRepository(path))
    books = BookService(BookRepository(path))
    a = authors.create(name='山田太郎', aliases=['山田 太郎'])
    b = authors.create(name='山田太郎', disambiguation_note='別人')
    book = books.add_book(title='原題', author='山田 太郎', tags=['保持'])
    return authors, books, a, b, book


def test_list_candidates_and_save_order_without_changing_book(setup):
    authors, books, a, b, book = setup
    assert authors.unlinked_books() == [{'id':book.id, 'title':'原題', 'author':'山田 太郎'}]
    assert {c.author.id for c in authors.search('山田 太郎')} == {a.id, b.id}
    authors.link_unassigned_book(book.id, [b.id, a.id], expected_title=book.title, expected_author=book.author)
    assert authors.unlinked_books() == []
    assert [x.id for x in authors.get_book_authors(book.id)] == [b.id, a.id]
    assert books.get_book(book.id) == book


def test_existing_links_are_never_replaced(setup):
    authors, books, a, b, book = setup
    authors.set_book_authors(book.id, [a.id])
    with pytest.raises(ValueError):
        authors.link_unassigned_book(book.id, [b.id], expected_title=book.title, expected_author=book.author)
    assert authors.get_book_authors(book.id) == [a]


@pytest.mark.parametrize('field,value', [('title','変更'), ('author','変更')])
def test_changed_book_is_rejected(setup, field, value):
    authors, books, a, b, book = setup
    books.update_book(replace(book, **{field:value}))
    with pytest.raises(ValueError):
        authors.link_unassigned_book(book.id, [a.id], expected_title=book.title, expected_author=book.author)
    assert authors.get_book_authors(book.id) == []


def test_deleted_author_rolls_back_all_links(setup):
    authors, books, a, b, book = setup
    authors.delete(b.id)
    with pytest.raises(ValueError):
        authors.link_unassigned_book(book.id, [a.id,b.id], expected_title=book.title, expected_author=book.author)
    assert authors.get_book_authors(book.id) == []


@pytest.mark.parametrize('ids', [[], [True], [0], [1,1], '1'])
def test_invalid_selection(setup, ids):
    authors, books, a, b, book = setup
    with pytest.raises((ValueError,TypeError)):
        authors.link_unassigned_book(book.id, ids, expected_title=book.title, expected_author=book.author)
    assert authors.get_book_authors(book.id) == []


def test_blank_original_author_is_supported(setup):
    authors, books, a, b, book = setup
    blank = books.add_book(title='著者空欄')
    authors.link_unassigned_book(blank.id,[a.id],expected_title=blank.title,expected_author=blank.author)
    assert books.get_book(blank.id).author == blank.author
