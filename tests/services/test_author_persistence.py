"""著者・関連付けの永続化とトランザクション、原表記保持。"""
import sqlite3
from datetime import datetime
from dataclasses import replace
import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.services.author_service import AuthorService


@pytest.fixture
def setup_authors(tmp_path):
    path = tmp_path / 'books.db'
    initialize_database(path)
    with create_connection(path) as conn:
        conn.execute("INSERT INTO book_items(id,title,author,created_at,updated_at) VALUES (5,'本','元の 著者名','2026-10-01 00:00:00','2026-10-01 00:00:00')")
    repo = AuthorRepository(path)
    return path, repo, AuthorService(repo, now_provider=lambda: datetime(2026, 10, 22, 10, 0, 0))


def test_create_same_name_and_alias_for_distinct_people(setup_authors):
    path, repo, service = setup_authors
    first = service.create(name=' 山田太郎 ', aliases=[' 山田 太郎 ', '山田 太郎'], disambiguation_note=' 経済学 ')
    second = service.create(name='山田太郎', aliases=['山田 太郎'], disambiguation_note='小説家')
    assert first.id != second.id
    assert first.aliases == ('山田 太郎',)
    assert first.disambiguation_note == '経済学'
    assert [item.author.id for item in service.search('山田　太郎')] == [first.id, second.id]
    assert AuthorService(AuthorRepository(path)).get(first.id) == first


def test_update_preserves_identity_created_at_and_original_book_text(setup_authors):
    path, repo, service = setup_authors
    first = service.create(name='山田太郎', aliases=['別名'])
    service.set_book_authors(5, [first.id])
    edited = service.update(author_id=first.id, name='山田 太郎', aliases=['新別名'], disambiguation_note='識別')
    assert edited.id == first.id and edited.created_at == first.created_at
    assert edited.aliases == ('新別名',)
    assert service.get_book_authors(5) == [edited]
    with create_connection(path) as conn:
        assert conn.execute('SELECT author FROM book_items WHERE id=5').fetchone()[0] == '元の 著者名'


def test_order_replace_and_unlink_do_not_delete_people(setup_authors):
    path, repo, service = setup_authors
    first = service.create(name='甲'); second = service.create(name='乙')
    service.set_book_authors(5, [second.id, first.id])
    assert [a.id for a in service.get_book_authors(5)] == [second.id, first.id]
    assert service.linked_book_ids(first.id) == (5,)
    service.set_book_authors(5, [])
    assert service.get_book_authors(5) == []
    assert len(service.list_authors()) == 2


def test_delete_linked_author_refused_and_book_delete_cascades_links(setup_authors):
    path, repo, service = setup_authors
    first = service.create(name='著者', aliases=['別名'])
    service.set_book_authors(5, [first.id])
    with pytest.raises(ValueError): service.delete(first.id)
    with create_connection(path) as conn: conn.execute('DELETE FROM book_items WHERE id=5')
    assert service.linked_book_ids(first.id) == ()
    assert service.get(first.id) is not None
    assert service.delete(first.id)
    assert not service.delete(first.id)
    with create_connection(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM author_aliases').fetchone()[0] == 0


@pytest.mark.parametrize('ids', [[9999], [True], [0], [-1], ['1'], [1, 1], '1'])
def test_invalid_link_update_preserves_existing_relations(setup_authors, ids):
    path, repo, service = setup_authors
    author = service.create(name='著者'); service.set_book_authors(5, [author.id])
    with pytest.raises((ValueError, TypeError)): service.set_book_authors(5, ids)
    assert service.get_book_authors(5) == [author]


def test_missing_book_or_author_does_not_write(setup_authors):
    path, repo, service = setup_authors
    with pytest.raises(ValueError): service.set_book_authors(999, [])
    with pytest.raises(ValueError): service.update(author_id=999, name='存在しない')
    assert service.list_authors() == []


def test_shared_transaction_rolls_back_book_and_author_links_together(setup_authors):
    path, repo, service = setup_authors
    with pytest.raises(RuntimeError):
        with repo.transaction() as conn:
            conn.execute("UPDATE book_items SET title='変更' WHERE id=5")
            author = service.create(name='著者', connection=conn)
            service.set_book_authors(5, [author.id], connection=conn)
            raise RuntimeError('simulate failure')
    assert service.list_authors() == []
    with create_connection(path) as conn:
        assert conn.execute('SELECT title FROM book_items WHERE id=5').fetchone()[0] == '本'


def test_alias_failure_rolls_back_edit(setup_authors):
    path, repo, service = setup_authors
    author = service.create(name='著者', aliases=['元別名'])
    with pytest.raises(sqlite3.IntegrityError):
        repo.save(replace(author, name='変更', aliases=('重複', '重複')))
    assert service.get(author.id) == author


def test_shared_connection_requires_active_transaction(setup_authors):
    path, repo, service = setup_authors
    with create_connection(path) as conn:
        with pytest.raises(ValueError): service.create(name='著者', connection=conn)
    assert service.list_authors() == []


def test_raw_database_foreign_key_protects_linked_author(setup_authors):
    path,repo,service=setup_authors
    author=service.create(name='著者');service.set_book_authors(5,[author.id])
    with create_connection(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):conn.execute('DELETE FROM authors WHERE id=?',(author.id,))
    assert service.get_book_authors(5)==[author]
