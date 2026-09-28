"""表紙画像の取得とキャッシュを担当するService。"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests import Session


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CoverCacheStatus:
    """表紙画像キャッシュの存在状態。"""

    file_count: int
    total_size_bytes: int


@dataclass(frozen=True, slots=True)
class CoverCacheClearResult:
    """表紙画像キャッシュの削除結果。"""

    deleted_count: int
    deleted_size_bytes: int
    failed_count: int
    remaining_status: CoverCacheStatus


class CoverCacheError(RuntimeError):
    """表紙画像キャッシュを確認または整理できない場合。"""


class CoverImageService:
    """表紙画像を取得してローカルへ保存する。"""

    def __init__(
        self,
        *,
        session: Session,
        cache_directory: Path,
        root_directory: Path | None = None,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        """Serviceを初期化する。

        Args:
            session:
                HTTP通信に使用するSession。
            cache_directory:
                表紙画像の保存先。
            root_directory:
                DBへ保存する相対パスの基準となる
                利用者データルート。
            timeout:
                接続・読み込みtimeout。
        """
        self._session = session
        self._cache_directory = Path(
            cache_directory,
        ).resolve(strict=False)
        self._root_directory = (
            Path(root_directory).resolve(strict=False)
            if root_directory is not None
            else None
        )

        if self._root_directory is not None:
            try:
                self._cache_directory.relative_to(
                    self._root_directory,
                )
            except ValueError as error:
                raise ValueError(
                    "表紙キャッシュは利用者データルート内を"
                    "指定してください。"
                ) from error

        self._timeout = timeout

    def fetch(
        self,
        image_url: str,
    ) -> Path:
        """表紙画像を取得し、キャッシュファイルのパスを返す。

        すでにキャッシュが存在する場合は再取得しない。

        Args:
            image_url:
                表紙画像URL。

        Returns:
            保存済み画像ファイルのパス。

        Raises:
            ValueError:
                URLが空またはHTTP/HTTPSでない場合。
            requests.RequestException:
                画像を取得できない場合。
        """
        normalized_url = image_url.strip()

        if normalized_url == "":
            raise ValueError(
                "表紙画像URLが指定されていません。"
            )

        parsed_url = urlparse(
            normalized_url,
        )

        if parsed_url.scheme not in {
            "http",
            "https",
        }:
            raise ValueError(
                "表紙画像URLが正しくありません。"
            )

        cache_path = self._create_cache_path(
            normalized_url,
        )

        if cache_path.exists():
            return cache_path

        response = self._session.get(
            normalized_url,
            timeout=self._timeout,
        )
        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        )

        if not content_type.lower().startswith(
            "image/"
        ):
            raise ValueError(
                "取得したデータは画像ではありません。"
            )

        self._cache_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        cache_path.write_bytes(
            response.content,
        )

        return cache_path

    def get_cache_status(self) -> CoverCacheStatus:
        """管理対象キャッシュの件数と合計サイズを返す。

        キャッシュディレクトリ直下のファイルだけを対象とし、
        サブディレクトリとその内容は集計しない。

        Raises:
            CoverCacheError:
                キャッシュの列挙またはサイズ取得に失敗した場合。
        """
        cache_files = self._get_cache_files()
        total_size_bytes = 0

        for cache_file in cache_files:
            try:
                total_size_bytes += cache_file.stat().st_size
            except OSError as error:
                raise CoverCacheError(
                    "表紙画像キャッシュの状態を確認できません。"
                ) from error

        return CoverCacheStatus(
            file_count=len(cache_files),
            total_size_bytes=total_size_bytes,
        )

    def clear_cache(self) -> CoverCacheClearResult:
        """管理対象の表紙画像キャッシュを削除する。

        個別ファイルの削除失敗後も残りの処理を継続する。
        キャッシュディレクトリとサブディレクトリは削除しない。

        Raises:
            CoverCacheError:
                キャッシュの列挙または処理後確認に失敗した場合。
        """
        cache_files = self._get_cache_files()
        deleted_count = 0
        deleted_size_bytes = 0
        failed_count = 0

        for cache_file in cache_files:
            try:
                file_size = cache_file.stat().st_size
                cache_file.unlink()
            except OSError:
                failed_count += 1
                logger.warning(
                    "表紙画像キャッシュを削除できませんでした: %s",
                    cache_file,
                    exc_info=True,
                )
                continue

            deleted_count += 1
            deleted_size_bytes += file_size

        remaining_status = self.get_cache_status()

        return CoverCacheClearResult(
            deleted_count=deleted_count,
            deleted_size_bytes=deleted_size_bytes,
            failed_count=failed_count,
            remaining_status=remaining_status,
        )

    def _get_cache_files(self) -> tuple[Path, ...]:
        """キャッシュディレクトリ直下のファイルを返す。"""
        try:
            if not self._cache_directory.exists():
                return ()

            return tuple(
                entry
                for entry in self._cache_directory.iterdir()
                if entry.is_file()
            )
        except OSError as error:
            raise CoverCacheError(
                "表紙画像キャッシュの状態を確認できません。"
            ) from error

    def _create_cache_path(
        self,
        image_url: str,
    ) -> Path:
        """URLからキャッシュファイル名を生成する。"""
        digest = hashlib.sha256(
            image_url.encode("utf-8"),
        ).hexdigest()

        suffix = self._extract_suffix(
            image_url,
        )

        return self._cache_directory / (
            f"{digest}{suffix}"
        )

    def create_stored_path(
        self,
        image_path: Path,
    ) -> str:
        """画像パスをDBへ保存する文字列へ変換する。

        利用者データルートが設定されている場合は、
        そのルートからの相対POSIXパスを返す。

        Args:
            image_path:
                キャッシュ済み表紙画像のパス。

        Returns:
            DBへ保存する表紙画像パス。

        Raises:
            ValueError:
                画像が表紙キャッシュ外にある場合。
        """
        resolved_image_path = Path(
            image_path,
        ).resolve(strict=False)

        if self._root_directory is None:
            return Path(image_path).as_posix()

        self._require_cover_cache_path(
            resolved_image_path,
        )

        return resolved_image_path.relative_to(
            self._root_directory,
        ).as_posix()

    def resolve_stored_path(
        self,
        stored_path: str | None,
    ) -> Path | None:
        """DBの表紙画像パスを表示用のPathへ解決する。

        既存データの絶対パスは互換目的でそのまま扱う。
        相対パスは利用者データルートを基準に解決し、
        表紙キャッシュ外を参照する場合はNoneを返す。
        """
        if stored_path is None:
            return None

        normalized_path = stored_path.strip()

        if not normalized_path:
            return None

        image_path = Path(normalized_path)

        if image_path.is_absolute():
            return image_path.resolve(strict=False)

        if self._root_directory is None:
            return image_path

        resolved_image_path = (
            self._root_directory
            / image_path
        ).resolve(strict=False)

        try:
            self._require_cover_cache_path(
                resolved_image_path,
            )
        except ValueError:
            return None

        return resolved_image_path

    def _require_cover_cache_path(
        self,
        image_path: Path,
    ) -> None:
        """指定パスが表紙キャッシュ配下であることを確認する。"""
        try:
            image_path.relative_to(
                self._cache_directory,
            )
        except ValueError as error:
            raise ValueError(
                "表紙画像パスは表紙キャッシュ内を"
                "指定してください。"
            ) from error

    @staticmethod
    def _extract_suffix(
        image_url: str,
    ) -> str:
        """URLから利用可能な拡張子を取得する。"""
        suffix = Path(
            urlparse(image_url).path
        ).suffix.lower()

        if suffix in {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
        }:
            return suffix

        return ".jpg"
