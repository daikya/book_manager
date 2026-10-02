"""Excelの列割り当て・事前検査結果。登録処理は含まない。"""
from dataclasses import dataclass
from pathlib import Path

from book_manager.models.book_item import BookItem

EXCEL_IMPORT_FIELDS = (
    "title", "isbn", "reference_isbn", "magazine_code", "author", "publisher",
    "publication_format", "description", "completion_month", "reading_status",
    "is_favorite", "rating", "tags", "notes", "started_on", "completed_on",
    "history_notes",
)


@dataclass(frozen=True, slots=True)
class ExcelImportOptions:
    """列番号はExcelと同じ1始まり。列対応は利用者が確定する。"""
    column_mapping: tuple[tuple[str, int], ...]
    excluded_rows: tuple[int, ...] = ()
    end_marker_title: str | None = None
    default_publication_format: str | None = None

    def __post_init__(self):
        fields = [field for field, _ in self.column_mapping]
        columns = [column for _, column in self.column_mapping]
        if "title" not in fields:
            raise ValueError("書籍名の列割り当ては必須です。")
        if len(fields) != len(set(fields)) or len(columns) != len(set(columns)):
            raise ValueError("項目または列の割り当てが重複しています。")
        if any(field not in EXCEL_IMPORT_FIELDS for field in fields):
            raise ValueError("未対応の取り込み項目が指定されています。")
        if any(type(column) is not int or column < 1 for column in columns):
            raise ValueError("列番号は1以上の整数で指定してください。")
        if any(type(row) is not int or row < 1 for row in self.excluded_rows):
            raise ValueError("除外行は1以上の整数で指定してください。")
        if self.end_marker_title is not None and not self.end_marker_title.strip():
            raise ValueError("管理用の最終行タイトルは空欄にできません。")


@dataclass(frozen=True, slots=True)
class ExcelImportIssue:
    row_number: int
    message: str
    field: str | None = None
    coordinate: str | None = None


@dataclass(frozen=True, slots=True)
class ExcelImportRecord:
    row_number: int
    book: BookItem
    started_on: str | None = None
    completed_on: str | None = None
    history_notes: str | None = None
    reading_status_suggested: bool = False

    @property
    def has_history(self) -> bool:
        return any(value is not None for value in (
            self.started_on, self.completed_on, self.history_notes,
        ))


@dataclass(frozen=True, slots=True)
class ExcelImportPreview:
    source_path: Path
    source_sha256: str
    sheet_name: str
    header_row: int
    options: ExcelImportOptions
    records: tuple[ExcelImportRecord, ...]
    errors: tuple[ExcelImportIssue, ...] = ()
    warnings: tuple[ExcelImportIssue, ...] = ()
    skipped: tuple[ExcelImportIssue, ...] = ()

    @property
    def can_import(self) -> bool:
        """エラーのあるExcelは一部だけ登録する対象にしない。"""
        return bool(self.records) and not self.errors
