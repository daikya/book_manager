"""同名を許可する著者の登録・編集・検索・関連付け。"""
from datetime import datetime

from book_manager.models.author import Author
from book_manager.repositories.author_repository import AuthorRepository
from book_manager.services.author_matching import find_author_candidates


class AuthorService:
    def __init__(self, repository: AuthorRepository, *, now_provider=datetime.now):
        self._repository = repository
        self._now = now_provider

    @staticmethod
    def _id(value):
        if type(value) is not int or value < 1:
            raise ValueError('IDは1以上の整数で指定してください。')
        return value

    @staticmethod
    def _fields(name, aliases, note):
        if not isinstance(aliases, (tuple, list)):
            raise TypeError('別名はタプルまたはリストで指定してください。')
        # Validate raw values before trimming; invalid controls must not disappear.
        Author(name, aliases=tuple(aliases), disambiguation_note=note)
        name = name.strip()
        aliases = tuple(dict.fromkeys(value.strip() for value in aliases if value.strip() != name))
        note = note.strip() or None if note is not None else None
        return name, aliases, note

    def list_authors(self):
        return self._repository.list_authors()

    def get(self, author_id):
        return self._repository.get(self._id(author_id))

    def create(self, *, name, aliases=(), disambiguation_note=None, connection=None):
        name, aliases, note = self._fields(name, aliases, disambiguation_note)
        now = self._now().strftime('%Y-%m-%d %H:%M:%S')
        return self._repository.save(Author(name, aliases=aliases, disambiguation_note=note,
                                            created_at=now, updated_at=now), connection=connection)

    def update(self, *, author_id, name, aliases=(), disambiguation_note=None, connection=None):
        author_id = self._id(author_id)
        name, aliases, note = self._fields(name, aliases, disambiguation_note)
        now = self._now().strftime('%Y-%m-%d %H:%M:%S')
        return self._repository.save(Author(name, id=author_id, aliases=aliases,
                                            disambiguation_note=note, updated_at=now), connection=connection)

    def search(self, query):
        return find_author_candidates(self.list_authors(), query)

    def set_book_authors(self, book_id, author_ids, *, connection=None):
        book_id = self._id(book_id)
        if not isinstance(author_ids, (tuple, list)):
            raise TypeError('著者IDはタプルまたはリストで指定してください。')
        ids = tuple(self._id(value) for value in author_ids)
        if len(ids) != len(set(ids)):
            raise ValueError('同じ著者を重複して指定できません。')
        self._repository.set_book_authors(book_id, ids, connection=connection)

    def get_book_authors(self, book_id):
        book_id = self._id(book_id)
        with self._repository.transaction(write=False) as conn:
            ids = self._repository.book_author_ids(book_id, connection=conn)
            by_id = {author.id: author for author in self._repository.list_authors(connection=conn)}
            return [by_id[author_id] for author_id in ids]

    def linked_book_ids(self, author_id):
        return self._repository.linked_book_ids(self._id(author_id))

    def delete(self, author_id):
        return self._repository.delete(self._id(author_id))

    def usage_counts(self) -> dict[int, int]:
        return self._repository.usage_counts()

    def unlinked_books(self):
        return self._repository.unlinked_books()

    def link_unassigned_book(self, book_id, author_ids, *, expected_title, expected_author):
        book_id = self._id(book_id)
        if not isinstance(author_ids, (tuple, list)):
            raise TypeError('著者IDはタプルまたはリストで指定してください。')
        ids = tuple(self._id(value) for value in author_ids)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('管理著者を重複なく1人以上選択してください。')
        self._repository.link_unassigned_book(book_id, ids,
            expected_title=expected_title, expected_author=expected_author)
