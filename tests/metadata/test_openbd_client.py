"""Tests for OpenBdClient."""

from typing import Any

import pytest
import requests

from book_manager.metadata.exceptions import (
    BookMetadataConnectionError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)
from book_manager.metadata.openbd_client import (
    OpenBdClient,
)


class FakeResponse:
    """openBD APIのテスト用レスポンス。"""

    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object = None,
        json_error: ValueError | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self) -> None:
        """HTTP異常時にHTTPErrorを送出する。"""
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )

    def json(self) -> object:
        """設定されたJSONデータを返す。"""
        if self._json_error is not None:
            raise self._json_error

        return self._payload


class FakeSession:
    """requests.Sessionのテスト用Fake。"""

    def __init__(
        self,
        *,
        response: FakeResponse | None = None,
        error: requests.RequestException | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: tuple[int, int],
    ) -> FakeResponse:
        """GET呼び出しを記録してレスポンスを返す。"""
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )

        if self._error is not None:
            raise self._error

        if self._response is None:
            raise AssertionError(
                "FakeResponseが設定されていません。"
            )

        return self._response


def test_source_name() -> None:
    """取得元名を確認する。"""
    client = OpenBdClient(
        session=FakeSession(),  # type: ignore[arg-type]
    )

    assert client.source_name == "openBD"


def test_build_params() -> None:
    """検索パラメータを確認する。"""
    client = OpenBdClient(
        session=FakeSession(),  # type: ignore[arg-type]
    )

    params = client._build_params(
        "9784163917733",
    )

    assert params == {
        "isbn": "9784163917733",
    }


def test_fetch_by_isbn_uses_expected_request_values() -> None:
    """URL、パラメータ、timeoutを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=[None],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
        timeout=(3, 20),
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None
    assert session.calls == [
        {
            "url": "https://api.openbd.jp/v1/get",
            "params": {
                "isbn": "9784163917733",
            },
            "timeout": (3, 20),
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        [None],
    ],
)
def test_fetch_by_isbn_returns_none_when_not_found(
    payload: list[object],
) -> None:
    """対象書籍がない場合にNoneを返す。"""
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def test_fetch_by_isbn_returns_summary_metadata() -> None:
    """summaryから書誌情報を取得できる。"""
    payload = [
        {
            "summary": {
                "isbn": "9784163917733",
                "title": " 俺たちの箱根駅伝 下 ",
                "author": "池井戸潤",
                "publisher": "文藝春秋",
                "pubdate": "20240424",
                "cover": (
                    "https://cover.openbd.jp/"
                    "9784163917733.jpg"
                ),
            }
        }
    ]
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is not None
    assert result.isbn == "9784163917733"
    assert result.title == "俺たちの箱根駅伝 下"
    assert result.author == "池井戸潤"
    assert result.publisher == "文藝春秋"
    assert result.publication_date == "20240424"
    assert result.publication_format is None
    assert result.description is None
    assert (
        result.cover_image_url
        == (
            "https://cover.openbd.jp/"
            "9784163917733.jpg"
        )
    )
    assert result.sources == ("openBD",)
    assert result.raw_data == {
        "openBD": {
            "query": {
                "isbn": "9784163917733",
            },
            "response": payload,
        }
    }


def test_fetch_by_isbn_matches_isbn10_summary() -> None:
    """summaryのISBN-10をISBN-13へ変換して照合する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=[
                {
                    "summary": {
                        "isbn": "4101010013",
                        "title": "ISBN-10書籍",
                    }
                }
            ],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784101010014",
    )

    assert result is not None
    assert result.title == "ISBN-10書籍"


def test_fetch_by_isbn_returns_none_for_non_matching_isbn() -> None:
    """ISBNが一致しない場合にNoneを返す。"""
    session = FakeSession(
        response=FakeResponse(
            payload=[
                {
                    "summary": {
                        "isbn": "9784101010014",
                        "title": "別の書籍",
                    }
                }
            ],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def test_fetch_by_isbn_allows_missing_optional_fields() -> None:
    """任意項目が欠けていても取得できる。"""
    session = FakeSession(
        response=FakeResponse(
            payload=[
                {
                    "summary": {
                        "isbn": "9784163917733",
                        "title": "書籍名のみ",
                    }
                }
            ],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is not None
    assert result.title == "書籍名のみ"
    assert result.author is None
    assert result.publisher is None
    assert result.publication_date is None
    assert result.description is None
    assert result.cover_image_url is None


def test_fetch_by_isbn_returns_none_when_all_fields_are_empty() -> None:
    """有効な書誌項目がない場合にNoneを返す。"""
    session = FakeSession(
        response=FakeResponse(
            payload=[
                {
                    "summary": {
                        "isbn": "9784163917733",
                        "title": " ",
                        "author": "",
                    }
                }
            ],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def test_fetch_by_isbn_converts_connection_error() -> None:
    """通信例外をConnectionErrorへ変換する。"""
    session = FakeSession(
        error=requests.ConnectionError(
            "connection failed"
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataConnectionError,
        match="openBDへ接続できませんでした。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_converts_timeout_error() -> None:
    """timeoutをConnectionErrorへ変換する。"""
    session = FakeSession(
        error=requests.Timeout(
            "request timed out"
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataConnectionError,
        match="openBDへ接続できませんでした。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_raises_rate_limit_error() -> None:
    """HTTP 429を利用制限例外へ変換する。"""
    session = FakeSession(
        response=FakeResponse(
            status_code=429,
            payload=[],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataRateLimitError,
        match="openBDの利用制限に達しました。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        404,
        500,
        503,
    ],
)
def test_fetch_by_isbn_converts_http_error(
    status_code: int,
) -> None:
    """HTTP異常をResponseErrorへ変換する。"""
    session = FakeSession(
        response=FakeResponse(
            status_code=status_code,
            payload=[],
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "openBDから正常な応答を"
            "取得できませんでした。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_converts_json_error() -> None:
    """JSON解析失敗をResponseErrorへ変換する。"""
    session = FakeSession(
        response=FakeResponse(
            json_error=ValueError(
                "invalid json"
            ),
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "openBDの応答を"
            "解析できませんでした。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        "invalid",
        123,
        None,
    ],
)
def test_fetch_by_isbn_rejects_invalid_top_level_payload(
    payload: object,
) -> None:
    """配列以外のJSONを拒否する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = OpenBdClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "openBDの応答形式が"
            "正しくありません。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )