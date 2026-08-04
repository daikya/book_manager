"""openBD API client."""

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


class OpenBdClient:
    """openBD APIとの通信を担当するClient。"""

    BASE_URL = "https://api.openbd.jp/v1/get"

    def __init__(
        self,
        session: Session,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        """Clientを初期化する。"""
        self._session = session
        self._timeout = timeout

    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        return "openBD"

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

        Raises:
            BookMetadataConnectionError:
                openBDへ接続できない場合。
            BookMetadataRateLimitError:
                APIの利用制限に達した場合。
            BookMetadataResponseError:
                HTTP応答またはJSON形式が不正な場合。
        """
        payload = self._request_json(isbn)

        if not payload:
            return None

        matching_item = self._find_matching_item(
            items=payload,
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
    ) -> dict[str, str]:
        """openBD APIの検索パラメータを生成する。"""
        return {
            "isbn": isbn,
        }

    def _request_json(
        self,
        isbn: str,
    ) -> list[object]:
        """openBD APIへ接続してJSONを取得する。"""
        try:
            response = self._session.get(
                self.BASE_URL,
                params=self._build_params(isbn),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise BookMetadataConnectionError(
                "openBDへ接続できませんでした。"
            ) from exc

        if response.status_code == 429:
            raise BookMetadataRateLimitError(
                "openBDの利用制限に達しました。"
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise BookMetadataResponseError(
                "openBDから正常な応答を"
                "取得できませんでした。"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BookMetadataResponseError(
                "openBDの応答を解析できませんでした。"
            ) from exc

        if not isinstance(payload, list):
            raise BookMetadataResponseError(
                "openBDの応答形式が正しくありません。"
            )

        return payload

    def _find_matching_item(
        self,
        *,
        items: list[object],
        query_isbn: str,
    ) -> dict[str, Any] | None:
        """問い合わせISBNに一致する要素を返す。"""
        for item in items:
            if item is None:
                continue

            if not isinstance(item, dict):
                continue

            summary = item.get("summary")

            if not isinstance(summary, dict):
                continue

            candidate = summary.get("isbn")

            if not isinstance(candidate, str):
                continue

            try:
                normalized = normalize_isbn(candidate)
                candidate_isbn13 = to_isbn13(
                    normalized
                )
            except (TypeError, ValueError):
                continue

            if candidate_isbn13 == query_isbn:
                return item

        return None

    def _create_fetched_book_data(
        self,
        *,
        item: dict[str, Any],
        isbn: str,
        payload: list[object],
    ) -> FetchedBookData | None:
        """openBDの書誌情報を内部モデルへ変換する。"""
        summary = item.get("summary")

        if not isinstance(summary, dict):
            raise BookMetadataResponseError(
                "openBDのsummaryが正しくありません。"
            )

        title = self._normalize_optional_text(
            summary.get("title")
        )
        author = self._normalize_optional_text(
            summary.get("author")
        )
        publisher = self._normalize_optional_text(
            summary.get("publisher")
        )
        publication_date = (
            self._normalize_optional_text(
                summary.get("pubdate")
            )
        )
        cover_image_url = (
            self._normalize_optional_text(
                summary.get("cover")
            )
        )

        if not any(
            (
                title,
                author,
                publisher,
                publication_date,
                cover_image_url,
            )
        ):
            return None

        return FetchedBookData(
            isbn=isbn,
            title=title,
            author=author,
            publisher=publisher,
            publication_date=publication_date,
            publication_format=None,
            description=None,
            cover_image_url=cover_image_url,
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