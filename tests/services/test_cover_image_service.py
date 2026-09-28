"""Tests for CoverImageService."""

from pathlib import Path
from typing import Any

import pytest
import requests

from book_manager.services.cover_image_service import (
    CoverCacheError,
    CoverCacheStatus,
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


def test_get_cache_status_returns_empty_for_missing_directory(
    tmp_path: Path,
) -> None:
    """未作成のキャッシュを0件として扱う。"""
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path / "missing",
    )

    assert service.get_cache_status() == CoverCacheStatus(
        file_count=0,
        total_size_bytes=0,
    )


def test_get_cache_status_counts_files_and_sizes(
    tmp_path: Path,
) -> None:
    """直下ファイルの件数と合計サイズを返す。"""
    (tmp_path / "first.jpg").write_bytes(b"123")
    (tmp_path / "second.png").write_bytes(b"45678")
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    assert service.get_cache_status() == CoverCacheStatus(
        file_count=2,
        total_size_bytes=8,
    )


def test_get_cache_status_ignores_subdirectories(
    tmp_path: Path,
) -> None:
    """サブディレクトリとその内容を集計しない。"""
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    (nested_directory / "nested.jpg").write_bytes(b"nested")
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    assert service.get_cache_status() == CoverCacheStatus(
        file_count=1,
        total_size_bytes=5,
    )


def test_get_cache_status_wraps_directory_error(
    tmp_path: Path,
) -> None:
    """キャッシュ保存先がディレクトリでなければ専用例外にする。"""
    cache_path = tmp_path / "covers"
    cache_path.write_bytes(b"not-directory")
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=cache_path,
    )

    with pytest.raises(
        CoverCacheError,
        match="状態を確認できません",
    ):
        service.get_cache_status()


def test_clear_cache_deletes_files_and_preserves_directory(
    tmp_path: Path,
) -> None:
    """直下ファイルを削除してキャッシュディレクトリを残す。"""
    (tmp_path / "first.jpg").write_bytes(b"123")
    (tmp_path / "second.png").write_bytes(b"45678")
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    result = service.clear_cache()

    assert result.deleted_count == 2
    assert result.deleted_size_bytes == 8
    assert result.failed_count == 0
    assert result.remaining_status == CoverCacheStatus(0, 0)
    assert tmp_path.is_dir()
    assert tuple(tmp_path.iterdir()) == ()


def test_clear_cache_preserves_subdirectories(
    tmp_path: Path,
) -> None:
    """サブディレクトリとその内容を削除しない。"""
    nested_directory = tmp_path / "nested"
    nested_directory.mkdir()
    nested_file = nested_directory / "nested.jpg"
    nested_file.write_bytes(b"nested")
    (tmp_path / "cover.jpg").write_bytes(b"cover")
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    result = service.clear_cache()

    assert result.deleted_count == 1
    assert result.failed_count == 0
    assert nested_file.read_bytes() == b"nested"
    assert result.remaining_status == CoverCacheStatus(0, 0)


def test_clear_cache_returns_empty_result_for_missing_directory(
    tmp_path: Path,
) -> None:
    """未作成のキャッシュを正常な空状態として扱う。"""
    cache_directory = tmp_path / "missing"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=cache_directory,
    )

    result = service.clear_cache()

    assert result.deleted_count == 0
    assert result.deleted_size_bytes == 0
    assert result.failed_count == 0
    assert result.remaining_status == CoverCacheStatus(0, 0)
    assert not cache_directory.exists()


def test_clear_cache_continues_after_individual_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1件を削除できなくても残りの削除を継続する。"""
    failed_file = tmp_path / "failed.jpg"
    deleted_file = tmp_path / "deleted.jpg"
    failed_file.write_bytes(b"failed")
    deleted_file.write_bytes(b"deleted")
    original_unlink = Path.unlink

    def unlink_with_failure(
        path: Path,
        *args: object,
        **kwargs: object,
    ) -> None:
        if path == failed_file:
            raise PermissionError("denied")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink_with_failure)
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )

    result = service.clear_cache()

    assert result.deleted_count == 1
    assert result.deleted_size_bytes == len(b"deleted")
    assert result.failed_count == 1
    assert result.remaining_status == CoverCacheStatus(
        file_count=1,
        total_size_bytes=len(b"failed"),
    )
    assert failed_file.exists()
    assert not deleted_file.exists()


def test_create_stored_path_returns_root_relative_posix_path(
    tmp_path: Path,
) -> None:
    """表紙画像を利用者データルートからの相対パスにする。"""
    root_directory = tmp_path / "application"
    cache_directory = root_directory / "cache" / "covers"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=cache_directory,
        root_directory=root_directory,
    )
    image_path = cache_directory / "cover.jpg"

    result = service.create_stored_path(image_path)

    assert result == "cache/covers/cover.jpg"


def test_create_stored_path_rejects_path_outside_cover_cache(
    tmp_path: Path,
) -> None:
    """表紙キャッシュ外の画像パスを保存しない。"""
    root_directory = tmp_path / "application"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=root_directory / "cache" / "covers",
        root_directory=root_directory,
    )

    with pytest.raises(
        ValueError,
        match="表紙キャッシュ内を指定してください。",
    ):
        service.create_stored_path(
            tmp_path / "outside.jpg",
        )


def test_constructor_rejects_cache_outside_root(
    tmp_path: Path,
) -> None:
    """利用者データルート外のキャッシュ設定を拒否する。"""
    with pytest.raises(
        ValueError,
        match="利用者データルート内を指定してください。",
    ):
        CoverImageService(
            session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
            cache_directory=tmp_path / "outside",
            root_directory=tmp_path / "application",
        )


def test_resolve_stored_path_resolves_relative_path(
    tmp_path: Path,
) -> None:
    """相対保存パスを利用者データルート基準で解決する。"""
    root_directory = tmp_path / "application"
    cache_directory = root_directory / "cache" / "covers"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=cache_directory,
        root_directory=root_directory,
    )

    result = service.resolve_stored_path(
        "cache/covers/cover.jpg",
    )

    assert result == cache_directory / "cover.jpg"


@pytest.mark.parametrize(
    "stored_path",
    [
        None,
        "",
        "   ",
    ],
)
def test_resolve_stored_path_returns_none_for_empty_path(
    tmp_path: Path,
    stored_path: str | None,
) -> None:
    """空の保存パスをNoneとして扱う。"""
    root_directory = tmp_path / "application"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=root_directory / "cache" / "covers",
        root_directory=root_directory,
    )

    assert service.resolve_stored_path(stored_path) is None


def test_resolve_stored_path_keeps_existing_absolute_path(
    tmp_path: Path,
) -> None:
    """既存DBの絶対パスを互換目的で解決する。"""
    root_directory = tmp_path / "application"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=root_directory / "cache" / "covers",
        root_directory=root_directory,
    )
    absolute_path = tmp_path / "legacy" / "cover.jpg"

    result = service.resolve_stored_path(
        str(absolute_path),
    )

    assert result == absolute_path


@pytest.mark.parametrize(
    "stored_path",
    [
        "../outside.jpg",
        "cache/covers/../../../outside.jpg",
        "cache/other/image.jpg",
    ],
)
def test_resolve_stored_path_rejects_path_outside_cover_cache(
    tmp_path: Path,
    stored_path: str,
) -> None:
    """表紙キャッシュ外を参照する相対パスを拒否する。"""
    root_directory = tmp_path / "application"
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=root_directory / "cache" / "covers",
        root_directory=root_directory,
    )

    assert service.resolve_stored_path(stored_path) is None


def test_path_conversion_preserves_previous_behavior_without_root(
    tmp_path: Path,
) -> None:
    """ルート未設定時は既存呼び出しとの互換性を維持する。"""
    service = CoverImageService(
        session=FakeSession(FakeResponse()),  # type: ignore[arg-type]
        cache_directory=tmp_path,
    )
    relative_path = Path("cache/covers/cover.jpg")

    assert (
        service.create_stored_path(relative_path)
        == relative_path.as_posix()
    )
    assert (
        service.resolve_stored_path(relative_path.as_posix())
        == relative_path
    )
