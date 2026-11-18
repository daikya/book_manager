"""複数著者のOR・AND検索を実DBで検証する。"""
from dataclasses import replace
import pytest
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService


def test_multi_author_or_and_identity_and_combined_filters(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    repo = BookRepository(path)
    authors = AuthorService(AuthorRepository(path))
    books = BookService(repo)
    a = authors.create(name='山田太郎', disambiguation_note='経済学')
    b = authors.create(name='山田太郎', disambiguation_note='小説家')
    one = books.add_book(title='単著A', author_ids=(a.id,), reading_status='reading')
    both = books.add_book(title='共著AB', author_ids=(a.id, b.id), tags=('共著',), reading_status='reading')
    two = books.add_book(title='単著B', author_ids=(b.id,), reading_status='completed')
    books.add_book(title='同名未関連', author='山田太郎')
    ids = (a.id, b.id)
    def found(**kw):return {book.id for book in books.search_books(**kw)}
    assert found(managed_author_ids=ids) == {one.id, both.id, two.id}
    assert found(managed_author_ids=ids, managed_author_mode='all') == {both.id}
    assert found(managed_author_ids=ids, reading_status_filter='reading') == {one.id, both.id}
    assert found(managed_author_ids=ids, tag_name='共著') == {both.id}
    assert found(managed_author_ids=(a.id, a.id, b.id), managed_author_mode='all') == {both.id}
    assert found(managed_author_ids=(a.id,)) == {one.id, both.id}
    assert found(managed_author_id=a.id) == {one.id, both.id}
    assert found(managed_author_ids=()) == {book.id for book in repo.get_all()}
    assert found(managed_author_ids=(99999,), managed_author_mode='all') == set()
    assert found(managed_author_ids=(a.id, 99999), managed_author_mode='all') == set()
    assert found(managed_author_ids=(a.id, 99999)) == {one.id, both.id}
    # Repository直接利用でも同じ条件と重複なしの結果になる。
    assert {book.id for book in repo.search_by_conditions(managed_author_ids=ids)} == {one.id, both.id, two.id}
    assert [book.id for book in repo.search_by_conditions(managed_author_ids=ids, managed_author_mode='all')] == [both.id]
    authors.set_book_authors(both.id, (a.id,))
    assert found(managed_author_ids=ids, managed_author_mode='all') == set()
    assert found(managed_author_ids=ids) == {one.id, both.id, two.id}


@pytest.mark.parametrize('kwargs', [
    {'managed_author_ids': (True,)}, {'managed_author_ids': (0,)},
    {'managed_author_ids': (-1,)}, {'managed_author_ids': ('1',)},
    {'managed_author_ids': '1'}, {'managed_author_ids': None},
    {'managed_author_ids': (1.5,)}, {'managed_author_mode': 'invalid'},
    {'managed_author_id': 1, 'managed_author_ids': (2,)},
])
def test_invalid_conditions_rejected_by_service_and_repository(tmp_path, kwargs):
    repo = BookRepository(tmp_path / 'must_not_open.db')
    with pytest.raises(ValueError):BookService(repo).search_books(**kwargs)
    with pytest.raises(ValueError):repo.search_by_conditions(**kwargs)
