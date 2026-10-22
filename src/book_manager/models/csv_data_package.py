"""CSV data package models and format constants."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


PACKAGE_FORMAT = "book_manager_csv_package"
PACKAGE_FORMAT_VERSION = 3
SUPPORTED_PACKAGE_FORMAT_VERSIONS = (1, 2, 3)

MANIFEST_FILE_NAME = "manifest.csv"
BOOK_ITEMS_FILE_NAME = "book_items.csv"
TAGS_FILE_NAME = "tags.csv"
BOOK_ITEM_TAGS_FILE_NAME = "book_item_tags.csv"
READING_HISTORIES_FILE_NAME = "reading_histories.csv"

REQUIRED_FILE_NAMES = (
    MANIFEST_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    TAGS_FILE_NAME,
    BOOK_ITEM_TAGS_FILE_NAME,
    READING_HISTORIES_FILE_NAME,
)

AUTHORS_FILE_NAME = "authors.csv"
AUTHOR_ALIASES_FILE_NAME = "author_aliases.csv"
BOOK_ITEM_AUTHORS_FILE_NAME = "book_item_authors.csv"
AUTHOR_FILE_NAMES = (AUTHORS_FILE_NAME, AUTHOR_ALIASES_FILE_NAME, BOOK_ITEM_AUTHORS_FILE_NAME)
CURRENT_REQUIRED_FILE_NAMES = REQUIRED_FILE_NAMES + AUTHOR_FILE_NAMES
AUTHOR_HEADERS = ("author_key", "表示名", "識別メモ", "登録日時", "更新日時")
AUTHOR_ALIAS_HEADERS = ("author_key", "別名")
BOOK_ITEM_AUTHOR_HEADERS = ("book_key", "author_key", "表示順")
AUTHOR_MANIFEST_COUNT_KEYS = ("author_count", "author_alias_count", "book_item_author_count")
AUTHOR_KEY_PREFIX = "A"

MANIFEST_HEADERS = ("key", "value")
BOOK_ITEM_HEADERS_VERSION_1 = (
    "book_key",
    "ISBN",
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
BOOK_ITEM_HEADERS = (
    *BOOK_ITEM_HEADERS_VERSION_1[:2],
    "参照ISBN",
    *BOOK_ITEM_HEADERS_VERSION_1[2:],
)

TAG_HEADERS = (
    "tag_key",
    "タグ名",
    "登録日時",
    "更新日時",
)
BOOK_ITEM_TAG_HEADERS = ("book_key", "tag_key")
READING_HISTORY_HEADERS = (
    "history_key",
    "book_key",
    "読書開始日",
    "読了日",
    "読書メモ",
    "登録日時",
    "更新日時",
)

MANIFEST_REQUIRED_KEYS = (
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

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CSV_ENCODING = "utf-8-sig"
BOOLEAN_TRUE_TEXT = "はい"
BOOLEAN_FALSE_TEXT = "いいえ"

BOOK_KEY_PREFIX = "B"
TAG_KEY_PREFIX = "T"
HISTORY_KEY_PREFIX = "H"
PACKAGE_KEY_MINIMUM_DIGITS = 6

_KEY_PATTERN = re.compile(r"^(?P<prefix>[BTHA])(?P<number>[0-9]{6,})$")


def create_package_key(prefix: str, sequence: int) -> str:
    """連番からパッケージ内キーを生成する。"""
    if prefix not in {
        BOOK_KEY_PREFIX,
        TAG_KEY_PREFIX,
        HISTORY_KEY_PREFIX,
        AUTHOR_KEY_PREFIX,
    }:
        raise ValueError("未対応のパッケージキー種別です。")
    if sequence < 1:
        raise ValueError(
            "パッケージキーの連番は1以上である必要があります。"
        )

    return f"{prefix}{sequence:0{PACKAGE_KEY_MINIMUM_DIGITS}d}"


def is_valid_package_key(value: str, expected_prefix: str) -> bool:
    """値が指定種別のパッケージ内キーとして有効か返す。"""
    match = _KEY_PATTERN.fullmatch(value)
    if match is None:
        return False
    if expected_prefix not in {
        BOOK_KEY_PREFIX,
        TAG_KEY_PREFIX,
        HISTORY_KEY_PREFIX,
        AUTHOR_KEY_PREFIX,
    }:
        return False

    return (
        match.group("prefix") == expected_prefix
        and int(match.group("number")) >= 1
    )


@dataclass(frozen=True, slots=True)
class CsvDataPackageManifest:
    """CSVデータパッケージのmanifest情報を表す。"""

    application_version: str
    database_schema_version: int
    exported_at: str
    book_item_count: int
    tag_count: int
    book_item_tag_count: int
    reading_history_count: int
    package_format: str = PACKAGE_FORMAT
    format_version: int = PACKAGE_FORMAT_VERSION
    author_count: int = 0
    author_alias_count: int = 0
    book_item_author_count: int = 0

    def __post_init__(self) -> None:
        """manifestの基本的な整合性を検証する。"""
        if self.package_format != PACKAGE_FORMAT:
            raise ValueError("パッケージ形式が正しくありません。")
        if self.format_version not in SUPPORTED_PACKAGE_FORMAT_VERSIONS:
            raise ValueError("未対応のパッケージ形式Versionです。")
        if not self.application_version.strip():
            raise ValueError("アプリケーションVersionは必須です。")
        if self.database_schema_version < 1:
            raise ValueError(
                "DBスキーマVersionは1以上である必要があります。"
            )
        if not self.exported_at.strip():
            raise ValueError("エクスポート日時は必須です。")

        counts = (
            self.book_item_count,
            self.tag_count,
            self.book_item_tag_count,
            self.reading_history_count,
            self.author_count, self.author_alias_count, self.book_item_author_count,
        )
        if any(count < 0 for count in counts):
            raise ValueError("データ件数を負の値にはできません。")


@dataclass(frozen=True, slots=True)
class CsvDataPackageBookItem:
    """book_items.csvの正規化済み1行を表す。"""

    book_key: str
    title: str
    reading_status: str | None
    is_favorite: bool
    created_at: str
    updated_at: str
    isbn: str | None = None
    magazine_code: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    completion_month: str | None = None
    rating: int | None = None
    notes: str | None = None
    reference_isbn: str | None = None


@dataclass(frozen=True, slots=True)
class CsvDataPackageTag:
    """tags.csvの正規化済み1行を表す。"""

    tag_key: str
    name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class CsvDataPackageBookItemTag:
    """book_item_tags.csvの正規化済み1行を表す。"""

    book_key: str
    tag_key: str


@dataclass(frozen=True, slots=True)
class CsvDataPackageReadingHistory:
    """reading_histories.csvの正規化済み1行を表す。"""

    history_key: str
    book_key: str
    created_at: str
    updated_at: str
    started_on: str | None = None
    completed_on: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class CsvDataPackageAuthor:
    author_key: str
    name: str
    created_at: str
    updated_at: str
    disambiguation_note: str | None = None


@dataclass(frozen=True, slots=True)
class CsvDataPackageAuthorAlias:
    author_key: str
    name: str


@dataclass(frozen=True, slots=True)
class CsvDataPackageBookItemAuthor:
    book_key: str
    author_key: str
    position: int


@dataclass(frozen=True, slots=True)
class CsvDataPackageSnapshot:
    """DBから取得した完全データの一貫したスナップショット。"""

    book_items: tuple[CsvDataPackageBookItem, ...] = ()
    tags: tuple[CsvDataPackageTag, ...] = ()
    book_item_tags: tuple[CsvDataPackageBookItemTag, ...] = ()
    reading_histories: tuple[CsvDataPackageReadingHistory, ...] = ()
    authors: tuple[CsvDataPackageAuthor, ...] = ()
    author_aliases: tuple[CsvDataPackageAuthorAlias, ...] = ()
    book_item_authors: tuple[CsvDataPackageBookItemAuthor, ...] = ()


@dataclass(frozen=True, slots=True)
class CsvDataPackageArchiveFingerprint:
    """検査済みZIPの同一性確認に使用する情報。"""

    source_path: Path
    source_size: int
    source_modified_ns: int
    source_sha256: str


class CsvDataPackageIssueLevel(StrEnum):
    """CSVデータパッケージ検査Issueの重大度。"""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CsvDataPackageIssue:
    """ファイルと行・列を特定できる検査Issueを表す。"""

    level: CsvDataPackageIssueLevel
    file_name: str
    message: str
    row_number: int | None = None
    column_name: str | None = None
    value: str | None = None


@dataclass(frozen=True, slots=True)
class CsvDataPackagePreview:
    """完全データインポートの事前検査結果を表す。"""

    source_path: Path
    source_size: int
    source_modified_ns: int
    source_sha256: str
    manifest: CsvDataPackageManifest | None
    book_items: tuple[CsvDataPackageBookItem, ...] = ()
    tags: tuple[CsvDataPackageTag, ...] = ()
    book_item_tags: tuple[CsvDataPackageBookItemTag, ...] = ()
    reading_histories: tuple[CsvDataPackageReadingHistory, ...] = ()
    issues: tuple[CsvDataPackageIssue, ...] = ()
    authors: tuple[CsvDataPackageAuthor, ...] = ()
    author_aliases: tuple[CsvDataPackageAuthorAlias, ...] = ()
    book_item_authors: tuple[CsvDataPackageBookItemAuthor, ...] = ()

    @property
    def errors(self) -> tuple[CsvDataPackageIssue, ...]:
        """エラーだけを返す。"""
        return tuple(
            issue
            for issue in self.issues
            if issue.level is CsvDataPackageIssueLevel.ERROR
        )

    @property
    def warnings(self) -> tuple[CsvDataPackageIssue, ...]:
        """警告だけを返す。"""
        return tuple(
            issue
            for issue in self.issues
            if issue.level is CsvDataPackageIssueLevel.WARNING
        )

    @property
    def can_import(self) -> bool:
        """事前検査結果からインポート可能か返す。"""
        return self.manifest is not None and not self.errors


@dataclass(frozen=True, slots=True)
class CsvDataPackageImportResult:
    """完全データインポートの実行結果を表す。"""

    book_item_count: int
    tag_count: int
    book_item_tag_count: int
    reading_history_count: int
    backup_path: Path
    author_count: int = 0
    author_alias_count: int = 0
    book_item_author_count: int = 0


@dataclass(frozen=True, slots=True)
class CsvDataPackageExportResult:
    """完全データエクスポートの実行結果を表す。"""

    output_path: Path
    book_item_count: int
    tag_count: int
    book_item_tag_count: int
    reading_history_count: int
    author_count: int = 0
    author_alias_count: int = 0
    book_item_author_count: int = 0
