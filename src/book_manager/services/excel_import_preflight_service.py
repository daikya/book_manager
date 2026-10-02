"""Excelの列割り当てと全行の検査。DB登録・外部API呼び出しは行わない。"""
from datetime import date, datetime
from pathlib import Path
import re
from typing import Protocol
import unicodedata

from book_manager.models.book_item import BookItem
from book_manager.models.excel_import import (
    ExcelImportIssue, ExcelImportOptions, ExcelImportPreview, ExcelImportRecord,
)
from book_manager.models.excel_workbook import ExcelCell, ExcelSheetData
from book_manager.services.excel_date_converter import normalize_excel_reading_date
from book_manager.services.excel_workbook_reader_service import ExcelWorkbookReaderService
from book_manager.validators.reading_history_validator import validate_reading_history_dates


class _BookPreparer(Protocol):
    def prepare_book(self, **values: object) -> BookItem: ...


class ExcelImportPreflightService:
    """読み取り結果と列対応から、利用者が確認する登録予定を作る。"""
    DATE_FIELDS = {"started_on", "completed_on", "completion_month"}
    STATE_VALUES = {
        "未設定": None, "未読": "unread", "読書中": "reading", "読了": "completed",
        "unread": "unread", "reading": "reading", "completed": "completed",
    }

    def __init__(self, *, book_service: _BookPreparer,
                 reader: ExcelWorkbookReaderService | None = None):
        self._book_service = book_service
        self._reader = reader or ExcelWorkbookReaderService()

    def preview_file(self, source_path: Path | str, *, options: ExcelImportOptions,
                     header_row: int = 1) -> ExcelImportPreview:
        return self.preview_sheet(
            self._reader.read_sheet(source_path, header_row=header_row), options=options,
        )

    def preview_sheet(self, sheet: ExcelSheetData, *, options: ExcelImportOptions) -> ExcelImportPreview:
        mapping = dict(options.column_mapping)
        if any(column > len(sheet.header.cells) for column in mapping.values()):
            raise ValueError("割り当てた列がExcelに存在しません。")
        row_numbers = {row.row_number for row in sheet.rows}
        if any(row not in row_numbers for row in options.excluded_rows):
            raise ValueError("除外対象の行がデータ行に存在しません。")
        for field, column in mapping.items():
            cell = sheet.header.cells[column - 1]
            if cell.issue:
                raise ValueError(f"見出し {cell.coordinate}：{cell.issue}")
        records, errors, warnings, skipped = [], [], [], []
        for row in sheet.rows:
            if row.row_number in options.excluded_rows:
                skipped.append(ExcelImportIssue(row.row_number, "利用者が指定した除外行です。"))
                continue
            cells = {field: row.cells[column - 1] for field, column in mapping.items()}
            if all(self._empty(cell.value) and not cell.issue for cell in cells.values()):
                skipped.append(ExcelImportIssue(row.row_number, "割り当てた項目がすべて空欄の行です。"))
                continue
            if (options.end_marker_title is not None
                    and cells["title"].value == options.end_marker_title
                    and all(self._empty(cell.value) and not cell.issue
                            for field, cell in cells.items() if field != "title")
                    and not cells["title"].issue):
                skipped.append(ExcelImportIssue(row.row_number, "指定された管理用の最終行です。"))
                continue
            values = {}
            row_error_start = len(errors)
            for field, cell in cells.items():
                try:
                    if cell.issue:
                        raise ValueError(cell.issue)
                    values[field] = self._convert(field, cell)
                except ValueError as error:
                    errors.append(ExcelImportIssue(
                        row.row_number, str(error), field, cell.coordinate,
                    ))
            if len(errors) != row_error_start:
                continue
            started = values.pop("started_on", None)
            completed = values.pop("completed_on", None)
            history_notes = values.pop("history_notes", None)
            try:
                validate_reading_history_dates(started, completed)
            except ValueError as error:
                errors.append(ExcelImportIssue(
                    row.row_number, str(error), "completed_on",
                    cells["completed_on"].coordinate if "completed_on" in cells else None,
                ))
                continue
            explicit_month = values.get("completion_month")
            if explicit_month and completed and explicit_month != completed[:7]:
                errors.append(ExcelImportIssue(
                    row.row_number, "読了年月と読書履歴の読了年月が一致しません。",
                    "completion_month", cells["completion_month"].coordinate,
                ))
                continue
            if not explicit_month and completed:
                values["completion_month"] = completed[:7]
            suggested = "reading_status" not in mapping
            if suggested:
                values["reading_status"] = "completed" if completed else "reading" if started else None
            if "publication_format" not in mapping:
                values["publication_format"] = options.default_publication_format
            try:
                book = self._book_service.prepare_book(**values)
            except ValueError as error:
                errors.append(ExcelImportIssue(row.row_number, str(error)))
                continue
            record = ExcelImportRecord(
                row.row_number, book, started, completed, history_notes,
                reading_status_suggested=suggested and book.reading_status is not None,
            )
            records.append(record)
            if record.reading_status_suggested:
                warnings.append(ExcelImportIssue(
                    row.row_number, "開始・読了の記録から読書状態を提案しています。登録前に確認してください。",
                    "reading_status",
                ))
            if any(value and len(value) == 7 for value in (started, completed)):
                warnings.append(ExcelImportIssue(
                    row.row_number, "年月のみの読書記録です。日は不明のまま保持します。",
                ))
        return ExcelImportPreview(
            sheet.source_path, sheet.source_sha256, sheet.sheet_name, sheet.header.row_number,
            options, tuple(records), tuple(errors), tuple(warnings), tuple(skipped),
        )

    @staticmethod
    def _empty(value: object) -> bool:
        return value is None or isinstance(value, str) and not value.strip()

    @classmethod
    def _convert(cls, field: str, cell: ExcelCell):
        value = cell.value
        if field in cls.DATE_FIELDS:
            normalized = cls._date_value(cell, field)
            return normalized[:7] if normalized and field == "completion_month" else normalized
        if field == "is_favorite":
            if cls._empty(value):
                return False
            if type(value) is bool:
                return value
            text = cls._text(value).strip().lower()
            if text in {"はい", "true", "1"}:
                return True
            if text in {"いいえ", "false", "0"}:
                return False
            raise ValueError("お気に入りは、はい・いいえ・TRUE・FALSE・1・0で指定してください。")
        if field == "rating":
            if cls._empty(value):
                return None
            if type(value) is bool:
                raise ValueError("評価は1から5の整数で指定してください。")
            text = unicodedata.normalize("NFKC", cls._text(value)).strip()
            if text not in {"1", "2", "3", "4", "5"}:
                raise ValueError("評価は1から5の整数で指定してください。")
            return int(text)
        if field == "reading_status":
            if cls._empty(value):
                return None
            text = cls._text(value).strip()
            if text not in cls.STATE_VALUES:
                raise ValueError("読書状態は未設定・未読・読書中・読了で指定してください。")
            return cls.STATE_VALUES[text]
        if field == "tags":
            if cls._empty(value):
                return ()
            return tuple(part.strip() for part in cls._text(value).split("|") if part.strip())
        if cls._empty(value):
            return "" if field == "title" else None
        return cls._text(value)

    @staticmethod
    def _text(value: object) -> str:
        if isinstance(value, str):
            return value
        if type(value) is int:
            return str(value)
        if type(value) is float and value.is_integer():
            return str(int(value))
        raise ValueError("この項目は文字列または整数として指定してください。")

    @staticmethod
    def _date_value(cell: ExcelCell, field: str) -> str | None:
        value = cell.value
        if isinstance(value, (date, datetime)):
            # 表示用リテラル・ロケール・色指定を外し、年月だけの書式を判定する。
            pattern = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.|_.|\*.', "", cell.number_format).lower()
            if (re.search(r"[yeg]", pattern) and "m" in pattern
                    and not re.search(r"[dhs]", pattern)):
                value = f"{value.year:04d}-{value.month:02d}"
        return normalize_excel_reading_date(value, field_name={
            "started_on": "開始日・年月", "completed_on": "読了日・年月",
            "completion_month": "読了年月",
        }[field])
