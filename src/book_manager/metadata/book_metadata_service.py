"""外部書誌情報取得Service。"""

from collections.abc import Iterable, Sequence
from typing import Any

from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
    BookMetadataConnectionError,
    BookMetadataError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)
from book_manager.metadata.protocols import (
    BookMetadataClient,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)
from book_manager.validators.isbn_converter import (
    to_isbn13,
)
from book_manager.validators.isbn_normalizer import (
    normalize_isbn,
)
from book_manager.validators.isbn_validator import (
    validate_isbn,
)


class BookMetadataService:
    """複数の外部書誌情報取得Clientを制御するService。"""

    def __init__(
        self,
        clients: Sequence[BookMetadataClient],
    ) -> None:
        """Serviceを初期化する。

        Args:
            clients:
                優先順位順に並べた書誌情報取得Client。

        Raises:
            BookMetadataConfigurationError:
                Clientが一つも指定されていない場合。
        """
        if not clients:
            raise BookMetadataConfigurationError(
                "書誌情報取得Clientが登録されていません。"
            )

        self._clients = tuple(clients)

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData:
        """ISBNから書誌情報を取得して統合する。

        Args:
            isbn:
                正規化前のISBN-10またはISBN-13。

        Returns:
            複数の取得結果を統合したFetchedBookData。

        Raises:
            TypeError:
                ISBNが文字列でない場合。
            ValueError:
                ISBNの形式またはチェックデジットが不正な場合。
            BookMetadataNotFoundError:
                すべてのClientで対象書籍が見つからない場合。
            BookMetadataError:
                有効な結果がなく、いずれかのClientで
                外部取得エラーが発生した場合。
        """
        normalized_isbn = normalize_isbn(isbn)
        validate_isbn(normalized_isbn)

        query_isbn13 = to_isbn13(
            normalized_isbn
        )

        results: list[FetchedBookData] = []
        errors: list[BookMetadataError] = []

        for client in self._clients:
            try:
                result = client.fetch_by_isbn(
                    query_isbn13
                )
            except BookMetadataError as exc:
                errors.append(exc)
                continue

            if result is not None:
                results.append(result)

        if results:
            return self._merge_results(
                input_isbn=normalized_isbn,
                results=results,
            )

        if errors:
            raise self._select_final_error(errors)

        raise BookMetadataNotFoundError(
            "該当する書誌情報が見つかりませんでした。"
        )

    def _merge_results(
        self,
        *,
        input_isbn: str,
        results: list[FetchedBookData],
    ) -> FetchedBookData:
        """取得結果を優先順位順に統合する。"""
        merged = FetchedBookData(
            isbn=input_isbn,
            title=self._first_text(
                result.title
                for result in results
            ),
            author=self._first_text(
                result.author
                for result in results
            ),
            publisher=self._first_text(
                result.publisher
                for result in results
            ),
            publication_date=self._first_text(
                result.publication_date
                for result in results
            ),
            publication_format=self._first_text(
                result.publication_format
                for result in results
            ),
            description=self._first_text(
                result.description
                for result in results
            ),
            cover_image_url=self._first_text(
                result.cover_image_url
                for result in results
            ),
            sources=self._merge_sources(results),
            raw_data=self._merge_raw_data(results),
        )

        if not self._has_useful_metadata(merged):
            raise BookMetadataNotFoundError(
                "該当する書誌情報が見つかりませんでした。"
            )

        return merged

    @staticmethod
    def _first_text(
        values: Iterable[str | None],
    ) -> str | None:
        """最初の有効な文字列を返す。"""
        for value in values:
            if value is None:
                continue

            normalized = value.strip()

            if normalized:
                return normalized

        return None

    @staticmethod
    def _merge_sources(
        results: list[FetchedBookData],
    ) -> tuple[str, ...]:
        """取得元を重複なく優先順位順に結合する。"""
        sources: list[str] = []

        for result in results:
            for source in result.sources:
                if source not in sources:
                    sources.append(source)

        return tuple(sources)

    @staticmethod
    def _merge_raw_data(
        results: list[FetchedBookData],
    ) -> dict[str, Any]:
        """取得元ごとのRawデータを結合する。"""
        merged: dict[str, Any] = {}

        for result in results:
            merged.update(result.raw_data)

        return merged

    @staticmethod
    def _has_useful_metadata(
        data: FetchedBookData,
    ) -> bool:
        """有効な書誌項目が一つ以上存在するか確認する。"""
        values = (
            data.title,
            data.author,
            data.publisher,
            data.publication_date,
            data.publication_format,
            data.description,
            data.cover_image_url,
        )

        return any(
            isinstance(value, str)
            and bool(value.strip())
            for value in values
        )

    @staticmethod
    def _select_final_error(
        errors: list[BookMetadataError],
    ) -> BookMetadataError:
        """複数エラーから利用者へ返す代表例外を選択する。"""
        priority = (
            BookMetadataRateLimitError,
            BookMetadataConnectionError,
            BookMetadataResponseError,
            BookMetadataConfigurationError,
            BookMetadataError,
        )

        for error_type in priority:
            for error in errors:
                if isinstance(error, error_type):
                    return error

        return errors[0]