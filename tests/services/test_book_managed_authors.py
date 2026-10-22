"""書籍・タグ・管理著者を同一トランザクションで保存する。"""
from dataclasses import replace
from unittest.mock import patch
import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.author_service import AuthorService
from book_manager.services.book_service import BookService


@pytest.fixture
def services(tmp_path):
    path=tmp_path/'books.db';initialize_database(path)
    authors=AuthorService(AuthorRepository(path));books=BookService(BookRepository(path))
    first=authors.create(name='山田太郎',disambiguation_note='経済学')
    second=authors.create(name='山田太郎',disambiguation_note='小説家')
    return path,books,authors,first,second


def test_register_book_tags_and_same_name_people_in_order(services):
    path,books,authors,first,second=services
    book=books.add_book(title='本',author='山田 太郎',tags=['タグ'],author_ids=[second.id,first.id])
    assert [a.id for a in authors.get_book_authors(book.id)]==[second.id,first.id]
    assert books.get_book(book.id).author=='山田 太郎'
    assert books.get_book(book.id).tags==('タグ',)
    assert authors.usage_counts()=={first.id:1,second.id:1}


def test_update_with_none_preserves_links_empty_clears_links(services):
    path,books,authors,first,second=services
    book=books.add_book(title='本',author_ids=[first.id])
    assert books.update_book(replace(book,title='変更',author='取得表記'))
    assert authors.get_book_authors(book.id)==[first]
    assert books.update_book(replace(book,title='変更'),author_ids=[])
    assert authors.get_book_authors(book.id)==[]
    assert len(authors.list_authors())==2


def test_missing_author_on_register_rolls_back_book_tags_and_links(services):
    path,books,authors,first,second=services
    with pytest.raises(ValueError):books.add_book(title='本',tags=['新タグ'],author_ids=[first.id,99999])
    assert books.get_all_books()==[] and books.get_all_tags()==[]
    assert authors.usage_counts()=={}


def test_missing_author_on_update_rolls_back_all_changes(services):
    path,books,authors,first,second=services
    book=books.add_book(title='元',author='原表記',tags=['元タグ'],author_ids=[first.id])
    with pytest.raises(ValueError):
        books.update_book(replace(book,title='変更',author='別表記',tags=('新タグ',)),author_ids=[second.id,99999])
    assert books.get_book(book.id)==book
    assert authors.get_book_authors(book.id)==[first]
    assert [t.name for t in books.get_all_tags()]==['元タグ']


@pytest.mark.parametrize('ids',[[True],[0],[-1],['1'],[1,1],'1'])
def test_invalid_ids_do_not_create_books(services,ids):
    path,books,authors,first,second=services
    with pytest.raises((TypeError,ValueError)):books.add_book(title='本',author_ids=ids)
    assert books.get_all_books()==[]


def test_failure_after_relation_insert_rolls_back(services):
    path,books,authors,first,second=services
    real=AuthorRepository.set_book_authors
    def failing(self,*args,**kwargs):
        real(self,*args,**kwargs)
        raise RuntimeError('simulate failure after linking')
    with patch.object(AuthorRepository,'set_book_authors',failing):
        with pytest.raises(RuntimeError):books.add_book(title='本',tags=['新タグ'],author_ids=[first.id])
    assert books.get_all_books()==[] and books.get_all_tags()==[]
    assert authors.usage_counts()=={}


def test_no_managed_author_argument_keeps_existing_registration_compatible(services):
    path,books,authors,first,second=services
    book=books.add_book(title='通常登録',author='原表記')
    assert authors.get_book_authors(book.id)==[]
    assert books.update_book(replace(book,title='通常更新'))
    assert books.get_book(book.id).title=='通常更新'
