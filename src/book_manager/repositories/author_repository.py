"""著者と順序付き書籍関連の永続化。名前の一致で人物を統合しない。"""
from contextlib import contextmanager
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.author import Author
from book_manager.validators.author_name_normalizer import author_search_key


class AuthorRepository:
    def __init__(self, database_path: Path | str):
        self._database_path = Path(database_path)

    @contextmanager
    def transaction(self, connection=None, *, write=True):
        """共有接続では呼出元にcommit/rollbackを任せる。"""
        if connection is not None:
            if not connection.in_transaction:
                raise ValueError('共有接続はトランザクション内で使用してください。')
            yield connection
            return
        conn = create_connection(self._database_path)
        try:
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _read(self, query, parameters=(), connection=None):
        if connection is not None:
            return connection.execute(query, parameters).fetchall()
        conn = create_connection(self._database_path)
        try:
            conn.execute('BEGIN')
            return conn.execute(query, parameters).fetchall()
        finally:
            conn.rollback()
            conn.close()

    def list_authors(self, *, connection=None) -> list[Author]:
        """著者と別名を同じ読取スナップショットから取得する。"""
        if connection is None:
            conn = create_connection(self._database_path)
            try:
                conn.execute('BEGIN')
                return self.list_authors(connection=conn)
            finally:
                conn.rollback()
                conn.close()
        aliases = {}
        for row in self._read('SELECT author_id, name FROM author_aliases ORDER BY id', connection=connection):
            aliases.setdefault(row['author_id'], []).append(row['name'])
        return [Author(name=row['name'], id=row['id'],
                       aliases=tuple(aliases.get(row['id'], ())),
                       disambiguation_note=row['disambiguation_note'],
                       created_at=row['created_at'], updated_at=row['updated_at'])
                for row in self._read('SELECT * FROM authors ORDER BY id', connection=connection)]

    def get(self, author_id: int, *, connection=None) -> Author | None:
        return next((author for author in self.list_authors(connection=connection) if author.id == author_id), None)

    def save(self, author: Author, *, connection=None) -> Author:
        with self.transaction(connection) as conn:
            if author.id is None:
                cursor = conn.execute('INSERT INTO authors(name,name_key,disambiguation_note,created_at,updated_at) VALUES (?,?,?,?,?)',
                                      (author.name, author_search_key(author.name), author.disambiguation_note, author.created_at, author.updated_at))
                author_id = cursor.lastrowid
            else:
                cursor = conn.execute('UPDATE authors SET name=?,name_key=?,disambiguation_note=?,updated_at=? WHERE id=?',
                                      (author.name, author_search_key(author.name), author.disambiguation_note, author.updated_at, author.id))
                if cursor.rowcount != 1:
                    raise ValueError('著者が見つかりません。')
                author_id = author.id
                conn.execute('DELETE FROM author_aliases WHERE author_id=?', (author_id,))
            conn.executemany('INSERT INTO author_aliases(author_id,name,name_key) VALUES (?,?,?)',
                             [(author_id, name, author_search_key(name)) for name in author.aliases])
            return self.get(author_id, connection=conn)

    def linked_book_ids(self, author_id: int, *, connection=None) -> tuple[int, ...]:
        return tuple(row[0] for row in self._read('SELECT book_item_id FROM book_item_authors WHERE author_id=? ORDER BY book_item_id',
                                                 (author_id,), connection))

    def book_author_ids(self, book_id: int, *, connection=None) -> tuple[int, ...]:
        return tuple(row[0] for row in self._read('SELECT author_id FROM book_item_authors WHERE book_item_id=? ORDER BY position',
                                                 (book_id,), connection))

    def set_book_authors(self, book_id: int, author_ids: tuple[int, ...], *, connection=None) -> None:
        with self.transaction(connection) as conn:
            if conn.execute('SELECT id FROM book_items WHERE id=?', (book_id,)).fetchone() is None:
                raise ValueError('書籍が見つかりません。')
            for author_id in author_ids:
                if conn.execute('SELECT id FROM authors WHERE id=?', (author_id,)).fetchone() is None:
                    raise ValueError('著者が見つかりません。')
            conn.execute('DELETE FROM book_item_authors WHERE book_item_id=?', (book_id,))
            conn.executemany('INSERT INTO book_item_authors(book_item_id,author_id,position) VALUES (?,?,?)',
                             [(book_id, author_id, position) for position, author_id in enumerate(author_ids)])

    def delete(self, author_id: int) -> bool:
        with self.transaction() as conn:
            if self.linked_book_ids(author_id, connection=conn):
                raise ValueError('書籍に関連付けられた著者は削除できません。')
            return conn.execute('DELETE FROM authors WHERE id=?', (author_id,)).rowcount == 1

    def usage_counts(self) -> dict[int, int]:
        return {row[0]: row[1] for row in self._read(
            'SELECT author_id,COUNT(*) FROM book_item_authors GROUP BY author_id')}

    def unlinked_books(self):
        return [dict(row) for row in self._read(
            'SELECT id,title,author FROM book_items AS b '
            'WHERE NOT EXISTS (SELECT 1 FROM book_item_authors AS a '
            'WHERE a.book_item_id=b.id) ORDER BY b.id')]

    def link_unassigned_book(self, book_id, author_ids, *, expected_title, expected_author):
        """未関連・表示値を同一トランザクションで再確認する。"""
        with self.transaction() as conn:
            row = conn.execute('SELECT title,author FROM book_items WHERE id=?', (book_id,)).fetchone()
            if row is None or row['title'] != expected_title or row['author'] != expected_author:
                raise ValueError('書籍が変更または削除されました。一覧を更新して確認してください。')
            if self.book_author_ids(book_id, connection=conn):
                raise ValueError('既に管理著者が関連付けられています。一覧を更新してください。')
            self.set_book_authors(book_id, author_ids, connection=conn)
