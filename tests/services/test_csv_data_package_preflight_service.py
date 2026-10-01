"""Tests for the CsvDataPackagePreflightService."""

import csv
import zipfile
from pathlib import Path

import pytest

from book_manager.models.csv_data_package import (
    BOOK_ITEM_HEADERS,
    BOOK_ITEM_TAG_HEADERS,
    BOOK_ITEM_TAGS_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    MANIFEST_FILE_NAME,
    MANIFEST_HEADERS,
    READING_HISTORIES_FILE_NAME,
    READING_HISTORY_HEADERS,
    TAG_HEADERS,
    TAGS_FILE_NAME,
    CsvDataPackageIssueLevel,
)
from book_manager.services.csv_data_package_archive_validator import (
    CsvDataPackageArchiveValidator,
)
from book_manager.services.csv_data_package_preflight_service import (
    CsvDataPackagePreflightService,
)


def valid_rows() -> dict[str, list[list[str]]]:
    """相互参照を含む正常な5ファイル分の行を返す。"""
    return {
        MANIFEST_FILE_NAME: [
            list(MANIFEST_HEADERS),
            ["package_format", "book_manager_csv_package"],
            ["format_version", "1"],
            ["application_version", "2.6.0"],
            ["database_schema_version", "7"],
            ["exported_at", "2026-09-30 13:00:00"],
            ["book_item_count", "1"],
            ["tag_count", "1"],
            ["book_item_tag_count", "1"],
            ["reading_history_count", "1"],
        ],
        BOOK_ITEMS_FILE_NAME: [
            list(BOOK_ITEM_HEADERS),
            [
                "B000001",
                "9784101010014",
                "",
                "テスト書籍",
                "著者",
                "出版社",
                "単行本",
                "内容紹介",
                "https://example.com/cover.jpg",
                "2026-09",
                "読了",
                "はい",
                "5",
                "備考",
                "2026-09-01 10:00:00",
                "2026-09-02 10:00:00",
            ],
        ],
        TAGS_FILE_NAME: [
            list(TAG_HEADERS),
            [
                "T000001",
                "技術書",
                "2026-09-01 10:00:00",
                "2026-09-01 10:00:00",
            ],
        ],
        BOOK_ITEM_TAGS_FILE_NAME: [
            list(BOOK_ITEM_TAG_HEADERS),
            ["B000001", "T000001"],
        ],
        READING_HISTORIES_FILE_NAME: [
            list(READING_HISTORY_HEADERS),
            [
                "H000001",
                "B000001",
                "2026-09-01",
                "2026-09-02",
                "読了した。",
                "2026-09-01 10:00:00",
                "2026-09-02 10:00:00",
            ],
        ],
    }


def write_package(
    path: Path,
    rows_by_file: dict[str, list[list[str]]],
) -> None:
    """UTF-8 BOM付きCSV群をZIPへ書き込む。"""
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file_name, rows in rows_by_file.items():
            text_path = path.parent / file_name
            with text_path.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as file:
                csv.writer(file).writerows(rows)
            archive.write(text_path, arcname=file_name)
            text_path.unlink()


def create_service() -> CsvDataPackagePreflightService:
    """実際のZIP安全検査を使用するServiceを返す。"""
    return CsvDataPackagePreflightService(
        CsvDataPackageArchiveValidator()
    )


def replace_manifest_value(
    rows: dict[str, list[list[str]]],
    key: str,
    value: str,
) -> None:
    """テスト用manifestの値を置き換える。"""
    for row in rows[MANIFEST_FILE_NAME]:
        if row[0] == key:
            row[1] = value
            return
    raise AssertionError(f"manifest key not found: {key}")


def test_preview_accepts_complete_valid_package(tmp_path: Path) -> None:
    """正常な全データを正規化済みModelへ変換する。"""
    path = tmp_path / "package.zip"
    write_package(path, valid_rows())

    preview = create_service().preview(path)

    assert preview.can_import is True
    assert preview.errors == ()
    assert preview.manifest is not None
    assert preview.manifest.application_version == "2.6.0"
    assert len(preview.book_items) == 1
    assert preview.book_items[0].book_key == "B000001"
    assert preview.book_items[0].reading_status == "completed"
    assert preview.book_items[0].is_favorite is True
    assert preview.book_items[0].rating == 5
    assert preview.book_items[0].cover_image_url is not None
    assert preview.tags[0].name == "技術書"
    assert preview.book_item_tags[0].tag_key == "T000001"
    assert preview.reading_histories[0].book_key == "B000001"
    assert len(preview.source_sha256) == 64


def test_preview_accepts_empty_data_files(tmp_path: Path) -> None:
    """件数0のヘッダーだけのデータCSVを受け付ける。"""
    rows = valid_rows()
    for key in (
        "book_item_count",
        "tag_count",
        "book_item_tag_count",
        "reading_history_count",
    ):
        replace_manifest_value(rows, key, "0")
    for file_name in (
        BOOK_ITEMS_FILE_NAME,
        TAGS_FILE_NAME,
        BOOK_ITEM_TAGS_FILE_NAME,
        READING_HISTORIES_FILE_NAME,
    ):
        rows[file_name] = rows[file_name][:1]
    path = tmp_path / "empty.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert preview.can_import is True
    assert preview.book_items == ()
    assert preview.tags == ()
    assert preview.book_item_tags == ()
    assert preview.reading_histories == ()


def test_preview_warns_for_unknown_manifest_key(tmp_path: Path) -> None:
    """未知のmanifest keyを警告して既知項目を読み込む。"""
    rows = valid_rows()
    rows[MANIFEST_FILE_NAME].append(["future_key", "value"])
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert preview.can_import is True
    assert len(preview.warnings) == 1
    assert preview.warnings[0].value == "future_key"


@pytest.mark.parametrize(
    ("file_name", "headers"),
    [
        (MANIFEST_FILE_NAME, MANIFEST_HEADERS),
        (BOOK_ITEMS_FILE_NAME, BOOK_ITEM_HEADERS),
        (TAGS_FILE_NAME, TAG_HEADERS),
        (BOOK_ITEM_TAGS_FILE_NAME, BOOK_ITEM_TAG_HEADERS),
        (READING_HISTORIES_FILE_NAME, READING_HISTORY_HEADERS),
    ],
)
def test_preview_rejects_wrong_header(
    tmp_path: Path,
    file_name: str,
    headers: tuple[str, ...],
) -> None:
    """5ファイルそれぞれのヘッダー不一致をIssueにする。"""
    rows = valid_rows()
    rows[file_name][0] = [*headers[:-1], "不正列"]
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert preview.can_import is False
    assert any(
        issue.file_name == file_name
        and "ヘッダー" in issue.message
        for issue in preview.errors
    )


def test_preview_collects_errors_from_multiple_files(tmp_path: Path) -> None:
    """1件で停止せず複数ファイルの入力エラーを収集する。"""
    rows = valid_rows()
    rows[BOOK_ITEMS_FILE_NAME][1][0] = "invalid"
    rows[TAGS_FILE_NAME][1][1] = ""
    rows[READING_HISTORIES_FILE_NAME][1][2] = "2026/09/01"
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    error_files = {issue.file_name for issue in preview.errors}
    assert BOOK_ITEMS_FILE_NAME in error_files
    assert TAGS_FILE_NAME in error_files
    assert READING_HISTORIES_FILE_NAME in error_files


@pytest.mark.parametrize(
    ("column_index", "value", "column_name"),
    [
        (0, "B000000", "book_key"),
        (1, "invalid", "ISBN"),
        (2, "invalid", "雑誌コード"),
        (3, "", "書籍名"),
        (8, "file:///cover.jpg", "表紙画像URL"),
        (9, "2026-13", "読了年月"),
        (10, "未設定", "読書状態"),
        (11, "true", "お気に入り"),
        (12, "6", "評価"),
        (14, "2026/09/01", "登録日時"),
        (15, "2026-08-01 10:00:00", "更新日時"),
    ],
)
def test_preview_rejects_invalid_book_value(
    tmp_path: Path,
    column_index: int,
    value: str,
    column_name: str,
) -> None:
    """書籍の各重要項目の不正値をIssueにする。"""
    rows = valid_rows()
    rows[BOOK_ITEMS_FILE_NAME][1][column_index] = value
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        issue.file_name == BOOK_ITEMS_FILE_NAME
        and issue.column_name == column_name
        for issue in preview.errors
    )


@pytest.mark.parametrize(
    ("file_name", "row", "column_name"),
    [
        (
            BOOK_ITEMS_FILE_NAME,
            [
                "B000001",
                "9784101010014",
                "",
                "重複書籍",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "2026-09-01 10:00:00",
                "2026-09-01 10:00:00",
            ],
            "book_key",
        ),
        (
            TAGS_FILE_NAME,
            [
                "T000002",
                "技術書",
                "2026-09-01 10:00:00",
                "2026-09-01 10:00:00",
            ],
            "タグ名",
        ),
        (
            BOOK_ITEM_TAGS_FILE_NAME,
            ["B000001", "T000001"],
            None,
        ),
        (
            READING_HISTORIES_FILE_NAME,
            [
                "H000001",
                "B000001",
                "",
                "",
                "再読",
                "2026-09-03 10:00:00",
                "2026-09-03 10:00:00",
            ],
            "history_key",
        ),
    ],
)
def test_preview_rejects_duplicate_value(
    tmp_path: Path,
    file_name: str,
    row: list[str],
    column_name: str | None,
) -> None:
    """キー、タグ名、関連の重複をIssueにする。"""
    rows = valid_rows()
    rows[file_name].append(row)
    manifest_key = {
        BOOK_ITEMS_FILE_NAME: "book_item_count",
        TAGS_FILE_NAME: "tag_count",
        BOOK_ITEM_TAGS_FILE_NAME: "book_item_tag_count",
        READING_HISTORIES_FILE_NAME: "reading_history_count",
    }[file_name]
    replace_manifest_value(rows, manifest_key, "2")
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        issue.file_name == file_name
        and issue.column_name == column_name
        and "重複" in issue.message
        for issue in preview.errors
    )


@pytest.mark.parametrize(
    ("file_name", "column_index", "missing_key", "column_name"),
    [
        (BOOK_ITEM_TAGS_FILE_NAME, 0, "B999999", "book_key"),
        (BOOK_ITEM_TAGS_FILE_NAME, 1, "T999999", "tag_key"),
        (READING_HISTORIES_FILE_NAME, 1, "B999999", "book_key"),
    ],
)
def test_preview_rejects_missing_reference(
    tmp_path: Path,
    file_name: str,
    column_index: int,
    missing_key: str,
    column_name: str,
) -> None:
    """関連先ファイルに存在しないキー参照をIssueにする。"""
    rows = valid_rows()
    rows[file_name][1][column_index] = missing_key
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        issue.file_name == file_name
        and issue.column_name == column_name
        and "存在しません" in issue.message
        for issue in preview.errors
    )


@pytest.mark.parametrize(
    ("column_index", "value", "column_name"),
    [
        (0, "H000000", "history_key"),
        (2, "2026/09/01", "読書開始日"),
        (3, "2026-09-00", "読了日"),
        (5, "", "登録日時"),
        (6, "2026-08-01 10:00:00", "更新日時"),
    ],
)
def test_preview_rejects_invalid_history_value(
    tmp_path: Path,
    column_index: int,
    value: str,
    column_name: str,
) -> None:
    """読書履歴の日付、日時、キーの不正値をIssueにする。"""
    rows = valid_rows()
    rows[READING_HISTORIES_FILE_NAME][1][column_index] = value
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        issue.file_name == READING_HISTORIES_FILE_NAME
        and issue.column_name == column_name
        for issue in preview.errors
    )


def test_preview_rejects_empty_history(tmp_path: Path) -> None:
    """日付とメモがすべて空の読書履歴を拒否する。"""
    rows = valid_rows()
    rows[READING_HISTORIES_FILE_NAME][1][2:5] = ["", "", ""]
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        "日付またはメモ" in issue.message
        for issue in preview.errors
    )


def test_preview_rejects_reversed_history_dates(tmp_path: Path) -> None:
    """開始日が読了日より後の読書履歴を拒否する。"""
    rows = valid_rows()
    rows[READING_HISTORIES_FILE_NAME][1][2] = "2026-09-03"
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        "開始日は読了日以前" in issue.message
        for issue in preview.errors
    )


def test_preview_rejects_manifest_count_mismatch(tmp_path: Path) -> None:
    """manifest件数とCSV物理行数の不一致を拒否する。"""
    rows = valid_rows()
    replace_manifest_value(rows, "book_item_count", "2")
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert any(
        issue.file_name == MANIFEST_FILE_NAME
        and issue.column_name == "book_item_count"
        and "実件数" in issue.message
        for issue in preview.errors
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("package_format", "other"),
        ("format_version", "2"),
        ("application_version", ""),
        ("database_schema_version", "0"),
        ("exported_at", "2026/09/30"),
        ("tag_count", "-1"),
    ],
)
def test_preview_rejects_invalid_manifest_value(
    tmp_path: Path,
    key: str,
    value: str,
) -> None:
    """manifestの識別値、Version、日時、件数を検査する。"""
    rows = valid_rows()
    replace_manifest_value(rows, key, value)
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert preview.manifest is None
    assert preview.can_import is False
    assert any(issue.column_name == key for issue in preview.errors)


def test_preview_rejects_missing_manifest_key(tmp_path: Path) -> None:
    """manifestの必須key不足をIssueにする。"""
    rows = valid_rows()
    rows[MANIFEST_FILE_NAME] = [
        row
        for row in rows[MANIFEST_FILE_NAME]
        if not row or row[0] != "application_version"
    ]
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert preview.manifest is None
    assert any(
        issue.value == "application_version"
        and "必須key" in issue.message
        for issue in preview.errors
    )


def test_preview_reports_file_row_column_and_value(tmp_path: Path) -> None:
    """Issueに問題箇所を特定できる情報を保持する。"""
    rows = valid_rows()
    rows[BOOK_ITEMS_FILE_NAME][1][12] = "9"
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    issue = next(
        issue
        for issue in preview.errors
        if issue.column_name == "評価"
    )
    assert issue.level is CsvDataPackageIssueLevel.ERROR
    assert issue.file_name == BOOK_ITEMS_FILE_NAME
    assert issue.row_number == 2
    assert issue.value == "9"


@pytest.mark.parametrize("identifier_column", ["ISBN", "雑誌コード"])
def test_preview_preserves_duplicate_identifiers_and_empty_status(
    tmp_path: Path,
    identifier_column: str,
) -> None:
    """識別コードが同じ別書籍と空の読書状態を欠落させない。"""
    rows = valid_rows()
    first = rows[BOOK_ITEMS_FILE_NAME][1]
    index = list(BOOK_ITEM_HEADERS).index(identifier_column)
    first[index] = "9784101010014" if identifier_column == "ISBN" else "12345"
    first[list(BOOK_ITEM_HEADERS).index("読書状態")] = ""
    second = first.copy()
    second[0] = "B000002"
    rows[BOOK_ITEMS_FILE_NAME].append(second)
    rows[BOOK_ITEM_TAGS_FILE_NAME].append(["B000002", "T000001"])
    history = rows[READING_HISTORIES_FILE_NAME][1].copy()
    history[0:2] = ["H000002", "B000002"]
    rows[READING_HISTORIES_FILE_NAME].append(history)
    replace_manifest_value(rows, "book_item_count", "2")
    replace_manifest_value(rows, "book_item_tag_count", "2")
    replace_manifest_value(rows, "reading_history_count", "2")
    path = tmp_path / "package.zip"
    write_package(path, rows)

    preview = create_service().preview(path)

    assert not preview.errors
    assert len(preview.book_items) == 2
    assert all(book.reading_status is None for book in preview.book_items)
    assert len(preview.book_item_tags) == 2
    assert len(preview.reading_histories) == 2
