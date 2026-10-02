"""Application service for book management."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from book_manager.models.book_item import BookItem
from book_manager.models.tag import Tag
from book_manager.repositories.book_repository import BookRepository
from book_manager.validators.completion_month_validator import (
    validate_completion_month,
)
from book_manager.validators.isbn_validator import validate_isbn
from book_manager.validators.magazine_code_validator import (
    validate_magazine_code,
)
from book_manager.metadata.book_metadata_service import (
    BookMetadataService,
)
from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)
from book_manager.services.cover_image_service import (
    CoverImageService,
)
from book_manager.validators.reading_status_validator import (
    validate_reading_status,
)
from book_manager.validators.rating_validator import (
    validate_rating,
)
from book_manager.validators.tag_validator import (
    validate_tag_name,
)


READING_STATUS_SORT_ORDER = {
    None: 0,
    "unread": 1,
    "reading": 2,
    "completed": 3,
}


class BookService:
    """書籍管理に関するアプリケーションロジックを担当する。"""
    def __init__(
        self,
        repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
        metadata_service: BookMetadataService | None = None,
        cover_image_service: CoverImageService | None = None,
    ) -> None:
        """BookServiceを初期化する。"""
        self._repository = repository
        self._now_provider = now_provider
        self._book_metadata_service = metadata_service
        self._cover_image_service = cover_image_service

    def add_book(
        self,
        *,
        title: str,
        isbn: str | None = None,
        reference_isbn: str | None = None,
        magazine_code: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        publication_format: str | None = None,
        description: str | None = None,
        cover_image_url: str | None = None,
        cover_image_path: str | None = None,
        completion_month: str | None = None,
        reading_status: str | None = None,
        is_favorite: bool = False,
        rating: int | None = None,
        notes: str | None = None,
        tags: tuple[str, ...] | list[str] = (),
    ) -> BookItem:
        """入力値を検証し、書籍情報を登録する。"""
        return self._repository.add(self.prepare_book(
            title=title,
            isbn=isbn,
            reference_isbn=reference_isbn,
            magazine_code=magazine_code,
            author=author,
            publisher=publisher,
            publication_format=publication_format,
            description=description,
            cover_image_url=cover_image_url,
            cover_image_path=cover_image_path,
            completion_month=completion_month,
            reading_status=reading_status,
            is_favorite=is_favorite,
            rating=rating,
            notes=notes,
            tags=tags,
        ))

    def prepare_book(
        self,
        *,
        title: str,
        isbn: str | None = None,
        reference_isbn: str | None = None,
        magazine_code: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        publication_format: str | None = None,
        description: str | None = None,
        cover_image_url: str | None = None,
        cover_image_path: str | None = None,
        completion_month: str | None = None,
        reading_status: str | None = None,
        is_favorite: bool = False,
        rating: int | None = None,
        notes: str | None = None,
        tags: tuple[str, ...] | list[str] = (),
    ) -> BookItem:
        """DBを変更せず、入力値を正規化・検証する。

        Args:
            title: 書籍名。
            isbn: ISBN。
            reference_isbn: 別媒体の書誌情報を参照するISBN。
            magazine_code: 雑誌コード。
            author: 著者名。
            publisher: 出版社名。
            publication_format: 出版形態。
            description: 内容紹介。
            cover_image_url: 表紙画像の取得元URL。
            cover_image_path: キャッシュ済み表紙画像の相対パス。
            completion_month: 読了年月。
            reading_status: 読書ステータス。
            is_favorite: お気に入り状態。
            rating: 評価。
            notes: 備考。
            tags: タグ名のタプルまたはリスト。

        Returns:
            登録後のBookItem。

        Raises:
            ValueError: 入力値が正しくない場合。
        """
        normalized_title = self._normalize_title(title)
        normalized_isbn = self._normalize_isbn(isbn)
        normalized_reference_isbn = self._normalize_reference_isbn(reference_isbn)
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
        normalized_cover_image_url = (
            self._normalize_optional_text(
                cover_image_url
            )
        )
        normalized_cover_image_path = (
            self._normalize_optional_text(
                cover_image_path
            )
        )
        normalized_completion_month = (
            self._normalize_optional_text(
                completion_month
            )
        )
        normalized_reading_status = (
            self._normalize_optional_text(
                reading_status
            )
        )
        normalized_notes = self._normalize_optional_text(
            notes
        )
        normalized_tags = self._normalize_tags(tags)

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=normalized_completion_month,
        )
        validate_reading_status(
            normalized_reading_status,
        )
        validate_rating(
            rating,
        )
        current_timestamp = self._current_timestamp()

        book_item = BookItem(
            title=normalized_title,
            isbn=normalized_isbn,
            reference_isbn=normalized_reference_isbn,
            magazine_code=normalized_magazine_code,
            author=normalized_author,
            publisher=normalized_publisher,
            publication_format=(
                normalized_publication_format
            ),
            description=normalized_description,
            cover_image_url=normalized_cover_image_url,
            cover_image_path=normalized_cover_image_path,
            completion_month=normalized_completion_month,
            reading_status=normalized_reading_status,
            is_favorite=is_favorite,
            rating=rating,
            notes=normalized_notes,
            created_at=current_timestamp,
            updated_at=current_timestamp,
            tags=normalized_tags,
        )

        return book_item

    def add_books(self, books: tuple[BookItem, ...]) -> tuple[BookItem, ...]:
        """検証済み書籍とタグを1トランザクションで登録する。"""
        return self._repository.add_many(books)

    def find_duplicate_candidates(
        self,
        *,
        title: str | None = None,
        isbn: str | None = None,
        magazine_code: str | None = None,
    ) -> list[BookItem]:
        """書籍名、ISBN、雑誌コードが一致する重複候補を取得する。

        Args:
            title: 書籍名。
            isbn: ISBN。
            magazine_code: 雑誌コード。

        Returns:
            ID降順で重複排除したBookItemのリスト。

        Raises:
            ValueError: 入力値が正しくない場合。
        """
        normalized_title = self._normalize_optional_text(
            title,
        )
        normalized_isbn = self._normalize_isbn(
            isbn,
        )
        normalized_magazine_code = (
            self._normalize_optional_text(
                magazine_code,
            )
        )

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=None,
        )

        candidates: list[BookItem] = []

        if normalized_title is not None:
            title_candidates = (
                self._repository.search_by_title(
                    normalized_title,
                )
            )

            candidates.extend(
                candidate
                for candidate in title_candidates
                if candidate.title.strip()
                == normalized_title
            )

        if normalized_isbn is not None:
            candidates.extend(
                self._repository.find_by_isbn(
                    normalized_isbn,
                )
            )

        if normalized_magazine_code is not None:
            candidates.extend(
                self._repository.find_by_magazine_code(
                    normalized_magazine_code,
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

    def get_sorted_books(
        self,
        *,
        sort_by: str,
        descending: bool = False,
    ) -> list[BookItem]:
        """指定された項目と方向で全書籍を取得する。"""
        allowed_sort_fields = {
            "registered",
            "title",
            "author",
            "publisher",
            "completion_month",
            "reading_status",
            "is_favorite",
            "rating",
        }

        if sort_by not in allowed_sort_fields:
            raise ValueError(
                "指定された並べ替え項目が正しくありません。"
            )

        return self._repository.get_all_sorted(
            sort_by=sort_by,
            descending=descending,
        )

    def sort_books(
        self,
        books: list[BookItem],
        *,
        sort_by: str,
        descending: bool = False,
    ) -> list[BookItem]:
        """取得済みの書籍一覧を指定された項目で並べ替える。"""
        sort_key_map = {
            "title": lambda book: book.title,
            "author": lambda book: book.author,
            "publisher": lambda book: book.publisher,
            "completion_month": lambda book: book.completion_month,
        }

        if sort_by == "registered":
            return sorted(
                books,
                key=lambda book: book.id or 0,
                reverse=descending,
            )

        reading_information_sort_key_map = {
            "reading_status": lambda book: (
                READING_STATUS_SORT_ORDER.get(
                    book.reading_status,
                    0,
                )
            ),
            "is_favorite": lambda book: int(
                book.is_favorite
            ),
            "rating": lambda book: book.rating or 0,
        }

        reading_information_key = (
            reading_information_sort_key_map.get(
                sort_by,
            )
        )

        if reading_information_key is not None:
            sorted_books = sorted(
                books,
                key=lambda book: book.id or 0,
                reverse=True,
            )
            sorted_books.sort(
                key=reading_information_key,
                reverse=descending,
            )

            return sorted_books

        key_function = sort_key_map.get(
            sort_by,
        )

        if key_function is None:
            raise ValueError(
                "指定された並べ替え項目が正しくありません。"
            )

        with_value = [
            book
            for book in books
            if key_function(book) is not None
        ]

        without_value = [
            book
            for book in books
            if key_function(book) is None
        ]

        # 同じ値の場合はID降順にする。
        with_value.sort(
            key=lambda book: -(book.id or 0),
        )

        with_value.sort(
            key=lambda book: str(
                key_function(book)
            ),
            reverse=descending,
        )

        return with_value + without_value

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

    def search_books_by_author(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """著者名による部分一致検索を行う。"""
        normalized_keyword = keyword.strip()

        if normalized_keyword == "":
            return self._repository.get_all()

        return self._repository.search_by_author(
            normalized_keyword,
        )

    def search_books_by_publisher(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """出版社名による部分一致検索を行う。"""
        normalized_keyword = keyword.strip()

        if normalized_keyword == "":
            return self._repository.get_all()

        return self._repository.search_by_publisher(
            normalized_keyword,
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

    def search_books(
        self,
        *,
        title: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        isbn: str | None = None,
        magazine_code: str | None = None,
        reading_status_filter: str | None = None,
        favorite_filter: str | None = None,
        rating_filter: str | int | None = None,
        tag_name: str | None = None,
        untagged_only: bool = False,
    ) -> list[BookItem]:
        """複数条件によるAND検索を行う。"""
        normalized_title = self._normalize_optional_text(
            title,
        )
        normalized_author = self._normalize_optional_text(
            author,
        )
        normalized_publisher = self._normalize_optional_text(
            publisher,
        )
        normalized_isbn = self._normalize_isbn(
            isbn,
        )
        normalized_magazine_code = (
            self._normalize_optional_text(
                magazine_code,
            )
        )
        normalized_tag_name = self._normalize_optional_text(
            tag_name,
        )

        if normalized_tag_name is not None:
            validate_tag_name(normalized_tag_name)

        if normalized_tag_name is not None and untagged_only:
            raise ValueError(
                "タグとタグ未設定を同時に指定できません。"
            )

        if normalized_isbn is not None:
            validate_isbn(
                normalized_isbn,
            )

        if normalized_magazine_code is not None:
            validate_magazine_code(
                normalized_magazine_code,
            )

        if (
            reading_status_filter is not None
            and reading_status_filter
            not in {
                "unset",
                "unread",
                "reading",
                "completed",
            }
        ):
            raise ValueError(
                "読書状態の検索条件が正しくありません。"
            )

        if (
            favorite_filter is not None
            and favorite_filter
            not in {
                "favorite",
                "not_favorite",
            }
        ):
            raise ValueError(
                "お気に入りの検索条件が正しくありません。"
            )

        if rating_filter is not None:
            if rating_filter == "unrated":
                pass
            elif (
                type(rating_filter) is int
                and 1 <= rating_filter <= 5
            ):
                pass
            else:
                raise ValueError(
                    "評価の検索条件が正しくありません。"
                )

        if (
            not untagged_only
            and all(
                value is None
                for value in (
                    normalized_title,
                    normalized_author,
                    normalized_publisher,
                    normalized_isbn,
                    normalized_magazine_code,
                    reading_status_filter,
                    favorite_filter,
                    rating_filter,
                    normalized_tag_name,
                )
            )
        ):
            return self._repository.get_all()

        return self._repository.search_by_conditions(
            title=normalized_title,
            author=normalized_author,
            publisher=normalized_publisher,
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            reading_status_filter=reading_status_filter,
            favorite_filter=favorite_filter,
            rating_filter=rating_filter,
            tag_name=normalized_tag_name,
            untagged_only=untagged_only,
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
        normalized_reference_isbn = self._normalize_reference_isbn(book_item.reference_isbn)
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
        normalized_cover_image_url = (
            self._normalize_optional_text(
                book_item.cover_image_url
            )
        )
        normalized_cover_image_path = (
            self._normalize_optional_text(
                book_item.cover_image_path
            )
        )
        normalized_completion_month = (
            self._normalize_optional_text(
                book_item.completion_month
            )
        )
        normalized_reading_status = (
            self._normalize_optional_text(
                book_item.reading_status
            )
        )
        normalized_notes = self._normalize_optional_text(
            book_item.notes
        )
        normalized_tags = self._normalize_tags(
            book_item.tags,
        )

        self._validate_optional_values(
            isbn=normalized_isbn,
            magazine_code=normalized_magazine_code,
            completion_month=normalized_completion_month,
        )
        validate_reading_status(
            normalized_reading_status,
        )
        validate_rating(
            book_item.rating,
        )
        normalized_book_item = BookItem(
            id=book_item.id,
            title=normalized_title,
            isbn=normalized_isbn,
            reference_isbn=normalized_reference_isbn,
            magazine_code=normalized_magazine_code,
            author=normalized_author,
            publisher=normalized_publisher,
            publication_format=(
                normalized_publication_format
            ),
            description=normalized_description,
            cover_image_url=normalized_cover_image_url,
            cover_image_path=normalized_cover_image_path,
            completion_month=normalized_completion_month,
            reading_status=normalized_reading_status,
            is_favorite=book_item.is_favorite,
            rating=book_item.rating,
            notes=normalized_notes,
            created_at=existing.created_at,
            updated_at=self._current_timestamp(),
            tags=normalized_tags,
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

    def get_all_tags(self) -> list[Tag]:
        """登録済みタグを名称の昇順で取得する。"""
        return self._repository.get_all_tags()

    def rename_tag(
        self,
        *,
        tag_id: int,
        name: str,
    ) -> bool:
        """登録済みタグの名称を変更する。"""
        existing = self._repository.get_tag_by_id(tag_id)

        if existing is None:
            return False

        if not isinstance(name, str):
            validate_tag_name(name)

        normalized_name = name.strip()
        validate_tag_name(normalized_name)

        if existing.name == normalized_name:
            return True

        duplicate = self._repository.get_tag_by_name(
            normalized_name,
        )

        if duplicate is not None:
            raise ValueError(
                "同じ名前のタグがすでに登録されています。"
            )

        return self._repository.rename_tag(
            tag_id=tag_id,
            name=normalized_name,
            updated_at=self._current_timestamp(),
        )

    def delete_tag(self, tag_id: int) -> bool:
        """IDを指定してタグを削除する。"""
        return self._repository.delete_tag(tag_id)

    def count_books_by_tag(self, tag_id: int) -> int:
        """指定したタグを使用している書籍数を返す。"""
        return self._repository.count_books_by_tag(tag_id)

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

    @classmethod
    def _normalize_tags(
        cls,
        tags: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        """タグ名を正規化、検証、重複排除して昇順で返す。"""
        if not isinstance(tags, (tuple, list)):
            raise ValueError(
                "タグはタプルまたはリストで指定してください。"
            )

        normalized_tags: list[str] = []

        for tag_name in tags:
            if not isinstance(tag_name, str):
                validate_tag_name(tag_name)

            normalized_tag_name = tag_name.strip()

            if normalized_tag_name == "":
                continue

            validate_tag_name(normalized_tag_name)

            if normalized_tag_name not in normalized_tags:
                normalized_tags.append(normalized_tag_name)

        return tuple(sorted(normalized_tags))

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

    @classmethod
    def _normalize_reference_isbn(cls, value: str | None) -> str | None:
        """参照ISBNを検証し、ISBN-10はISBN-13へ変換する。"""
        if value is not None and not isinstance(value, str):
            raise ValueError("参照ISBNは文字列で入力してください。")
        normalized = cls._normalize_isbn(value)
        if normalized is None:
            return None
        normalized = normalized.upper()
        if len(normalized) == 10:
            if not (
                all("0" <= c <= "9" for c in normalized[:9])
                and normalized[-1] in "0123456789X"
            ):
                raise ValueError("参照ISBNの形式が正しくありません。")
            digits = [int(c) for c in normalized[:9]] + [10 if normalized[-1] == "X" else int(normalized[-1])]
            if sum((10 - i) * digit for i, digit in enumerate(digits)) % 11:
                raise ValueError("参照ISBNのチェックデジットが正しくありません。")
            prefix = "978" + normalized[:9]
            check = (-sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(prefix))) % 10
            normalized = prefix + str(check)
        try:
            validate_isbn(normalized)
        except ValueError as error:
            raise ValueError(f"参照ISBN：{error}") from error
        return normalized

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

    def fetch_book_metadata(
        self,
        isbn: str,
    ) -> FetchedBookData:
        """ISBNから書誌情報を取得する。

        Args:
            isbn:
                正規化前のISBN-10またはISBN-13。

        Returns:
            外部サービスから取得・統合した書誌情報。

        Raises:
            BookMetadataConfigurationError:
                外部書誌情報取得Serviceが設定されていない場合。
        """
        if self._book_metadata_service is None:
            raise BookMetadataConfigurationError(
                "外部書誌情報取得Serviceが"
                "設定されていません。"
            )

        return self._book_metadata_service.fetch_by_isbn(
            isbn,
        )

    def fetch_cover_image(
        self,
        image_url: str,
    ) -> Path:
        """表紙画像を取得してキャッシュパスを返す。

        Args:
            image_url:
                表紙画像URL。

        Returns:
            キャッシュされた画像ファイルのパス。

        Raises:
            BookMetadataConfigurationError:
                表紙画像取得Serviceが設定されていない場合。
        """
        if self._cover_image_service is None:
            raise BookMetadataConfigurationError(
                "表紙画像取得Serviceが"
                "設定されていません。"
            )

        return self._cover_image_service.fetch(
            image_url,
        )

    def create_stored_cover_image_path(
        self,
        image_path: Path,
    ) -> str:
        """表紙画像パスをDB保存用の文字列へ変換する。"""
        cover_image_service = (
            self._require_cover_image_service()
        )

        return cover_image_service.create_stored_path(
            image_path,
        )

    def resolve_cover_image_path(
        self,
        stored_path: str | None,
    ) -> Path | None:
        """DBの表紙画像パスを表示用のPathへ解決する。"""
        cover_image_service = (
            self._require_cover_image_service()
        )

        return cover_image_service.resolve_stored_path(
            stored_path,
        )

    def _require_cover_image_service(
        self,
    ) -> CoverImageService:
        """設定済みの表紙画像取得Serviceを返す。"""
        if self._cover_image_service is None:
            raise BookMetadataConfigurationError(
                "表紙画像取得Serviceが"
                "設定されていません。"
            )

        return self._cover_image_service
