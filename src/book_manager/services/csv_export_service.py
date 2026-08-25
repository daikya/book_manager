"""書籍情報のCSVエクスポート処理。"""

from __future__ import annotations

import csv
from pathlib import Path

from book_manager.models.book_item import BookItem


class CsvExportService:
    """書籍情報をCSV形式で出力する。"""

    HEADERS = (
        "書籍名",
        "ISBN",
        "雑誌コード",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",
        "読了年月",
        "読書状態",
        "備考",
        "登録日時",
        "更新日時",
    )

    READING_STATUS_LABELS = {
        "unread": "未読",
        "reading": "読書中",
        "completed": "読了",
    }

    def export(
        self,
        books: list[BookItem],
        output_path: Path,
    ) -> None:
        """書籍一覧をCSVファイルへ出力する。

        Args:
            books:
                出力対象の書籍一覧。
            output_path:
                CSVファイルの保存先。
        """
        output_path = Path(output_path)

        with output_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.writer(file)

            writer.writerow(
                self.HEADERS,
            )

            for book in books:
                writer.writerow(
                    self._book_to_row(
                        book,
                    )
                )

    @classmethod
    def _book_to_row(
        cls,
        book: BookItem,
    ) -> tuple[str, ...]:
        """BookItemをCSV出力用の1行へ変換する。"""
        reading_status = (
            cls.READING_STATUS_LABELS.get(
                book.reading_status,
                "",
            )
        )

        return (
            book.title,
            book.isbn or "",
            book.magazine_code or "",
            book.author or "",
            book.publisher or "",
            book.publication_format or "",
            book.description or "",
            book.completion_month or "",
            reading_status,
            book.notes or "",
            book.created_at or "",
            book.updated_at or "",
        )