"""Google Books API client."""

from __future__ import annotations

from typing import Any

import requests
from requests import Session

from book_manager.metadata.exceptions import (
    BookMetadataConnectionError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
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

class GoogleBooksClient:
    """Google Books APIとの通信を担当するClient。"""

    BASE_URL = (
        "https://www.googleapis.com/books/v1/volumes"
    )

    def __init__(
        self,
        session: Session,
        api_key: str | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        """Clientを初期化する。"""
        self._session = session
        self._api_key = api_key
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        return "Google Books"

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """ISBNに対応する書誌情報を取得する。

        現段階ではHTTP通信とJSON取得までを担当する。
        書誌情報への変換は次工程で実装する。

        Args:
            isbn:
                検証済みの問い合わせ用ISBN-13。

        Returns:
            対象が見つからない場合はNone。

        Raises:
            BookMetadataConnectionError:
                Google Booksへ接続できない場合。
            BookMetadataRateLimitError:
                APIの利用制限に達した場合。
            BookMetadataResponseError:
                HTTP応答またはJSON形式が不正な場合。
        """
        payload = self._request_json(isbn)

        total_items = payload.get("totalItems")

        if total_items == 0:
            return None

        items = payload.get("items")

        if items is None:
            return None

        if not isinstance(items, list):
            raise BookMetadataResponseError(
                "Google Booksのitemsが"
                "配列ではありません。"
            )

        if not items:
            return None

        matching_item = self._find_matching_item(
            items=items,
            query_isbn=isbn,
        )

        if matching_item is None:
            return None

        return self._create_fetched_book_data(
            item=matching_item,
            isbn=isbn,
            payload=payload,
        )

    def _build_params(
        self,
        isbn: str,
    ) -> dict[str, str | int]:
        """Google Books APIの検索パラメータを生成する。"""
        params: dict[str, str | int] = {
            "q": f"isbn:{isbn}",
            "maxResults": 10,
        }

        if self._api_key:
            params["key"] = self._api_key

        return params

    def _request_json(
        self,
        isbn: str,
    ) -> dict[str, Any]:
        """Google Books APIへ接続してJSONを取得する。"""
        try:
            response = self._session.get(
                self.BASE_URL,
                params=self._build_params(isbn),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise BookMetadataConnectionError(
                "Google Booksへ接続できませんでした。"
            ) from exc

        if response.status_code == 429:
            raise BookMetadataRateLimitError(
                "Google Booksの利用制限に達しました。"
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise BookMetadataResponseError(
                "Google Booksから正常な応答を"
                "取得できませんでした。"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BookMetadataResponseError(
                "Google Booksの応答を"
                "解析できませんでした。"
            ) from exc

        if not isinstance(payload, dict):
            raise BookMetadataResponseError(
                "Google Booksの応答形式が"
                "正しくありません。"
            )

        return payload


    def _find_matching_item(
        self,
        *,
        items: list[object],
        query_isbn: str,
    ) -> dict[str, Any] | None:
        """問い合わせISBNに一致する候補を返す。"""
        for item in items:
            if not isinstance(item, dict):
                continue

            volume_info = item.get("volumeInfo")

            if not isinstance(volume_info, dict):
                continue

            identifiers = volume_info.get(
                "industryIdentifiers"
            )

            if not isinstance(identifiers, list):
                continue

            if self._contains_matching_isbn(
                identifiers=identifiers,
                query_isbn=query_isbn,
            ):
                return item

        return None

    def _contains_matching_isbn(
        self,
        *,
        identifiers: list[object],
        query_isbn: str,
    ) -> bool:
        """識別子一覧に問い合わせISBNが含まれるか確認する。"""
        for identifier_data in identifiers:
            if not isinstance(identifier_data, dict):
                continue

            identifier_type = identifier_data.get(
                "type"
            )
            identifier = identifier_data.get(
                "identifier"
            )

            if identifier_type not in {
                "ISBN_10",
                "ISBN_13",
            }:
                continue

            if not isinstance(identifier, str):
                continue

            try:
                normalized = normalize_isbn(
                    identifier
                )
                candidate_isbn13 = to_isbn13(
                    normalized
                )
            except (TypeError, ValueError):
                continue

            if candidate_isbn13 == query_isbn:
                return True

        return False

    def _create_fetched_book_data(
        self,
        *,
        item: dict[str, Any],
        isbn: str,
        payload: dict[str, Any],
    ) -> FetchedBookData:
        """Google Booksの候補を書誌情報モデルへ変換する。"""
        volume_info = item.get("volumeInfo")

        if not isinstance(volume_info, dict):
            raise BookMetadataResponseError(
                "Google BooksのvolumeInfoが"
                "正しくありません。"
            )

        return FetchedBookData(
            isbn=isbn,
            title=self._normalize_optional_text(
                volume_info.get("title")
            ),
            author=self._extract_authors(
                volume_info.get("authors")
            ),
            publisher=self._normalize_optional_text(
                volume_info.get("publisher")
            ),
            publication_date=(
                self._normalize_optional_text(
                    volume_info.get("publishedDate")
                )
            ),
            publication_format=None,
            description=self._normalize_optional_text(
                volume_info.get("description")
            ),
            cover_image_url=self._extract_cover_image_url(
                volume_info.get("imageLinks")
            ),
            sources=(self.source_name,),
            raw_data={
                self.source_name: {
                    "query": {
                        "isbn": isbn,
                    },
                    "response": payload,
                },
            },
        )

    @staticmethod
    def _normalize_optional_text(
        value: object,
    ) -> str | None:
        """任意の文字列値を正規化する。"""
        if not isinstance(value, str):
            return None

        normalized = value.strip()

        return normalized or None

    def _extract_authors(
        self,
        value: object,
    ) -> str | None:
        """著者配列を表示用文字列へ変換する。"""
        if not isinstance(value, list):
            return None

        authors = [
            normalized
            for author in value
            if (
                normalized
                := self._normalize_optional_text(
                    author
                )
            )
            is not None
        ]

        if not authors:
            return None

        return "、".join(authors)

    def _extract_cover_image_url(
        self,
        value: object,
    ) -> str | None:
        """利用可能な表紙画像URLを取得する。"""
        if not isinstance(value, dict):
            return None

        priority_keys = (
            "extraLarge",
            "large",
            "medium",
            "small",
            "thumbnail",
            "smallThumbnail",
        )

        for key in priority_keys:
            url = self._normalize_optional_text(
                value.get(key)
            )

            if url is not None:
                return url

        return None