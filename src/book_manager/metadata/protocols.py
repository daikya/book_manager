"""外部書誌情報取得Clientの共通Protocol。"""

from typing import Protocol

from book_manager.models.book_search_candidate import BookSearchCandidate

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


class BookCandidateSearchClient(Protocol):
    """書籍名・著者名・出版社から候補を検索するClientのインターフェース。"""

    def search_candidates(
        self,
        *,
        title: str = "",
        author: str = "",
        publisher: str = "",
        max_results: int = 20,
        start_index: int = 0,
    ) -> list[BookSearchCandidate]:
        """未確認の候補を返す。候補なしは空リストとする。"""
        ...

    def fetch_candidate(self, candidate: BookSearchCandidate, *, isbn: str = "") -> FetchedBookData:
        """候補のIDから詳細情報を取得する。"""
        ...
