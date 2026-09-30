"""Tests for the CsvDataPackageArchiveValidator."""

import hashlib
import stat
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from book_manager.models.csv_data_package import REQUIRED_FILE_NAMES
from book_manager.services.csv_data_package_archive_validator import (
    CsvDataPackageArchiveValidator,
)


def create_archive(
    path: Path,
    *,
    names: tuple[str, ...] = REQUIRED_FILE_NAMES,
    content: bytes = b"header\r\n",
    compression: int = zipfile.ZIP_DEFLATED,
) -> None:
    """指定エントリを持つテスト用ZIPを作成する。"""
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name in names:
            archive.writestr(name, content)


def test_validate_returns_file_fingerprint(tmp_path: Path) -> None:
    """正常なZIPを検査して同一性確認用の情報を返す。"""
    path = tmp_path / "package.zip"
    create_archive(path)
    expected_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    result = CsvDataPackageArchiveValidator().validate(path)

    status = path.stat()
    assert result.source_path == path
    assert result.source_size == status.st_size
    assert result.source_modified_ns == status.st_mtime_ns
    assert result.source_sha256 == expected_hash


def test_validate_accepts_string_path(tmp_path: Path) -> None:
    """文字列のファイルパスを受け付ける。"""
    path = tmp_path / "package.zip"
    create_archive(path)

    result = CsvDataPackageArchiveValidator().validate(str(path))

    assert result.source_path == path


def test_validate_rejects_missing_file(tmp_path: Path) -> None:
    """存在しないZIPを拒否する。"""
    path = tmp_path / "missing.zip"

    with pytest.raises(FileNotFoundError, match="見つかりません"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_directory(tmp_path: Path) -> None:
    """ディレクトリ指定を拒否する。"""
    with pytest.raises(ValueError, match="ファイルを指定"):
        CsvDataPackageArchiveValidator().validate(tmp_path)


def test_validate_rejects_non_zip_file(tmp_path: Path) -> None:
    """ZIPではないファイルを拒否する。"""
    path = tmp_path / "not_zip.zip"
    path.write_text("not zip", encoding="utf-8")

    with pytest.raises(ValueError, match="ZIP形式"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_missing_required_file(tmp_path: Path) -> None:
    """必須ファイルが不足するZIPを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, names=REQUIRED_FILE_NAMES[:-1])

    with pytest.raises(ValueError, match="必須ファイル"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_extra_file(tmp_path: Path) -> None:
    """未対応の追加ファイルを拒否する。"""
    path = tmp_path / "package.zip"
    validator = CsvDataPackageArchiveValidator(max_entry_count=6)
    create_archive(path, names=REQUIRED_FILE_NAMES + ("extra.csv",))

    with pytest.raises(ValueError, match="未対応のファイル"):
        validator.validate(path)


def test_validate_rejects_too_many_entries(tmp_path: Path) -> None:
    """エントリ数上限を超えるZIPを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, names=REQUIRED_FILE_NAMES + ("extra.csv",))

    with pytest.raises(ValueError, match="ファイル数"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_duplicate_file_name(tmp_path: Path) -> None:
    """同名エントリを持つZIPを拒否する。"""
    path = tmp_path / "package.zip"
    validator = CsvDataPackageArchiveValidator(max_entry_count=6)
    with zipfile.ZipFile(path, "w") as archive:
        for name in REQUIRED_FILE_NAMES:
            archive.writestr(name, b"header\r\n")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(REQUIRED_FILE_NAMES[0], b"duplicate")

    with pytest.raises(ValueError, match="重複"):
        validator.validate(path)


@pytest.mark.parametrize(
    "dangerous_name",
    [
        "../manifest.csv",
        "directory/manifest.csv",
        "/manifest.csv",
        "C:/manifest.csv",
        "directory\\manifest.csv",
    ],
)
def test_validate_rejects_dangerous_path(
    tmp_path: Path,
    dangerous_name: str,
) -> None:
    """直下ファイルではない危険なパスを拒否する。"""
    path = tmp_path / "package.zip"
    names = (dangerous_name,) + REQUIRED_FILE_NAMES[1:]
    create_archive(path, names=names)

    with pytest.raises(ValueError, match="危険なパス"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_directory_entry(tmp_path: Path) -> None:
    """ディレクトリエントリを拒否する。"""
    path = tmp_path / "package.zip"
    validator = CsvDataPackageArchiveValidator(max_entry_count=6)
    with zipfile.ZipFile(path, "w") as archive:
        for name in REQUIRED_FILE_NAMES:
            archive.writestr(name, b"header\r\n")
        archive.writestr("directory/", b"")

    with pytest.raises(ValueError, match="危険なパス|ディレクトリ"):
        validator.validate(path)


def test_validate_rejects_symbolic_link(tmp_path: Path) -> None:
    """Unixシンボリックリンクのエントリを拒否する。"""
    path = tmp_path / "package.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name in REQUIRED_FILE_NAMES[1:]:
            archive.writestr(name, b"header\r\n")
        link = zipfile.ZipInfo(REQUIRED_FILE_NAMES[0])
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, b"target")

    with pytest.raises(ValueError, match="特殊ファイル"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_encrypted_entry(tmp_path: Path) -> None:
    """暗号化フラグを持つエントリを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, compression=zipfile.ZIP_STORED)
    content = bytearray(path.read_bytes())

    local_header = content.find(b"PK\x03\x04")
    central_header = content.find(b"PK\x01\x02")
    assert local_header >= 0
    assert central_header >= 0
    content[local_header + 6] |= 0x01
    content[central_header + 8] |= 0x01
    path.write_bytes(content)

    with pytest.raises(ValueError, match="暗号化"):
        CsvDataPackageArchiveValidator().validate(path)


def test_validate_rejects_large_entry(tmp_path: Path) -> None:
    """個別の展開後サイズ上限を超えるファイルを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, content=b"12345")
    validator = CsvDataPackageArchiveValidator(max_entry_size=4)

    with pytest.raises(ValueError, match="ファイルの展開後サイズ"):
        validator.validate(path)


def test_validate_rejects_large_total_size(tmp_path: Path) -> None:
    """展開後合計サイズ上限を超えるZIPを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, content=b"12345")
    validator = CsvDataPackageArchiveValidator(max_total_size=20)

    with pytest.raises(ValueError, match="合計サイズ"):
        validator.validate(path)


def test_validate_rejects_excessive_compression_ratio(
    tmp_path: Path,
) -> None:
    """異常に高い圧縮率のファイルを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path, content=b"A" * 10_000)
    validator = CsvDataPackageArchiveValidator(
        max_compression_ratio=2,
    )

    with pytest.raises(ValueError, match="圧縮率"):
        validator.validate(path)


def test_validate_rejects_crc_failure(tmp_path: Path) -> None:
    """CRC検査で破損が判明したZIPを拒否する。"""
    path = tmp_path / "package.zip"
    create_archive(path)

    with patch.object(
        zipfile.ZipFile,
        "testzip",
        return_value=REQUIRED_FILE_NAMES[0],
    ):
        with pytest.raises(ValueError, match="破損"):
            CsvDataPackageArchiveValidator().validate(path)


@pytest.mark.parametrize(
    ("keyword", "value", "message"),
    [
        ("max_entry_count", 0, "エントリ数"),
        ("max_entry_size", 0, "ファイルサイズ"),
        ("max_total_size", 0, "合計サイズ"),
        ("max_compression_ratio", 1, "圧縮率"),
    ],
)
def test_validator_rejects_invalid_limit(
    keyword: str,
    value: int,
    message: str,
) -> None:
    """0以下などの無効な検査上限を拒否する。"""
    with pytest.raises(ValueError, match=message):
        CsvDataPackageArchiveValidator(**{keyword: value})
