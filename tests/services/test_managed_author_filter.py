"""管理著者IDと既存条件を組み合わせた検索。"""
import pytest
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService


def test_identity_filter_and_combined_conditions(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    authors = AuthorService(AuthorRepository(path))
    books = BookService(BookRepository(path))
    first = authors.create(name='山田太郎', aliases=['山田 太郎'], disambiguation_note='経済学')
    second = authors.create(name='山田太郎', disambiguation_note='小説家')
    a = books.add_book(title='経済の本', author='別表記', tags=['研究'], author_ids=[first.id])
    b = books.add_book(title='共著', author_ids=[first.id, second.id])
    c = books.add_book(title='小説', author='山田太郎', author_ids=[second.id])
    books.add_book(title='未関連', author='山田太郎')
    assert {x.id for x in books.search_books(managed_author_id=first.id)} == {a.id, b.id}
    assert {x.id for x in books.search_books(managed_author_id=second.id)} == {b.id, c.id}
    assert [x.id for x in books.search_books(managed_author_id=first.id, tag_name='研究')] == [a.id]
    assert [x.id for x in books.search_books(managed_author_id=first.id, title='経済')] == [a.id]
    assert books.search_books(managed_author_id=first.id, author='山田太郎') == []
    assert books.search_books(managed_author_id=99999) == []
    assert len(books.search_books()) == 4
    authors.update(author_id=first.id, name='山田 太郎', aliases=['山田太郎'])
    assert len(books.search_books(managed_author_id=first.id)) == 2


@pytest.mark.parametrize('value', [True, False, 0, -1, '1', 1.5])
def test_invalid_author_filter(value, tmp_path):
    service = BookService(BookRepository(tmp_path / 'unused.db'))
    with pytest.raises(ValueError):
        service.search_books(managed_author_id=value)
