"""表紙画像の取得とキャッシュを担当するService。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests import Session


class CoverImageService:
    """表紙画像を取得してローカルへ保存する。"""

    def __init__(
        self,
        *,
        session: Session,
        cache_directory: Path,
        timeout: tuple[int, int] = (5, 10),
    ) -> None:
        """Serviceを初期化する。

        Args:
            session:
                HTTP通信に使用するSession。
            cache_directory:
                表紙画像の保存先。
            timeout:
                接続・読み込みtimeout。
        """
        self._session = session
        self._cache_directory = cache_directory
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