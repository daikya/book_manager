"""Google Books API client."""

from __future__ import annotations

from typing import Any

from book_manager.metadata.candidate_matching import prepare_search_terms, rank_candidates

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

from book_manager.models.book_search_candidate import BookSearchCandidate


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

    def set_api_key(self, api_key: str | None) -> None:
        """以後の通信に使用するAPIキーを変更する。"""
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        return "Google Books"

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """ISBNに対応する書誌情報を取得する。

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

    def search_candidates(
        self,
        *,
        title: str = "",
        author: str = "",
        publisher: str = "",
        max_results: int = 20,
        start_index: int = 0,
    ) -> list[BookSearchCandidate]:
        """書籍名・著者名・出版社から未確認の候補を取得する。

        少なくとも1項目を指定する。1回の呼出しで最大40件を要求し、
        ページ追加取得・自動再試行・DB更新は行わない。
        ISBNなしの候補も返す。媒体・版は推測しない。
        GUIからはワーカーで呼び出す。
        """
        conditions = prepare_search_terms(title=title, author=author, publisher=publisher)
        if type(max_results) is not int:
            raise TypeError("取得件数は整数で指定してください。")
        if not 1 <= max_results <= 40:
            raise ValueError("取得件数は1から40の範囲で指定してください。")
        if type(start_index) is not int or not 0 <= start_index <= 180:
            raise ValueError("検索位置は0から180の整数で指定してください。")
        parts = [value for value in conditions.values() if value]
        params: dict[str, str | int] = {
            "q": " ".join(parts),
            "maxResults": max_results,
            "printType": "books",
        }
        if self._api_key:
            params["key"] = self._api_key
        if start_index:
            params["startIndex"] = start_index
        payload = self._request_params(params)
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise BookMetadataResponseError(
                "Google Booksのitemsが配列ではありません。"
            )
        if payload.get("totalItems") == 0:
            return []

        candidates = []
        seen_ids: set[str] = set()
        for item in items[:max_results]:
            if not isinstance(item, dict):
                continue
            info = item.get("volumeInfo")
            if not isinstance(info, dict):
                continue
            candidate_title = self._normalize_optional_text(info.get("title"))
            if candidate_title is None:
                continue
            volume_id = self._normalize_optional_text(item.get("id"))
            if volume_id is not None:
                if volume_id in seen_ids:
                    continue
                seen_ids.add(volume_id)
            sale_info = item.get("saleInfo")
            is_ebook = (
                sale_info.get("isEbook")
                if isinstance(sale_info, dict) else None
            )
            candidates.append(BookSearchCandidate(
                source=self.source_name,
                source_id=volume_id,
                title=candidate_title,
                subtitle=self._normalize_optional_text(info.get("subtitle")),
                author=self._extract_authors(info.get("authors")),
                publisher=self._normalize_optional_text(info.get("publisher")),
                publication_date=self._normalize_optional_text(
                    info.get("publishedDate")
                ),
                cover_image_url=self._extract_cover_image_url(
                    info.get("imageLinks")
                ),
                isbn_candidates=self._extract_candidate_isbns(
                    info.get("industryIdentifiers")
                ),
                is_ebook=is_ebook if type(is_ebook) is bool else None,
            ))
        return rank_candidates(candidates, title=title, author=author, publisher=publisher)

    def fetch_candidate(self, candidate: BookSearchCandidate, *, isbn: str = "") -> FetchedBookData:
        """選択されたGoogle IDを直接取得し、ID・選択ISBNを検証する。"""
        from urllib.parse import quote

        if candidate.source != self.source_name or not candidate.source_id:
            raise ValueError("Google IDを持つ候補を選択してください。")
        if isbn and isbn not in candidate.isbn_candidates:
            raise ValueError("候補に含まれるISBNを選択してください。")
        params = {"key": self._api_key} if self._api_key else {}
        payload = self._request_params(
            params, url=self.BASE_URL + "/" + quote(candidate.source_id, safe=""),
        )
        if payload.get("id") != candidate.source_id:
            raise BookMetadataResponseError("選択したGoogle IDと応答が一致しません。")
        info = payload.get("volumeInfo")
        if not isinstance(info, dict):
            raise BookMetadataResponseError("候補の書誌情報が正しくありません。")
        if isbn and isbn not in self._extract_candidate_isbns(info.get("industryIdentifiers")):
            raise BookMetadataResponseError("選択したISBNと詳細情報が一致しません。")
        return self._create_fetched_book_data(item=payload, isbn=isbn, payload=payload)

    @staticmethod
    def _extract_candidate_isbns(value: object) -> tuple[str, ...]:
        """有効なISBNだけをISBN-13に統一し、重複を除く。"""
        if not isinstance(value, list):
            return ()
        result = []
        for identifier in value:
            if not isinstance(identifier, dict):
                continue
            kind = identifier.get("type")
            text = identifier.get("identifier")
            if kind not in ("ISBN_10", "ISBN_13") or not isinstance(text, str):
                continue
            try:
                normalized = normalize_isbn(text)
                expected_length = 10 if kind == "ISBN_10" else 13
                if len(normalized) != expected_length:
                    continue
                isbn = to_isbn13(normalized)
            except (TypeError, ValueError):
                continue
            if isbn not in result:
                result.append(isbn)
        return tuple(result)

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
        return self._request_params(self._build_params(isbn))

    def _request_params(
        self,
        params: dict[str, str | int],
        *, url: str | None = None,
    ) -> dict[str, Any]:
        """検索とISBN取得で共通のHTTP・JSON処理を行う。"""
        try:
            response = self._session.get(
                url or self.BASE_URL,
                params=params,
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
