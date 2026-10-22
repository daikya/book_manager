"""CSV data package models and format constants tests."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from book_manager.models.csv_data_package import (
    BOOLEAN_FALSE_TEXT,
    BOOLEAN_TRUE_TEXT,
    BOOK_ITEM_HEADERS,
    BOOK_ITEM_TAG_HEADERS,
    BOOK_ITEM_TAGS_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    BOOK_KEY_PREFIX,
    CSV_ENCODING,
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageImportResult,
    CsvDataPackageIssue,
    CsvDataPackageIssueLevel,
    CsvDataPackageManifest,
    CsvDataPackagePreview,
    CsvDataPackageReadingHistory,
    CsvDataPackageTag,
    DATETIME_FORMAT,
    DATE_FORMAT,
    HISTORY_KEY_PREFIX,
    MANIFEST_FILE_NAME,
    MANIFEST_HEADERS,
    MANIFEST_REQUIRED_KEYS,
    PACKAGE_FORMAT,
    PACKAGE_FORMAT_VERSION,
    READING_HISTORIES_FILE_NAME,
    READING_HISTORY_HEADERS,
    REQUIRED_FILE_NAMES,
    TAG_HEADERS,
    TAG_KEY_PREFIX,
    TAGS_FILE_NAME,
    create_package_key,
    is_valid_package_key,
)


def create_manifest(**overrides: object) -> CsvDataPackageManifest:
    """テスト用manifestを生成する。"""
    values: dict[str, object] = {
        "application_version": "2.6.0",
        "database_schema_version": 7,
        "exported_at": "2026-09-30 12:00:00",
        "book_item_count": 2,
        "tag_count": 3,
        "book_item_tag_count": 4,
        "reading_history_count": 5,
    }
    values.update(overrides)
    return CsvDataPackageManifest(**values)  # type: ignore[arg-type]


def create_preview(
    *,
    manifest: CsvDataPackageManifest | None = None,
    issues: tuple[CsvDataPackageIssue, ...] = (),
) -> CsvDataPackagePreview:
    """テスト用プレビューを生成する。"""
    return CsvDataPackagePreview(
        source_path=Path("package.zip"),
        source_size=123,
        source_modified_ns=456,
        source_sha256="a" * 64,
        manifest=manifest,
        issues=issues,
    )


def test_package_format_constants() -> None:
    """パッケージ形式の識別値を固定する。"""
    assert PACKAGE_FORMAT == "book_manager_csv_package"
    assert PACKAGE_FORMAT_VERSION == 3
    assert CSV_ENCODING == "utf-8-sig"
    assert DATE_FORMAT == "%Y-%m-%d"
    assert DATETIME_FORMAT == "%Y-%m-%d %H:%M:%S"
    assert BOOLEAN_TRUE_TEXT == "はい"
    assert BOOLEAN_FALSE_TEXT == "いいえ"


def test_required_file_names_are_fixed() -> None:
    """ZIP直下の必須ファイル名を固定する。"""
    assert REQUIRED_FILE_NAMES == (
        MANIFEST_FILE_NAME,
        BOOK_ITEMS_FILE_NAME,
        TAGS_FILE_NAME,
        BOOK_ITEM_TAGS_FILE_NAME,
        READING_HISTORIES_FILE_NAME,
    )
    assert len(REQUIRED_FILE_NAMES) == len(set(REQUIRED_FILE_NAMES)) == 5


def test_csv_headers_are_fixed() -> None:
    """各CSVのヘッダーと列順を固定する。"""
    assert MANIFEST_HEADERS == ("key", "value")
    assert BOOK_ITEM_HEADERS == (
        "book_key",
        "ISBN",
        "参照ISBN",
        "雑誌コード",
        "書籍名",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",
        "表紙画像URL",
        "読了年月",
        "読書状態",
        "お気に入り",
        "評価",
        "備考",
        "登録日時",
        "更新日時",
    )
    assert TAG_HEADERS == (
        "tag_key",
        "タグ名",
        "登録日時",
        "更新日時",
    )
    assert BOOK_ITEM_TAG_HEADERS == ("book_key", "tag_key")
    assert READING_HISTORY_HEADERS == (
        "history_key",
        "book_key",
        "読書開始日",
        "読了日",
        "読書メモ",
        "登録日時",
        "更新日時",
    )


def test_manifest_required_keys_are_fixed() -> None:
    """manifestの必須keyを固定する。"""
    assert MANIFEST_REQUIRED_KEYS == (
        "package_format",
        "format_version",
        "application_version",
        "database_schema_version",
        "exported_at",
        "book_item_count",
        "tag_count",
        "book_item_tag_count",
        "reading_history_count",
    )


@pytest.mark.parametrize(
    ("prefix", "sequence", "expected"),
    [
        (BOOK_KEY_PREFIX, 1, "B000001"),
        (TAG_KEY_PREFIX, 42, "T000042"),
        (HISTORY_KEY_PREFIX, 999999, "H999999"),
        (BOOK_KEY_PREFIX, 1000000, "B1000000"),
    ],
)
def test_create_package_key(
    prefix: str,
    sequence: int,
    expected: str,
) -> None:
    """種別と連番から固定幅以上のキーを生成する。"""
    assert create_package_key(prefix, sequence) == expected


@pytest.mark.parametrize("prefix", ["", "X", "b", "BT"])
def test_create_package_key_rejects_unknown_prefix(prefix: str) -> None:
    """未対応のキー種別を拒否する。"""
    with pytest.raises(ValueError, match="未対応"):
        create_package_key(prefix, 1)


@pytest.mark.parametrize("sequence", [0, -1, -999])
def test_create_package_key_rejects_non_positive_sequence(
    sequence: int,
) -> None:
    """0以下の連番を拒否する。"""
    with pytest.raises(ValueError, match="1以上"):
        create_package_key(BOOK_KEY_PREFIX, sequence)


@pytest.mark.parametrize(
    ("value", "prefix"),
    [
        ("B000001", BOOK_KEY_PREFIX),
        ("T000001", TAG_KEY_PREFIX),
        ("H000001", HISTORY_KEY_PREFIX),
        ("B1000000", BOOK_KEY_PREFIX),
    ],
)
def test_is_valid_package_key_accepts_valid_key(
    value: str,
    prefix: str,
) -> None:
    """正しい種別と6桁以上の連番を受け付ける。"""
    assert is_valid_package_key(value, prefix) is True


@pytest.mark.parametrize(
    ("value", "prefix"),
    [
        ("B000001", TAG_KEY_PREFIX),
        ("B00001", BOOK_KEY_PREFIX),
        ("B000000", BOOK_KEY_PREFIX),
        ("B-00001", BOOK_KEY_PREFIX),
        ("b000001", BOOK_KEY_PREFIX),
        ("B１２３４５６", BOOK_KEY_PREFIX),
        ("", BOOK_KEY_PREFIX),
        ("B000001", "X"),
    ],
)
def test_is_valid_package_key_rejects_invalid_key(
    value: str,
    prefix: str,
) -> None:
    """形式または種別が異なるキーを拒否する。"""
    assert is_valid_package_key(value, prefix) is False


def test_manifest_accepts_zero_counts() -> None:
    """全データ0件のmanifestを表現できる。"""
    manifest = create_manifest(
        book_item_count=0,
        tag_count=0,
        book_item_tag_count=0,
        reading_history_count=0,
    )

    assert manifest.package_format == PACKAGE_FORMAT
    assert manifest.format_version == PACKAGE_FORMAT_VERSION
    assert manifest.book_item_count == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("package_format", "other", "パッケージ形式"),
        ("format_version", 4, "形式Version"),
        ("application_version", "  ", "アプリケーションVersion"),
        ("database_schema_version", 0, "DBスキーマVersion"),
        ("exported_at", "", "エクスポート日時"),
        ("book_item_count", -1, "負の値"),
        ("tag_count", -1, "負の値"),
        ("book_item_tag_count", -1, "負の値"),
        ("reading_history_count", -1, "負の値"),
    ],
)
def test_manifest_rejects_invalid_basic_value(
    field: str,
    value: object,
    message: str,
) -> None:
    """manifestの識別値と件数の不整合を拒否する。"""
    with pytest.raises(ValueError, match=message):
        create_manifest(**{field: value})


def test_data_row_models_preserve_normalized_values() -> None:
    """4データCSVの正規化済み値を保持する。"""
    book = CsvDataPackageBookItem(
        book_key="B000001",
        isbn="9784000000000",
        magazine_code=None,
        title="テスト書籍",
        author="著者",
        publisher="出版社",
        publication_format="単行本",
        description="紹介",
        cover_image_url="https://example.com/cover.jpg",
        completion_month="2026-09",
        reading_status="読了",
        is_favorite=True,
        rating=5,
        notes="備考",
        created_at="2026-09-01 10:00:00",
        updated_at="2026-09-02 11:00:00",
    )
    tag = CsvDataPackageTag(
        tag_key="T000001",
        name="技術書",
        created_at="2026-09-01 10:00:00",
        updated_at="2026-09-01 10:00:00",
    )
    relation = CsvDataPackageBookItemTag(
        book_key="B000001",
        tag_key="T000001",
    )
    history = CsvDataPackageReadingHistory(
        history_key="H000001",
        book_key="B000001",
        started_on="2026-09-01",
        completed_on="2026-09-07",
        notes="読了した。",
        created_at="2026-09-01 10:00:00",
        updated_at="2026-09-07 20:00:00",
    )

    assert book.cover_image_url == "https://example.com/cover.jpg"
    assert book.is_favorite is True
    assert tag.name == "技術書"
    assert relation == CsvDataPackageBookItemTag("B000001", "T000001")
    assert history.completed_on == "2026-09-07"


def test_models_are_immutable() -> None:
    """検査済みデータが実行前に書き換わらない。"""
    manifest = create_manifest()

    with pytest.raises(FrozenInstanceError):
        manifest.book_item_count = 100  # type: ignore[misc]


def test_preview_separates_warnings_and_errors() -> None:
    """プレビューから警告とエラーを分けて取得する。"""
    warning = CsvDataPackageIssue(
        level=CsvDataPackageIssueLevel.WARNING,
        file_name=MANIFEST_FILE_NAME,
        message="未知のkeyを無視します。",
    )
    error = CsvDataPackageIssue(
        level=CsvDataPackageIssueLevel.ERROR,
        file_name=BOOK_ITEMS_FILE_NAME,
        row_number=3,
        column_name="評価",
        value="6",
        message="評価は1～5で入力してください。",
    )
    preview = create_preview(
        manifest=create_manifest(),
        issues=(warning, error),
    )

    assert preview.warnings == (warning,)
    assert preview.errors == (error,)
    assert preview.can_import is False


def test_preview_can_import_with_manifest_and_warnings_only() -> None:
    """manifestがあり警告だけなら実行可能とする。"""
    warning = CsvDataPackageIssue(
        level=CsvDataPackageIssueLevel.WARNING,
        file_name=MANIFEST_FILE_NAME,
        message="未知のkeyを無視します。",
    )
    preview = create_preview(
        manifest=create_manifest(),
        issues=(warning,),
    )

    assert preview.can_import is True


def test_preview_cannot_import_without_manifest() -> None:
    """Issueがなくてもmanifestを読めなければ実行不可とする。"""
    preview = create_preview(manifest=None)

    assert preview.errors == ()
    assert preview.can_import is False


def test_import_result_preserves_counts_and_backup_path() -> None:
    """インポート結果に全件数とバックアップ先を保持する。"""
    result = CsvDataPackageImportResult(
        book_item_count=10,
        tag_count=3,
        book_item_tag_count=8,
        reading_history_count=6,
        backup_path=Path("backup.db"),
    )

    assert result.book_item_count == 10
    assert result.tag_count == 3
    assert result.book_item_tag_count == 8
    assert result.reading_history_count == 6
    assert result.backup_path == Path("backup.db")
