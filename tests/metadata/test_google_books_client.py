"""Tests for GoogleBooksClient."""

from typing import Any

import pytest
import requests

from book_manager.metadata.exceptions import (
    BookMetadataConnectionError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)
from book_manager.metadata.google_books_client import (
    GoogleBooksClient,
)


class FakeResponse:
    """Google Books APIのテスト用レスポンス。"""

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
        params: dict[str, str | int],
        timeout: tuple[int, int],
    ) -> FakeResponse:
        """GET呼び出しを記録してFakeResponseを返す。"""
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
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
    )

    assert client.source_name == "Google Books"


def test_build_params_without_api_key() -> None:
    """APIキーなしの検索パラメータを確認する。"""
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
    )

    params = client._build_params(
        "9784163917733",
    )

    assert params == {
        "q": "isbn:9784163917733",
        "maxResults": 10,
    }


def test_build_params_with_api_key() -> None:
    """APIキーありの検索パラメータを確認する。"""
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
        api_key="TEST_KEY",
    )

    params = client._build_params(
        "9784163917733",
    )

    assert params == {
        "q": "isbn:9784163917733",
        "maxResults": 10,
        "key": "TEST_KEY",
    }


def test_set_api_key_adds_key_to_later_request_params() -> None:
    """起動後に設定したAPIキーを以後の検索へ使用する。"""
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
    )

    client.set_api_key("NEW_TEST_KEY")

    assert client._build_params("9784163917733") == {
        "q": "isbn:9784163917733",
        "maxResults": 10,
        "key": "NEW_TEST_KEY",
    }


def test_set_api_key_replaces_existing_key() -> None:
    """設定済みのAPIキーを新しい値へ変更する。"""
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
        api_key="OLD_TEST_KEY",
    )

    client.set_api_key("NEW_TEST_KEY")

    assert client._build_params("9784163917733")["key"] == (
        "NEW_TEST_KEY"
    )


def test_set_api_key_with_none_removes_key_from_params() -> None:
    """APIキー削除後は検索パラメータへキーを含めない。"""
    client = GoogleBooksClient(
        session=FakeSession(),  # type: ignore[arg-type]
        api_key="TEST_KEY",
    )

    client.set_api_key(None)

    assert client._build_params("9784163917733") == {
        "q": "isbn:9784163917733",
        "maxResults": 10,
    }


def test_fetch_by_isbn_uses_updated_api_key() -> None:
    """APIキー変更後の通信に新しい値を使用する。"""
    session = FakeSession(
        response=FakeResponse(
            payload={
                "totalItems": 0,
            },
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
        api_key="OLD_TEST_KEY",
    )

    client.set_api_key("NEW_TEST_KEY")
    result = client.fetch_by_isbn("9784163917733")

    assert result is None
    assert session.calls[0]["params"] == {
        "q": "isbn:9784163917733",
        "maxResults": 10,
        "key": "NEW_TEST_KEY",
    }


def test_fetch_by_isbn_uses_expected_request_values() -> None:
    """URL、パラメータ、timeoutを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload={
                "totalItems": 0,
            },
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
        api_key="TEST_KEY",
        timeout=(3, 20),
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None
    assert session.calls == [
        {
            "url": (
                "https://www.googleapis.com/"
                "books/v1/volumes"
            ),
            "params": {
                "q": "isbn:9784163917733",
                "maxResults": 10,
                "key": "TEST_KEY",
            },
            "timeout": (3, 20),
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "totalItems": 0,
        },
        {
            "totalItems": 1,
        },
        {
            "totalItems": 1,
            "items": [],
        },
    ],
)
def test_fetch_by_isbn_returns_none_when_book_is_not_found(
    payload: dict[str, object],
) -> None:
    """対象書籍がない場合にNoneを返すことを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def test_fetch_by_isbn_converts_connection_error() -> None:
    """通信例外をConnectionErrorへ変換することを確認する。"""
    session = FakeSession(
        error=requests.ConnectionError(
            "connection failed"
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataConnectionError,
        match="Google Booksへ接続できませんでした。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_converts_timeout_error() -> None:
    """timeoutをConnectionErrorへ変換することを確認する。"""
    session = FakeSession(
        error=requests.Timeout(
            "request timed out"
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataConnectionError,
        match="Google Booksへ接続できませんでした。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_raises_rate_limit_error() -> None:
    """HTTP 429を利用制限例外へ変換することを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            status_code=429,
            payload={},
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataRateLimitError,
        match="Google Booksの利用制限に達しました。",
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        403,
        404,
        500,
        503,
    ],
)
def test_fetch_by_isbn_converts_http_error(
    status_code: int,
) -> None:
    """HTTP異常をResponseErrorへ変換することを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            status_code=status_code,
            payload={},
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "Google Booksから正常な応答を"
            "取得できませんでした。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_converts_json_error() -> None:
    """JSON解析失敗をResponseErrorへ変換することを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=None,
            json_error=ValueError(
                "invalid json"
            ),
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "Google Booksの応答を"
            "解析できませんでした。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "invalid",
        123,
        None,
    ],
)
def test_fetch_by_isbn_rejects_invalid_top_level_payload(
    payload: object,
) -> None:
    """辞書以外のJSONを拒否することを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "Google Booksの応答形式が"
            "正しくありません。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )


def test_fetch_by_isbn_rejects_non_list_items() -> None:
    """itemsが配列でない場合にエラーとなることを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload={
                "totalItems": 1,
                "items": {
                    "invalid": "value",
                },
            },
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(
        BookMetadataResponseError,
        match=(
            "Google Booksのitemsが"
            "配列ではありません。"
        ),
    ):
        client.fetch_by_isbn(
            "9784163917733",
        )
def test_fetch_by_isbn_returns_matching_book_metadata() -> None:
    """ISBNが一致する書誌情報を取得できることを確認する。"""
    payload = {
        "totalItems": 1,
        "items": [
            {
                "volumeInfo": {
                    "title": " テスト書籍 ",
                    "authors": [
                        "著者A",
                        " 著者B ",
                    ],
                    "publisher": "テスト出版社",
                    "publishedDate": "2023-10-27",
                    "description": "内容紹介",
                    "industryIdentifiers": [
                        {
                            "type": "ISBN_13",
                            "identifier": (
                                "9784163917733"
                            ),
                        }
                    ],
                    "imageLinks": {
                        "thumbnail": (
                            "https://example.com/"
                            "thumbnail.jpg"
                        ),
                        "large": (
                            "https://example.com/"
                            "large.jpg"
                        ),
                    },
                }
            }
        ],
    }
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is not None
    assert result.isbn == "9784163917733"
    assert result.title == "テスト書籍"
    assert result.author == "著者A、著者B"
    assert result.publisher == "テスト出版社"
    assert result.publication_date == "2023-10-27"
    assert result.publication_format is None
    assert result.description == "内容紹介"
    assert (
        result.cover_image_url
        == "https://example.com/large.jpg"
    )
    assert result.sources == ("Google Books",)
    assert result.raw_data == {
        "Google Books": {
            "query": {
                "isbn": "9784163917733",
            },
            "response": payload,
        }
    }


def test_fetch_by_isbn_skips_first_non_matching_item() -> None:
    """先頭候補が不一致でも後続の一致候補を取得する。"""
    payload = {
        "totalItems": 2,
        "items": [
            {
                "volumeInfo": {
                    "title": "不一致書籍",
                    "industryIdentifiers": [
                        {
                            "type": "ISBN_13",
                            "identifier": (
                                "9784101010014"
                            ),
                        }
                    ],
                }
            },
            {
                "volumeInfo": {
                    "title": "一致書籍",
                    "industryIdentifiers": [
                        {
                            "type": "ISBN_13",
                            "identifier": (
                                "9784163917733"
                            ),
                        }
                    ],
                }
            },
        ],
    }
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is not None
    assert result.title == "一致書籍"


def test_fetch_by_isbn_matches_isbn10_identifier() -> None:
    """ISBN-10識別子をISBN-13へ変換して照合する。"""
    payload = {
        "totalItems": 1,
        "items": [
            {
                "volumeInfo": {
                    "title": "ISBN-10書籍",
                    "industryIdentifiers": [
                        {
                            "type": "ISBN_10",
                            "identifier": (
                                "4101010013"
                            ),
                        }
                    ],
                }
            }
        ],
    }
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784101010014",
    )

    assert result is not None
    assert result.title == "ISBN-10書籍"


def test_fetch_by_isbn_returns_none_without_matching_isbn() -> None:
    """ISBN一致候補がなければNoneを返す。"""
    session = FakeSession(
        response=FakeResponse(
            payload={
                "totalItems": 1,
                "items": [
                    {
                        "volumeInfo": {
                            "title": "別の書籍",
                            "industryIdentifiers": [
                                {
                                    "type": "ISBN_13",
                                    "identifier": (
                                        "9784101010014"
                                    ),
                                }
                            ],
                        }
                    }
                ],
            },
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def test_fetch_by_isbn_allows_missing_optional_fields() -> None:
    """任意項目が欠けていても取得できることを確認する。"""
    session = FakeSession(
        response=FakeResponse(
            payload={
                "totalItems": 1,
                "items": [
                    {
                        "volumeInfo": {
                            "title": "書籍名のみ",
                            "industryIdentifiers": [
                                {
                                    "type": "ISBN_13",
                                    "identifier": (
                                        "9784163917733"
                                    ),
                                }
                            ],
                        }
                    }
                ],
            },
        ),
    )
    client = GoogleBooksClient(
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


def test_fetch_by_isbn_ignores_invalid_identifiers() -> None:
    """不正な識別子を無視して処理を継続する。"""
    payload = {
        "totalItems": 1,
        "items": [
            {
                "volumeInfo": {
                    "title": "テスト書籍",
                    "industryIdentifiers": [
                        None,
                        "invalid",
                        {
                            "type": "OTHER",
                            "identifier": "value",
                        },
                        {
                            "type": "ISBN_13",
                            "identifier": "invalid",
                        },
                    ],
                }
            }
        ],
    }
    session = FakeSession(
        response=FakeResponse(
            payload=payload,
        ),
    )
    client = GoogleBooksClient(
        session=session,  # type: ignore[arg-type]
    )

    result = client.fetch_by_isbn(
        "9784163917733",
    )

    assert result is None


def search_client(payload):
    session = FakeSession(response=FakeResponse(payload=payload))
    return GoogleBooksClient(session=session, api_key="TEST_KEY"), session


def test_search_params():
    client, session = search_client({"totalItems": 0})
    client.set_api_key("NEW_KEY")
    assert client.search_candidates(title=" 三体 II ", author=" 劉 慈欣 ") == []
    assert session.calls[0]["params"] == {
        "q": '三体 II 劉 慈欣',
        "maxResults": 20, "printType": "books", "key": "NEW_KEY",
    }


@pytest.mark.parametrize("kwargs,error", [
    ({}, ValueError), ({"title": "　"}, ValueError),
    ({"title": None}, TypeError), ({"title": "本", "author": 1}, TypeError),
    ({"title": "本", "max_results": True}, TypeError),
    ({"title": "本", "max_results": 0}, ValueError),
    ({"title": "本", "max_results": 41}, ValueError),
])
def test_search_invalid_input(kwargs, error):
    client, session = search_client({})
    with pytest.raises(error):
        client.search_candidates(**kwargs)
    assert session.calls == []


@pytest.mark.parametrize("field", ["title", "author"])
def test_search_single_condition(field):
    client, session = search_client({})
    assert client.search_candidates(**{field: "検索語"}) == []
    assert session.calls[0]["params"]["q"] == "検索語"


def test_search_metadata_isbns_and_missing_isbn():
    client, _ = search_client({"items": [
        {"id": "a", "volumeInfo": {
            "title": " 書籍 ", "subtitle": " 第二巻 ",
            "authors": ["著者A", " 著者B "],
            "publisher": "出版元", "publishedDate": "2020-05",
            "imageLinks": {"thumbnail": "https://example.com/cover"},
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "4101010013"},
                {"type": "ISBN_13", "identifier": "978-4-10-101001-4"},
                {"type": "ISBN_13", "identifier": "9784163917733"},
                {"type": "ISBN_13", "identifier": "9784163917730"},
                {"type": "OTHER", "identifier": "9784101010014"}, None,
            ],
        }, "saleInfo": {"isEbook": True}},
        {"id": "b", "volumeInfo": {"title": "ISBNなし"}},
    ]})
    first, second = client.search_candidates(title="書籍")
    assert first.title == "書籍"
    assert first.subtitle == "第二巻"
    assert first.author == "著者A、著者B"
    assert first.publisher == "出版元"
    assert first.publication_date == "2020-05"
    assert first.cover_image_url == "https://example.com/cover"
    assert first.isbn_candidates == ("9784101010014", "9784163917733")
    assert first.is_ebook is True
    assert second.isbn_candidates == ()
    assert second.is_ebook is None


def test_search_malformed_items_and_duplicate_ids():
    client, _ = search_client({"items": [
        None, {}, {"volumeInfo": []}, {"volumeInfo": {"title": " "}},
        {"id": "a", "volumeInfo": {"title": "第一候補"}},
        {"id": "a", "volumeInfo": {"title": "重複"}},
        {"id": "b", "volumeInfo": {"title": "別の版"}},
    ]})
    assert [c.title for c in client.search_candidates(title="本")] == [
        "第一候補", "別の版",
    ]


def test_search_limit_without_pagination():
    client, session = search_client({"totalItems": 100, "items": [
        {"id": str(i), "volumeInfo": {"title": str(i)}} for i in range(10)
    ]})
    assert len(client.search_candidates(title="本", max_results=3)) == 3
    assert len(session.calls) == 1


@pytest.mark.parametrize("payload", [[], None, "invalid", {"items": None},
                                     {"items": {}}])
def test_search_bad_response(payload):
    client, _ = search_client(payload)
    with pytest.raises(BookMetadataResponseError):
        client.search_candidates(title="本")


@pytest.mark.parametrize("status,error", [
    (429, BookMetadataRateLimitError),
    (403, BookMetadataResponseError), (500, BookMetadataResponseError),
])
def test_search_http_error_without_retry(status, error):
    session = FakeSession(response=FakeResponse(status_code=status, payload={}))
    with pytest.raises(error):
        GoogleBooksClient(session=session).search_candidates(title="本")
    assert len(session.calls) == 1


@pytest.mark.parametrize("error", [requests.Timeout(), requests.ConnectionError()])
def test_search_connection_error(error):
    session = FakeSession(error=error)
    with pytest.raises(BookMetadataConnectionError):
        GoogleBooksClient(session=session).search_candidates(title="本")
    assert len(session.calls) == 1


def test_search_json_error():
    session = FakeSession(response=FakeResponse(json_error=ValueError("invalid")))
    with pytest.raises(BookMetadataResponseError):
        GoogleBooksClient(session=session).search_candidates(title="本")


def test_search_key_removed():
    client, session = search_client({})
    client.set_api_key(None)
    client.search_candidates(title="本")
    assert "key" not in session.calls[0]["params"]


def test_search_preserves_volumes_with_same_isbn():
    client, _ = search_client({"items": [
        {"id": i, "volumeInfo": {"title": i, "industryIdentifiers": [
            {"type": "ISBN_13", "identifier": "9784101010014"}
        ]}} for i in ("a", "b")
    ]})
    assert len(client.search_candidates(title="本")) == 2


def test_search_wrong_identifier_length_and_optional_types():
    client, _ = search_client({"items": [{
        "volumeInfo": {
            "title": "候補", "authors": "著者", "imageLinks": [],
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "9784101010014"},
                {"type": "ISBN_13", "identifier": "4101010013"},
            ],
        }, "saleInfo": {"isEbook": "false"},
    }]})
    candidate = client.search_candidates(title="候補")[0]
    assert candidate.isbn_candidates == ()
    assert candidate.author is None
    assert candidate.cover_image_url is None
    assert candidate.is_ebook is None


def test_search_removes_quote_and_field_operator():
    client, session = search_client({})
    client.search_candidates(title='本" inauthor:別人')
    assert session.calls[0]["params"]["q"] == '本 inauthor 別人'
