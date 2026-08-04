"""Tests for the BookMetadataClient Protocol."""

from book_manager.metadata.protocols import BookMetadataClient
from book_manager.models.fetched_book_data import FetchedBookData


class FakeBookMetadataClient:
    """Protocolへ適合するテスト用Client。"""

    @property
    def source_name(self) -> str:
        """取得元名を返す。"""
        return "Fake"

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData | None:
        """テスト用の書誌情報を返す。"""
        return FetchedBookData(
            isbn=isbn,
            title="テスト書籍",
            sources=(self.source_name,),
        )


def get_source_name(
    client: BookMetadataClient,
) -> str:
    """Protocolを引数型として利用する。"""
    return client.source_name


def fetch_test_data(
    client: BookMetadataClient,
    isbn: str,
) -> FetchedBookData | None:
    """Protocol経由で書誌情報を取得する。"""
    return client.fetch_by_isbn(isbn)


def test_protocol_accepts_structurally_compatible_client() -> None:
    """継承なしのClientをProtocol型として利用できることを確認する。"""
    client = FakeBookMetadataClient()

    assert get_source_name(client) == "Fake"


def test_protocol_client_can_fetch_book_metadata() -> None:
    """Protocol経由で書誌情報を取得できることを確認する。"""
    client = FakeBookMetadataClient()

    result = fetch_test_data(
        client,
        "9784163917733",
    )

    assert result is not None
    assert result.isbn == "9784163917733"
    assert result.title == "テスト書籍"
    assert result.sources == ("Fake",)


def test_protocol_client_can_return_none() -> None:
    """対象なしの場合にNoneを返せることを確認する。"""

    class NotFoundClient:
        @property
        def source_name(self) -> str:
            return "Not Found"

        def fetch_by_isbn(
            self,
            isbn: str,
        ) -> FetchedBookData | None:
            return None

    client = NotFoundClient()

    result = fetch_test_data(
        client,
        "9784163917733",
    )

    assert result is None