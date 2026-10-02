"""Excel読み取り結果。列割り当てと登録前のセル情報を保持する。"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

ExcelCellValue = str | int | float | bool | date | datetime | time | timedelta | None


@dataclass(frozen=True, slots=True)
class ExcelCell:
    """値と書式を保持する。数式は計算せず保存済み値だけ使用する。"""
    coordinate: str
    value: ExcelCellValue
    number_format: str
    is_formula: bool = False
    issue: str | None = None


@dataclass(frozen=True, slots=True)
class ExcelRow:
    row_number: int
    cells: tuple[ExcelCell, ...]

    @property
    def is_empty(self) -> bool:
        """問題のある数式セルは空行として扱わない。"""
        return all(
            cell.issue is None and (
                cell.value is None or isinstance(cell.value, str) and not cell.value.strip()
            )
            for cell in self.cells
        )


@dataclass(frozen=True, slots=True)
class ExcelSheetData:
    """同じファイル内容から取得した見出しとデータ行。"""
    source_path: Path
    source_sha256: str
    source_size: int
    sheet_name: str
    header: ExcelRow
    rows: tuple[ExcelRow, ...]
