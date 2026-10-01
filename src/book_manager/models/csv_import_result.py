"""CSV import result models."""

from dataclasses import dataclass
from pathlib import Path

from book_manager.models.book_item import BookItem


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
    backup_path: Path | None = None


@dataclass(frozen=True, slots=True)
class CsvImportPreview:
    """DBを変更せずに検査した、単一CSVの登録予定と行別結果。"""

    input_path: Path
    source_sha256: str
    books: tuple[BookItem, ...]
    skipped: tuple[CsvImportIssue, ...]
    errors: tuple[CsvImportIssue, ...]

    @property
    def importable_count(self) -> int:
        return len(self.books)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def error_count(self) -> int:
        return len(self.errors)
