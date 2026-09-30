"""Structural and security validation for CSV data package archives."""

from __future__ import annotations

import hashlib
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from book_manager.models.csv_data_package import (
    REQUIRED_FILE_NAMES,
    CsvDataPackageArchiveFingerprint,
)


class CsvDataPackageArchiveValidator:
    """ZIPを展開せず構造と安全性を検査する。"""

    DEFAULT_MAX_ENTRY_COUNT = len(REQUIRED_FILE_NAMES)
    DEFAULT_MAX_ENTRY_SIZE = 64 * 1024 * 1024
    DEFAULT_MAX_TOTAL_SIZE = 128 * 1024 * 1024
    DEFAULT_MAX_COMPRESSION_RATIO = 200.0
    HASH_CHUNK_SIZE = 1024 * 1024

    _DRIVE_PATH_PATTERN = re.compile(r"^[A-Za-z]:")

    def __init__(
        self,
        *,
        max_entry_count: int = DEFAULT_MAX_ENTRY_COUNT,
        max_entry_size: int = DEFAULT_MAX_ENTRY_SIZE,
        max_total_size: int = DEFAULT_MAX_TOTAL_SIZE,
        max_compression_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO,
    ) -> None:
        """検査上限を保持する。"""
        if max_entry_count < 1:
            raise ValueError(
                "ZIPエントリ数の上限は1以上である必要があります。"
            )
        if max_entry_size < 1:
            raise ValueError(
                "ZIP内ファイルサイズの上限が正しくありません。"
            )
        if max_total_size < 1:
            raise ValueError(
                "ZIP合計サイズの上限が正しくありません。"
            )
        if max_compression_ratio <= 1:
            raise ValueError(
                "ZIP圧縮率の上限は1より大きい必要があります。"
            )

        self._max_entry_count = max_entry_count
        self._max_entry_size = max_entry_size
        self._max_total_size = max_total_size
        self._max_compression_ratio = max_compression_ratio

    def validate(
        self,
        source_path: Path | str,
    ) -> CsvDataPackageArchiveFingerprint:
        """ZIP構造を検査してファイルの指紋を返す。"""
        resolved_source_path = Path(source_path)

        if not resolved_source_path.exists():
            raise FileNotFoundError(
                "CSVデータパッケージが見つかりません。"
            )
        if not resolved_source_path.is_file():
            raise ValueError(
                "CSVデータパッケージにはファイルを"
                "指定してください。"
            )
        if not zipfile.is_zipfile(resolved_source_path):
            raise ValueError(
                "CSVデータパッケージがZIP形式ではありません。"
            )

        try:
            with zipfile.ZipFile(resolved_source_path, "r") as archive:
                self._validate_entries(archive)

                bad_file = archive.testzip()
                if bad_file is not None:
                    raise ValueError(
                        "CSVデータパッケージ内のファイルが"
                        f"破損しています: {bad_file}"
                    )
        except zipfile.BadZipFile as error:
            raise ValueError(
                "CSVデータパッケージが破損しています。"
            ) from error

        file_status = resolved_source_path.stat()
        return CsvDataPackageArchiveFingerprint(
            source_path=resolved_source_path,
            source_size=file_status.st_size,
            source_modified_ns=file_status.st_mtime_ns,
            source_sha256=self._calculate_sha256(resolved_source_path),
        )

    def _validate_entries(self, archive: zipfile.ZipFile) -> None:
        """ZIP内エントリの構成と属性を検査する。"""
        entries = archive.infolist()
        if len(entries) > self._max_entry_count:
            raise ValueError(
                "CSVデータパッケージ内のファイル数が"
                "上限を超えています。"
            )

        total_size = 0
        names: list[str] = []

        for entry in entries:
            self._validate_entry_path(entry)
            self._validate_entry_type(entry)
            self._validate_entry_size(entry)
            total_size += entry.file_size
            if total_size > self._max_total_size:
                raise ValueError(
                    "CSVデータパッケージの展開後合計サイズが"
                    "上限を超えています。"
                )
            names.append(entry.filename)

        if len(names) != len(set(names)):
            raise ValueError(
                "CSVデータパッケージ内に同名ファイルが"
                "重複しています。"
            )

        actual_names = set(names)
        required_names = set(REQUIRED_FILE_NAMES)
        missing_names = required_names - actual_names
        extra_names = actual_names - required_names

        if missing_names:
            missing_text = ", ".join(sorted(missing_names))
            raise ValueError(
                "CSVデータパッケージに必須ファイルがありません: "
                f"{missing_text}"
            )
        if extra_names:
            extra_text = ", ".join(sorted(extra_names))
            raise ValueError(
                "CSVデータパッケージに未対応の"
                "ファイルがあります: "
                f"{extra_text}"
            )

    @classmethod
    def _validate_entry_path(cls, entry: zipfile.ZipInfo) -> None:
        """ZIPエントリが直下の安全なファイル名か検査する。"""
        name = entry.filename
        path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or name.startswith("/")
            or cls._DRIVE_PATH_PATTERN.match(name) is not None
            or path.is_absolute()
            or len(path.parts) != 1
            or any(part in {".", ".."} for part in path.parts)
        ):
            raise ValueError(
                "CSVデータパッケージ内に危険なパスがあります: "
                f"{name}"
            )

    @staticmethod
    def _validate_entry_type(entry: zipfile.ZipInfo) -> None:
        """ディレクトリ、暗号化、特殊ファイルを拒否する。"""
        if entry.is_dir():
            raise ValueError(
                "CSVデータパッケージ内にディレクトリがあります: "
                f"{entry.filename}"
            )
        if entry.flag_bits & 0x1:
            raise ValueError(
                "暗号化されたZIPエントリには対応していません: "
                f"{entry.filename}"
            )

        if entry.create_system != 3:
            return

        file_type = stat.S_IFMT(entry.external_attr >> 16)
        if file_type not in {0, stat.S_IFREG}:
            raise ValueError(
                "CSVデータパッケージ内に特殊ファイルがあります: "
                f"{entry.filename}"
            )

    def _validate_entry_size(self, entry: zipfile.ZipInfo) -> None:
        """展開後サイズと圧縮率を検査する。"""
        if entry.file_size > self._max_entry_size:
            raise ValueError(
                "CSVデータパッケージ内ファイルの展開後サイズが"
                f"上限を超えています: {entry.filename}"
            )
        if entry.file_size == 0:
            return
        if entry.compress_size == 0:
            raise ValueError(
                "CSVデータパッケージ内ファイルの圧縮率が"
                f"正しくありません: {entry.filename}"
            )

        compression_ratio = entry.file_size / entry.compress_size
        if compression_ratio > self._max_compression_ratio:
            raise ValueError(
                "CSVデータパッケージ内ファイルの圧縮率が"
                f"上限を超えています: {entry.filename}"
            )

    @classmethod
    def _calculate_sha256(cls, path: Path) -> str:
        """ファイルのSHA-256を計算する。"""
        digest = hashlib.sha256()
        with path.open("rb") as file:
            while chunk := file.read(cls.HASH_CHUNK_SIZE):
                digest.update(chunk)
        return digest.hexdigest()
