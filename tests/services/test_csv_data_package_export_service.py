"""Tests for the CsvDataPackageExportService."""

import csv
import zipfile
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from book_manager.models.csv_data_package import (
    BOOK_ITEM_HEADERS,
    BOOK_ITEM_TAGS_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    CSV_ENCODING,
    MANIFEST_FILE_NAME,
    MANIFEST_HEADERS,
    PACKAGE_FORMAT,
    READING_HISTORIES_FILE_NAME,
    CURRENT_REQUIRED_FILE_NAMES as REQUIRED_FILE_NAMES,
    TAGS_FILE_NAME,
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageReadingHistory,
    CsvDataPackageSnapshot,
    CsvDataPackageTag,
)
from book_manager.services.csv_data_package_export_service import (
    CsvDataPackageExportService,
)


FIXED_NOW = datetime(2026, 9, 30, 12, 34, 56)


def create_snapshot() -> CsvDataPackageSnapshot:
    """全CSVの内容を検証できるスナップショットを生成する。"""
    return CsvDataPackageSnapshot(
        book_items=(
            CsvDataPackageBookItem(
                book_key="B000001",
                isbn="9784000000000",
                magazine_code=None,
                title='引用符"と,カンマを含む書籍',
                author="著者\n二行目",
                publisher="出版社",
                publication_format="単行本",
                description="日本語の内容紹介",
                cover_image_url="https://example.com/cover.jpg",
                completion_month="2026-09",
                reading_status="completed",
                is_favorite=True,
                rating=5,
                notes="一行目\n二行目",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-02 11:00:00",
            ),
            CsvDataPackageBookItem(
                book_key="B000002",
                title="任意項目なし",
                reading_status="unread",
                is_favorite=False,
                created_at="2026-09-03 10:00:00",
                updated_at="2026-09-03 10:00:00",
            ),
        ),
        tags=(
            CsvDataPackageTag(
                tag_key="T000001",
                name="技術書",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-01 10:00:00",
            ),
        ),
        book_item_tags=(
            CsvDataPackageBookItemTag(
                book_key="B000001",
                tag_key="T000001",
            ),
        ),
        reading_histories=(
            CsvDataPackageReadingHistory(
                history_key="H000001",
                book_key="B000001",
                started_on="2026-09-01",
                completed_on="2026-09-02",
                notes="読了した。",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-02 11:00:00",
            ),
        ),
    )


def create_service(
    snapshot: CsvDataPackageSnapshot | None = None,
) -> tuple[CsvDataPackageExportService, Mock]:
    """固定日時とVersionを使うテスト用Serviceを生成する。"""
    repository = Mock()
    repository.export_snapshot.return_value = (
        snapshot
        if snapshot is not None
        else create_snapshot()
    )
    service = CsvDataPackageExportService(
        repository,
        now_provider=lambda: FIXED_NOW,
        application_version_provider=lambda: "2.6.0",
        database_schema_version=7,
    )
    return service, repository


def read_csv_from_archive(
    archive_path: Path,
    file_name: str,
) -> list[list[str]]:
    """ZIP内CSVを文字列行として読み込む。"""
    with zipfile.ZipFile(archive_path, "r") as archive:
        with archive.open(file_name, "r") as binary_file:
            with TextIOWrapper(
                binary_file,
                encoding=CSV_ENCODING,
                newline="",
            ) as text_file:
                return list(csv.reader(text_file))


def test_create_default_file_name_uses_current_time() -> None:
    """既定ファイル名へ現在日時を含める。"""
    service, _ = create_service()

    assert (
        service.create_default_file_name()
        == "book_manager_data_20260930_123456.zip"
    )


def test_export_creates_archive_with_required_files(
    tmp_path: Path,
) -> None:
    """ZIP直下へ必須5ファイルだけを固定順で格納する。"""
    service, repository = create_service()
    output_path = tmp_path / "package.zip"

    result = service.export(output_path)

    repository.export_snapshot.assert_called_once_with()
    assert result.output_path == output_path
    with zipfile.ZipFile(output_path, "r") as archive:
        assert tuple(archive.namelist()) == REQUIRED_FILE_NAMES
        assert archive.testzip() is None


def test_export_writes_manifest_from_actual_counts(
    tmp_path: Path,
) -> None:
    """manifestへ識別情報、Version、日時、実件数を出力する。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"

    service.export(output_path)

    rows = read_csv_from_archive(output_path, MANIFEST_FILE_NAME)
    assert rows[0] == list(MANIFEST_HEADERS)
    assert dict(rows[1:]) == {
        "package_format": PACKAGE_FORMAT,
        "format_version": "3",
        "application_version": "2.6.0",
        "database_schema_version": "7",
        "exported_at": "2026-09-30 12:34:56",
        "book_item_count": "2",
        "tag_count": "1",
        "book_item_tag_count": "1",
        "reading_history_count": "1",
        "author_count": "0", "author_alias_count": "0", "book_item_author_count": "0",
    }


def test_export_writes_all_book_fields_and_special_characters(
    tmp_path: Path,
) -> None:
    """書籍の全移行対象とCSV特殊文字を欠落なく出力する。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"

    service.export(output_path)

    rows = read_csv_from_archive(output_path, BOOK_ITEMS_FILE_NAME)
    assert rows[0] == list(BOOK_ITEM_HEADERS)
    assert rows[1] == [
        "B000001",
        "9784000000000",
        "",
        "",
        '引用符"と,カンマを含む書籍',
        "著者\n二行目",
        "出版社",
        "単行本",
        "日本語の内容紹介",
        "https://example.com/cover.jpg",
        "2026-09",
        "読了",
        "はい",
        "5",
        "一行目\n二行目",
        "2026-09-01 10:00:00",
        "2026-09-02 11:00:00",
    ]
    assert rows[2][0] == "B000002"
    assert rows[2][11:14] == ["未読", "いいえ", ""]


def test_export_writes_tags_relations_and_histories(
    tmp_path: Path,
) -> None:
    """タグ、関連、読書履歴をそれぞれのCSVへ出力する。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"

    service.export(output_path)

    tag_rows = read_csv_from_archive(output_path, TAGS_FILE_NAME)
    relation_rows = read_csv_from_archive(
        output_path,
        BOOK_ITEM_TAGS_FILE_NAME,
    )
    history_rows = read_csv_from_archive(
        output_path,
        READING_HISTORIES_FILE_NAME,
    )
    assert tag_rows[1] == [
        "T000001",
        "技術書",
        "2026-09-01 10:00:00",
        "2026-09-01 10:00:00",
    ]
    assert relation_rows[1] == ["B000001", "T000001"]
    assert history_rows[1] == [
        "H000001",
        "B000001",
        "2026-09-01",
        "2026-09-02",
        "読了した。",
        "2026-09-01 10:00:00",
        "2026-09-02 11:00:00",
    ]


def test_export_writes_utf8_bom_to_every_csv(tmp_path: Path) -> None:
    """すべてのCSVをUTF-8 BOM付きで出力する。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"

    service.export(output_path)

    with zipfile.ZipFile(output_path, "r") as archive:
        for file_name in REQUIRED_FILE_NAMES:
            assert archive.read(file_name).startswith(b"\xef\xbb\xbf")


def test_export_accepts_empty_snapshot(tmp_path: Path) -> None:
    """データ0件でもヘッダー付きパッケージを出力する。"""
    service, _ = create_service(CsvDataPackageSnapshot())
    output_path = tmp_path / "empty.zip"

    result = service.export(output_path)

    assert result.book_item_count == 0
    assert result.tag_count == 0
    assert result.book_item_tag_count == 0
    assert result.reading_history_count == 0
    assert read_csv_from_archive(
        output_path,
        BOOK_ITEMS_FILE_NAME,
    ) == [list(BOOK_ITEM_HEADERS)]
    manifest = dict(
        read_csv_from_archive(
            output_path,
            MANIFEST_FILE_NAME,
        )[1:]
    )
    assert manifest["book_item_count"] == "0"
    assert manifest["reading_history_count"] == "0"


def test_export_replaces_existing_output_after_validation(
    tmp_path: Path,
) -> None:
    """自己検査成功後に既存ファイルを置き換える。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"
    output_path.write_bytes(b"old")

    service.export(output_path)

    assert output_path.read_bytes() != b"old"
    with zipfile.ZipFile(output_path, "r") as archive:
        assert archive.testzip() is None


def test_export_preserves_existing_output_when_repository_fails(
    tmp_path: Path,
) -> None:
    """DB読取失敗時に既存ファイルを変更しない。"""
    service, repository = create_service()
    repository.export_snapshot.side_effect = RuntimeError("DB読取失敗")
    output_path = tmp_path / "package.zip"
    output_path.write_bytes(b"old")

    with pytest.raises(RuntimeError, match="DB読取失敗"):
        service.export(output_path)

    assert output_path.read_bytes() == b"old"
    assert not list(
        tmp_path.glob(
            f"{service.TEMPORARY_DIRECTORY_PREFIX}*"
        )
    )


def test_export_preserves_existing_output_when_validation_fails(
    tmp_path: Path,
) -> None:
    """自己検査失敗時に既存ファイルを変更せず一時物を消す。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"
    output_path.write_bytes(b"old")

    with patch.object(
        service,
        "_validate_archive",
        side_effect=ValueError("自己検査失敗"),
    ):
        with pytest.raises(ValueError, match="自己検査失敗"):
            service.export(output_path)

    assert output_path.read_bytes() == b"old"
    assert not list(
        tmp_path.glob(
            f"{service.TEMPORARY_DIRECTORY_PREFIX}*"
        )
    )


def test_export_rejects_missing_output_directory(
    tmp_path: Path,
) -> None:
    """存在しない保存先ではDBを読み取らず失敗する。"""
    service, repository = create_service()
    output_path = tmp_path / "missing" / "package.zip"

    with pytest.raises(FileNotFoundError, match="保存先"):
        service.export(output_path)

    repository.export_snapshot.assert_not_called()


def test_export_result_contains_actual_counts(tmp_path: Path) -> None:
    """結果Modelへ保存先と4種類の実件数を格納する。"""
    service, _ = create_service()
    output_path = tmp_path / "package.zip"

    result = service.export(output_path)

    assert result.output_path == output_path
    assert result.book_item_count == 2
    assert result.tag_count == 1
    assert result.book_item_tag_count == 1
    assert result.reading_history_count == 1
