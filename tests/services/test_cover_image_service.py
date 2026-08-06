"""Tests for CoverImageService."""

from pathlib import Path
from typing import Any

import pytest
import requests

from book_manager.services.cover_image_service import (
    CoverImageService,
)


class FakeResponse:
    """テスト用HTTPレスポンス。"""

    def __init__(
        self,
        *,
        content: bytes = b"image-data",
        content_type: str = "image/jpeg",
        status_code: int = 200,
    ) -> None:
        self.content = content
        self.headers = {
            "Content-Type": content_type,
        }
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """HTTPエラーを送出する。"""
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )


class FakeSession:
    """GET呼び出しを記録するFake Session。"""

    def __init__(
        self,
        response: FakeResponse,
    ) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        timeout: tuple[int, int],
    ) -> FakeResponse:
        """GET呼び出しを記録する。"""
        self.calls.append(
            {
                "url": url,
                "timeout": timeout,
            }
        )

        return self._response


def test_fetch_downloads_and_saves_image(
    tmp_path: Path,
) -> None:
    """画像を取得してキャッシュへ保存する。"""
    session = FakeSession(
        FakeResponse(
            content=b"test-image",
        )
    )
    service = CoverImageService(
        session=session,  # type: ignore[arg-type]
        cache_directory=tmp_path,
        timeout=(3, 20),
    )

    result = service.fetch(
        "https://example.com/cover.jpg"
    )

    assert result.exists()
    assert result.read_bytes() == b"test-image"
    assert result.suffix == ".jpg"
    assert session.calls == [
        {
            "url": "https://example.com/cover.jpg",
            "timeout": (3, 20),
        }
    ]


def test_fetch_uses_existing_cache(
    tmp_path: Path,
) -> None:
    """キャッシュ済みの場合は通信しない。"""
    session = FakeSession(
        FakeResponse(),
    )
    service = CoverImageService(
        session=session,  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    first_result = service.fetch(
        "https://example.com/cover.jpg"
    )
    session.calls.clear()

    second_result = service.fetch(
        "https://example.com/cover.jpg"
    )

    assert second_result == first_result
    assert session.calls == []


@pytest.mark.parametrize(
    "image_url",
    [
        "",
        "   ",
    ],
)
def test_fetch_rejects_empty_url(
    tmp_path: Path,
    image_url: str,
) -> None:
    """空のURLを拒否する。"""
    service = CoverImageService(
        session=FakeSession(  # type: ignore[arg-type]
            FakeResponse(),
        ),
        cache_directory=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="表紙画像URLが指定されていません。",
    ):
        service.fetch(image_url)


@pytest.mark.parametrize(
    "image_url",
    [
        "cover.jpg",
        "file:///cover.jpg",
        "ftp://example.com/cover.jpg",
    ],
)
def test_fetch_rejects_unsupported_url(
    tmp_path: Path,
    image_url: str,
) -> None:
    """HTTP/HTTPS以外のURLを拒否する。"""
    service = CoverImageService(
        session=FakeSession(  # type: ignore[arg-type]
            FakeResponse(),
        ),
        cache_directory=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="表紙画像URLが正しくありません。",
    ):
        service.fetch(image_url)


def test_fetch_rejects_non_image_response(
    tmp_path: Path,
) -> None:
    """画像以外のレスポンスを拒否する。"""
    service = CoverImageService(
        session=FakeSession(  # type: ignore[arg-type]
            FakeResponse(
                content_type="text/html",
            ),
        ),
        cache_directory=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="取得したデータは画像ではありません。",
    ):
        service.fetch(
            "https://example.com/cover.jpg"
        )


def test_fetch_raises_http_error(
    tmp_path: Path,
) -> None:
    """HTTP異常を呼び出し元へ通知する。"""
    service = CoverImageService(
        session=FakeSession(  # type: ignore[arg-type]
            FakeResponse(
                status_code=404,
            ),
        ),
        cache_directory=tmp_path,
    )

    with pytest.raises(
        requests.HTTPError,
    ):
        service.fetch(
            "https://example.com/cover.jpg"
        )


@pytest.mark.parametrize(
    ("image_url", "expected_suffix"),
    [
        (
            "https://example.com/cover.png",
            ".png",
        ),
        (
            "https://example.com/cover.webp?size=large",
            ".webp",
        ),
        (
            "https://example.com/content?id=123",
            ".jpg",
        ),
    ],
)
def test_fetch_uses_expected_file_suffix(
    tmp_path: Path,
    image_url: str,
    expected_suffix: str,
) -> None:
    """URLに応じた拡張子を利用する。"""
    service = CoverImageService(
        session=FakeSession(  # type: ignore[arg-type]
            FakeResponse(),
        ),
        cache_directory=tmp_path,
    )

    result = service.fetch(
        image_url,
    )

    assert result.suffix == expected_suffix