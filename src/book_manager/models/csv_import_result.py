"""CSV import result models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CsvImportIssue:
    """CSVインポート時のスキップまたはエラー情報を表す。"""

    row_number: int
    message: str


@dataclass(frozen=True, slots=True)
class CsvImportResult:
    """CSVインポート処理の結果を表す。"""

    imported_count: int
    skipped_count: int
    error_count: int
    skipped: tuple[CsvImportIssue, ...]
    errors: tuple[CsvImportIssue, ...]
