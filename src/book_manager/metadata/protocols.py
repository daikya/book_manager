"""外部書誌情報取得Clientの共通Protocol。"""

from typing import Protocol

from book_manager.models.fetched_book_data import FetchedBookData


class BookMetadataClient(Protocol):
    """外部書誌情報取得Clientの共通インターフェース。"""

    @property
    def source_name(self) -> str:
        """取得元の名称を返す。"""
        ...

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """ISBNに対応する書誌情報を取得する。

        Args:
            isbn:
                検証済みの問い合わせ用ISBN-13。

        Returns:
            書誌情報を取得できた場合はFetchedBookData。
            対象書籍が見つからない場合はNone。
        """
        ...