"""Application service for book management."""

from collections.abc import Callable
from datetime import datetime

from book_manager.models.book_item import BookItem
from book_manager.repositories.book_repository import BookRepository
from book_manager.validators.completion_month_validator import (
    validate_completion_month,
)
from book_manager.validators.isbn_validator import validate_isbn
from book_manager.validators.magazine_code_validator import (
    validate_magazine_code,
)


class BookService:
    """書籍管理に関するアプリケーションロジックを担当する。"""

    def __init__(
        self,
        repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        """BookServiceを初期化する。

        Args:
            repository: 書籍情報の永続化を担当するRepository。
            now_provider: 現在日時を返す関数。
        """
        self._repository = repository
        self._now_provider = now_provider

    def add_book(
        self,
        *,
        title: str,
        isbn: str | None = None,
        magazine_code: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        publication_format: str | None = None,
        description: str | None = None,
        completion_month: str | None = None,
        notes: str | None = None,
    ) -> BookItem:
        """書籍情報を登録する。

        Args:
            title: 書籍名。
            isbn: ISBN。
            magazine_code: 雑誌コード。
            author: 著者名。
            publisher: 出版社名。
            publication_format: 出版形態。
            description: 内容紹介。
            completion_month: 読了年月。
            notes: 備考。

        Returns:
            登録後のBookItem。

        Raises:
            ValueError: 入力値が正しくない場合。
        """
        normalized_title = self._normalize_title(title)
        normalized_isbn = self._normalize_isbn(isbn)
        normalized_magazine_code = (
            self._normalize_optional_text(
                magazine_code
            )
        )
        normalized_author = self._normalize_optional_text(
            author
        )
        normalized_publisher = (
            self._normalize_optional_text(
                publisher
            )
        )
        normalized_publication_format = (
            self._normalize_optional_text(
                publication_format
            )
        )
        normalized_description = (
            self._normalize_optional_text(
                description
            )
        )
        normalized_completion_month = (
            self._normalize_optional_text(
                completion_month
            )
        )
        normalized_notes = self._normalize_optional_text(
            notes
        )

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=normalized_completion_month,
        )

        current_timestamp = self._current_timestamp()

        book_item = BookItem(
            title=normalized_title,
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            author=normalized_author,
            publisher=normalized_publisher,
            publication_format=(
                normalized_publication_format
            ),
            description=normalized_description,
            completion_month=normalized_completion_month,
            notes=normalized_notes,
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )

        return self._repository.add(book_item)

    def find_duplicate_candidates(
        self,
        *,
        isbn: str | None = None,
        magazine_code: str | None = None,
    ) -> list[BookItem]:
        """ISBNまたは雑誌コードが一致する重複候補を取得する。

        Args:
            isbn: ISBN。
            magazine_code: 雑誌コード。

        Returns:
            ID降順で重複排除したBookItemのリスト。

        Raises:
            ValueError: 入力値が正しくない場合。
        """
        normalized_isbn = self._normalize_isbn(isbn)
        normalized_magazine_code = (
            self._normalize_optional_text(
                magazine_code
            )
        )

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=None,
        )

        candidates: list[BookItem] = []

        if normalized_isbn is not None:
            candidates.extend(
                self._repository.find_by_isbn(
                    normalized_isbn
                )
            )

        if normalized_magazine_code is not None:
            candidates.extend(
                self._repository.find_by_magazine_code(
                    normalized_magazine_code
                )
            )

        candidates_by_id: dict[int, BookItem] = {}

        for candidate in candidates:
            if candidate.id is None:
                continue

            candidates_by_id[candidate.id] = candidate

        return sorted(
            candidates_by_id.values(),
            key=lambda book_item: book_item.id or 0,
            reverse=True,
        )

    def get_book(
        self,
        book_id: int,
    ) -> BookItem | None:
        """IDを指定して書籍情報を取得する。"""
        return self._repository.get_by_id(book_id)

    def get_all_books(self) -> list[BookItem]:
        """すべての書籍情報を取得する。"""
        return self._repository.get_all()

    def search_books_by_title(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """書籍名による部分一致検索を行う。"""
        normalized_keyword = keyword.strip()

        if normalized_keyword == "":
            return self._repository.get_all()

        return self._repository.search_by_title(
            normalized_keyword
        )

    def find_books_by_isbn(
        self,
        isbn: str,
    ) -> list[BookItem]:
        """ISBNによる完全一致検索を行う。"""
        normalized_isbn = self._normalize_isbn(isbn)

        if normalized_isbn is None:
            return []

        validate_isbn(normalized_isbn)

        return self._repository.find_by_isbn(
            normalized_isbn
        )

    def find_books_by_magazine_code(
        self,
        magazine_code: str,
    ) -> list[BookItem]:
        """雑誌コードによる完全一致検索を行う。"""
        normalized_magazine_code = (
            self._normalize_optional_text(
                magazine_code
            )
        )

        if normalized_magazine_code is None:
            return []

        validate_magazine_code(
            normalized_magazine_code
        )

        return self._repository.find_by_magazine_code(
            normalized_magazine_code
        )

    def update_book(
        self,
        book_item: BookItem,
    ) -> bool:
        """既存の書籍情報を更新する。

        Args:
            book_item: 更新内容を持つBookItem。

        Returns:
            更新できた場合はTrue、対象が存在しない場合はFalse。

        Raises:
            ValueError: IDがない場合、または入力値が正しくない場合。
        """
        if book_item.id is None:
            raise ValueError(
                "更新対象のBookItemにはidが必要です。"
            )

        existing = self._repository.get_by_id(
            book_item.id
        )

        if existing is None:
            return False

        normalized_title = self._normalize_title(
            book_item.title
        )
        normalized_isbn = self._normalize_isbn(
            book_item.isbn
        )
        normalized_magazine_code = (
            self._normalize_optional_text(
                book_item.magazine_code
            )
        )
        normalized_author = self._normalize_optional_text(
            book_item.author
        )
        normalized_publisher = (
            self._normalize_optional_text(
                book_item.publisher
            )
        )
        normalized_publication_format = (
            self._normalize_optional_text(
                book_item.publication_format
            )
        )
        normalized_description = (
            self._normalize_optional_text(
                book_item.description
            )
        )
        normalized_completion_month = (
            self._normalize_optional_text(
                book_item.completion_month
            )
        )
        normalized_notes = self._normalize_optional_text(
            book_item.notes
        )

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=normalized_completion_month,
        )

        normalized_book_item = BookItem(
            id=book_item.id,
            title=normalized_title,
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            author=normalized_author,
            publisher=normalized_publisher,
            publication_format=(
                normalized_publication_format
            ),
            description=normalized_description,
            completion_month=normalized_completion_month,
            notes=normalized_notes,
            created_at=existing.created_at,
            updated_at=self._current_timestamp(),
        )

        return self._repository.update(
            normalized_book_item
        )

    def delete_book(
        self,
        book_id: int,
    ) -> bool:
        """IDを指定して書籍情報を削除する。"""
        return self._repository.delete(book_id)

    @staticmethod
    def _normalize_title(title: str) -> str:
        """書籍名を正規化する。"""
        normalized_title = title.strip()

        if normalized_title == "":
            raise ValueError(
                "書籍名を入力してください。"
            )

        return normalized_title

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        """任意入力の文字列を正規化する。"""
        if value is None:
            return None

        normalized_value = value.strip()

        if normalized_value == "":
            return None

        return normalized_value

    @staticmethod
    def _normalize_isbn(
        isbn: str | None,
    ) -> str | None:
        """ISBNを正規化する。"""
        if isbn is None:
            return None

        normalized_isbn = isbn.strip()
        normalized_isbn = normalized_isbn.replace(
            "-",
            "",
        )
        normalized_isbn = normalized_isbn.replace(
            " ",
            "",
        )

        if normalized_isbn == "":
            return None

        return normalized_isbn

    def _current_timestamp(self) -> str:
        """現在日時を保存用文字列として取得する。"""
        return self._now_provider().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @staticmethod
    def _validate_optional_values(
        *,
        isbn: str | None,
        magazine_code: str | None,
        completion_month: str | None,
    ) -> None:
        """正規化済みの任意入力値を検証する。"""
        if isbn is not None:
            validate_isbn(isbn)

        if magazine_code is not None:
            validate_magazine_code(
                magazine_code
            )

        if completion_month is not None:
            validate_completion_month(
                completion_month
            )