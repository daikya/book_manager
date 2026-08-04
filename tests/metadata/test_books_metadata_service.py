"""Tests for BookMetadataService."""

import pytest

from book_manager.metadata.book_metadata_service import (
    BookMetadataService,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)
from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
    BookMetadataConnectionError,
    BookMetadataError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)

class FakeBookMetadataClient:
    """Serviceテスト用の書誌情報取得Client。"""

    def __init__(
        self,
        source_name: str,
    ) -> None:
        """Fake Clientを初期化する。"""
        self._source_name = source_name

    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        return self._source_name

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """対象なしとしてNoneを返す。"""
        return None


def test_service_accepts_clients() -> None:
    """Clientを指定してServiceを生成できることを確認する。"""
    google_client = FakeBookMetadataClient(
        "Google Books"
    )
    openbd_client = FakeBookMetadataClient(
        "openBD"
    )

    service = BookMetadataService(
        clients=[
            google_client,
            openbd_client,
        ],
    )

    assert service._clients == (
        google_client,
        openbd_client,
    )


def test_service_preserves_client_order() -> None:
    """Clientの優先順位を維持することを確認する。"""
    first_client = FakeBookMetadataClient(
        "First"
    )
    second_client = FakeBookMetadataClient(
        "Second"
    )

    service = BookMetadataService(
        clients=[
            first_client,
            second_client,
        ],
    )

    assert service._clients[0] is first_client
    assert service._clients[1] is second_client


def test_service_copies_client_list_to_tuple() -> None:
    """元のリスト変更がServiceへ影響しないことを確認する。"""
    first_client = FakeBookMetadataClient(
        "First"
    )
    second_client = FakeBookMetadataClient(
        "Second"
    )
    clients = [
        first_client,
    ]

    service = BookMetadataService(
        clients=clients,
    )

    clients.append(second_client)

    assert service._clients == (
        first_client,
    )


@pytest.mark.parametrize(
    "clients",
    [
        [],
        (),
    ],
)
def test_service_rejects_empty_clients(
    clients: list[FakeBookMetadataClient]
    | tuple[FakeBookMetadataClient, ...],
) -> None:
    """Clientが空の場合に設定例外となることを確認する。"""
    with pytest.raises(
        BookMetadataConfigurationError,
        match=(
            "書誌情報取得Clientが"
            "登録されていません。"
        ),
    ):
        BookMetadataService(
            clients=clients,
        )

class RecordingBookMetadataClient:
    """呼び出し内容を記録するFake Client。"""

    def __init__(
        self,
        source_name: str,
        *,
        result: FetchedBookData | None = None,
        error: BookMetadataError | None = None,
    ) -> None:
        self._source_name = source_name
        self.result = result
        self.error = error
        self.calls: list[str] = []

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        self.calls.append(isbn)

        if self.error is not None:
            raise self.error

        return self.result

def test_fetch_by_isbn_calls_first_client() -> None:
    """最優先Clientのみ呼ばれることを確認する。"""

    expected = FetchedBookData(
        isbn="9784163917733",
        title="タイトル",
        author=None,
        publisher=None,
        publication_date=None,
        publication_format=None,
        description=None,
        cover_image_url=None,
        sources=("Google Books",),
        raw_data={},
    )

    client = RecordingBookMetadataClient(
        "Google Books",
        result=expected,
    )

    service = BookMetadataService(
        clients=[
            client,
        ],
    )

    result = service.fetch_by_isbn(
        "9784163917733",
    )

    assert result == expected

    assert client.calls == [
        "9784163917733",
    ]

def test_fetch_by_isbn_converts_isbn10() -> None:
    """ISBN-10をISBN-13へ変換してClientへ渡す。"""
    client = RecordingBookMetadataClient(
        "Google Books",
        result=None,
    )

    service = BookMetadataService(
        clients=[
            client,
        ],
    )

    with pytest.raises(
        BookMetadataNotFoundError,
        match="該当する書誌情報が見つかりませんでした。",
    ):
        service.fetch_by_isbn(
            "4101010013",
        )

    assert client.calls == [
        "9784101010014",
    ]

def test_fetch_by_isbn_rejects_invalid_isbn() -> None:
    """不正なISBNを拒否する。"""

    client = RecordingBookMetadataClient(
        None,
    )

    service = BookMetadataService(
        clients=[
            client,
        ],
    )

    with pytest.raises(
        ValueError,
    ):
        service.fetch_by_isbn(
            "12345",
        )

def test_fetch_by_isbn_calls_all_clients_in_order() -> None:
    """すべてのClientを登録順に呼び出す。"""
    call_order: list[str] = []

    class OrderedClient:
        def __init__(
            self,
            source_name: str,
        ) -> None:
            self._source_name = source_name

        @property
        def source_name(self) -> str:
            return self._source_name

        def fetch_by_isbn(
            self,
            isbn: str,
        ) -> FetchedBookData | None:
            call_order.append(
                self.source_name
            )
            return FetchedBookData(
                isbn=isbn,
                title=self.source_name,
                sources=(self.source_name,),
            )

    service = BookMetadataService(
        clients=[
            OrderedClient("First"),
            OrderedClient("Second"),
        ],
    )

    service.fetch_by_isbn(
        "9784163917733"
    )

    assert call_order == [
        "First",
        "Second",
    ]


def test_fetch_by_isbn_merges_missing_fields() -> None:
    """後順位Clientが空欄だけを補完する。"""
    google_result = FetchedBookData(
        isbn="9784163917733",
        title="Googleの書籍名",
        author="Googleの著者",
        publisher=None,
        publication_date="2024-04-24",
        description="Googleの内容紹介",
        cover_image_url=None,
        sources=("Google Books",),
        raw_data={
            "Google Books": {
                "response": "google",
            },
        },
    )
    openbd_result = FetchedBookData(
        isbn="9784163917733",
        title="openBDの書籍名",
        author="openBDの著者",
        publisher="文藝春秋",
        publication_date="20240424",
        description=None,
        cover_image_url=(
            "https://example.com/openbd.jpg"
        ),
        sources=("openBD",),
        raw_data={
            "openBD": {
                "response": "openbd",
            },
        },
    )

    service = BookMetadataService(
        clients=[
            RecordingBookMetadataClient(
                "Google Books",
                result=google_result,
            ),
            RecordingBookMetadataClient(
                "openBD",
                result=openbd_result,
            ),
        ],
    )

    result = service.fetch_by_isbn(
        "9784163917733"
    )

    assert result.title == "Googleの書籍名"
    assert result.author == "Googleの著者"
    assert result.publisher == "文藝春秋"
    assert result.publication_date == "2024-04-24"
    assert result.description == "Googleの内容紹介"
    assert (
        result.cover_image_url
        == "https://example.com/openbd.jpg"
    )
    assert result.sources == (
        "Google Books",
        "openBD",
    )
    assert result.raw_data == {
        "Google Books": {
            "response": "google",
        },
        "openBD": {
            "response": "openbd",
        },
    }


def test_fetch_by_isbn_preserves_normalized_input_isbn() -> None:
    """最終結果に正規化済み入力ISBNを保持する。"""
    client = RecordingBookMetadataClient(
        "Google Books",
        result=FetchedBookData(
            isbn="9784101010014",
            title="テスト書籍",
            sources=("Google Books",),
        ),
    )
    service = BookMetadataService(
        clients=[client],
    )

    result = service.fetch_by_isbn(
        "4-10-101001-3"
    )

    assert client.calls == [
        "9784101010014",
    ]
    assert result.isbn == "4101010013"


def test_fetch_by_isbn_succeeds_when_first_client_fails() -> None:
    """先順位Clientが失敗しても後順位の結果を返す。"""
    google_client = RecordingBookMetadataClient(
        "Google Books",
        error=BookMetadataConnectionError(
            "Google Books接続失敗"
        ),
    )
    openbd_client = RecordingBookMetadataClient(
        "openBD",
        result=FetchedBookData(
            isbn="9784163917733",
            title="openBDの書籍",
            sources=("openBD",),
        ),
    )
    service = BookMetadataService(
        clients=[
            google_client,
            openbd_client,
        ],
    )

    result = service.fetch_by_isbn(
        "9784163917733"
    )

    assert result.title == "openBDの書籍"
    assert result.sources == ("openBD",)


def test_fetch_by_isbn_ignores_later_client_error_after_success() -> None:
    """有効結果があれば後順位のエラーを送出しない。"""
    google_client = RecordingBookMetadataClient(
        "Google Books",
        result=FetchedBookData(
            isbn="9784163917733",
            title="Googleの書籍",
            sources=("Google Books",),
        ),
    )
    openbd_client = RecordingBookMetadataClient(
        "openBD",
        error=BookMetadataResponseError(
            "openBD応答失敗"
        ),
    )
    service = BookMetadataService(
        clients=[
            google_client,
            openbd_client,
        ],
    )

    result = service.fetch_by_isbn(
        "9784163917733"
    )

    assert result.title == "Googleの書籍"


def test_fetch_by_isbn_raises_not_found_when_all_return_none() -> None:
    """すべて対象なしの場合にNotFoundを送出する。"""
    service = BookMetadataService(
        clients=[
            RecordingBookMetadataClient(
                "Google Books"
            ),
            RecordingBookMetadataClient(
                "openBD"
            ),
        ],
    )

    with pytest.raises(
        BookMetadataNotFoundError,
        match="該当する書誌情報が見つかりませんでした。",
    ):
        service.fetch_by_isbn(
            "9784163917733"
        )


def test_fetch_by_isbn_raises_error_when_none_and_error_are_mixed() -> None:
    """対象なしと接続失敗の混在では接続例外を送出する。"""
    service = BookMetadataService(
        clients=[
            RecordingBookMetadataClient(
                "Google Books",
                result=None,
            ),
            RecordingBookMetadataClient(
                "openBD",
                error=BookMetadataConnectionError(
                    "openBD接続失敗"
                ),
            ),
        ],
    )

    with pytest.raises(
        BookMetadataConnectionError,
        match="openBD接続失敗",
    ):
        service.fetch_by_isbn(
            "9784163917733"
        )


def test_fetch_by_isbn_prioritizes_rate_limit_error() -> None:
    """全失敗時は利用制限例外を優先する。"""
    service = BookMetadataService(
        clients=[
            RecordingBookMetadataClient(
                "Google Books",
                error=BookMetadataConnectionError(
                    "接続失敗"
                ),
            ),
            RecordingBookMetadataClient(
                "openBD",
                error=BookMetadataRateLimitError(
                    "利用制限"
                ),
            ),
        ],
    )

    with pytest.raises(
        BookMetadataRateLimitError,
        match="利用制限",
    ):
        service.fetch_by_isbn(
            "9784163917733"
        )


def test_fetch_by_isbn_rejects_results_with_no_metadata() -> None:
    """有効な書誌項目がない結果を成功扱いしない。"""
    client = RecordingBookMetadataClient(
        "Google Books",
        result=FetchedBookData(
            isbn="9784163917733",
            sources=("Google Books",),
            raw_data={
                "Google Books": {},
            },
        ),
    )
    service = BookMetadataService(
        clients=[client],
    )

    with pytest.raises(
        BookMetadataNotFoundError,
        match="該当する書誌情報が見つかりませんでした。",
    ):
        service.fetch_by_isbn(
            "9784163917733"
        )