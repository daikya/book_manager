"""書籍情報のCSVインポート処理。"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from book_manager.models.csv_import_result import (
    CsvImportIssue,
    CsvImportResult,
)

if TYPE_CHECKING:
    from book_manager.services.book_service import BookService


class CsvImportService:
    """書籍情報をCSV形式から取り込む。"""

    HEADERS = (
        "書籍名",
        "ISBN",
        "雑誌コード",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",        "読了年月",
        "読書状態",
        "お気に入り",
        "評価",
        "備考",
        "登録日時",
        "更新日時",
    )

    READING_STATUS_VALUES = {
        "": None,
        "未読": "unread",
        "読書中": "reading",
        "読了": "completed",
    }

    def __init__(
        self,
        *,
        book_service: BookService,
    ) -> None:
        """CsvImportServiceを初期化する。

        Args:
            book_service:
                書籍情報の登録・検索を担当するサービス。
        """
        self._book_service = book_service

    def import_file(
        self,
        input_path: Path,
    ) -> CsvImportResult:
        """CSVファイルから書籍情報を取り込む。

        Args:
            input_path:
                読み込むCSVファイル。

        Returns:
            CSVインポート処理の結果。

        Raises:
            ValueError:
                CSVヘッダーが仕様と一致しない場合。
        """
        input_path = Path(input_path)

        with input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            try:
                reader = csv.reader(
                    file,
                    strict=True,
                )
                rows = list(reader)
            except csv.Error as exc:
                raise ValueError(
                    "CSVとして正常に解析できません。"
                ) from exc

        if not rows:
            raise ValueError(
                "CSVヘッダーが存在しません。"
            )

        header = tuple(rows[0])

        if header != self.HEADERS:
            raise ValueError(
                "CSVヘッダーが仕様と一致しません。"
            )

        imported_count = 0
        skipped: list[CsvImportIssue] = []
        errors: list[CsvImportIssue] = []

        for row_number, row in enumerate(
            rows[1:],
            start=2,
        ):
            if len(row) != len(self.HEADERS):
                errors.append(
                    CsvImportIssue(
                        row_number=row_number,
                        message="列数が不正です。",
                    )
                )
                continue

            try:
                reading_status = self._convert_reading_status(
                    row[8],
                )
                is_favorite = self._convert_is_favorite(
                    row[9],
                )
                rating = self._convert_rating(
                    row[10],
                )
            except ValueError as exc:
                errors.append(
                    CsvImportIssue(
                        row_number=row_number,
                        message=str(exc),
                    )
                )
                continue

            isbn = row[1]
            magazine_code = row[2]

            if isbn:
                try:
                    existing_books = (
                        self._book_service.find_books_by_isbn(
                            isbn,
                        )
                    )
                except ValueError as exc:
                    errors.append(
                        CsvImportIssue(
                            row_number=row_number,
                            message=str(exc),
                        )
                    )
                    continue

                if existing_books:
                    skipped.append(
                        CsvImportIssue(
                            row_number=row_number,
                            message=(
                                "ISBNが既存データと重複しています。"
                            ),
                        )
                    )
                    continue

            if magazine_code:
                try:
                    existing_books = (
                        self._book_service.find_books_by_magazine_code(
                            magazine_code,
                        )
                    )
                except ValueError as exc:
                    errors.append(
                        CsvImportIssue(
                            row_number=row_number,
                            message=str(exc),
                        )
                    )
                    continue

                if existing_books:
                    skipped.append(
                        CsvImportIssue(
                            row_number=row_number,
                            message=(
                                "雑誌コードが既存データと重複しています。"
                            ),
                        )
                    )
                    continue

            try:
                self._book_service.add_book(
                    title=row[0],
                    isbn=isbn,
                    magazine_code=magazine_code,
                    author=row[3],
                    publisher=row[4],
                    publication_format=row[5],
                    description=row[6],
                    completion_month=row[7],
                    reading_status=reading_status,
                    is_favorite=is_favorite,
                    rating=rating,
                    notes=row[11],
                )
            except ValueError as exc:
                errors.append(
                    CsvImportIssue(
                        row_number=row_number,
                        message=str(exc),
                    )
                )
                continue

            imported_count += 1

        return CsvImportResult(
            imported_count=imported_count,
            skipped_count=len(skipped),
            error_count=len(errors),
            skipped=tuple(skipped),
            errors=tuple(errors),
        )

    @classmethod
    def _convert_reading_status(
        cls,
        value: str,
    ) -> str | None:
        """CSV上の読書状態を内部値へ変換する。"""
        if value not in cls.READING_STATUS_VALUES:
            raise ValueError(
                "読書状態が不正です。"
            )

        return cls.READING_STATUS_VALUES[value]

    @staticmethod
    def _convert_is_favorite(
        value: str,
    ) -> bool:
        """CSV上のお気に入り状態をboolへ変換する。"""
        if value == "はい":
            return True

        if value == "いいえ":
            return False

        raise ValueError(
            "お気に入りが不正です。"
        )

    @staticmethod
    def _convert_rating(
        value: str,
    ) -> int | None:
        """CSV上の評価を内部値へ変換する。"""
        if value == "":
            return None

        try:
            rating = int(value)
        except ValueError as exc:
            raise ValueError(
                "評価が不正です。"
            ) from exc

        if rating < 1 or rating > 5:
            raise ValueError(
                "評価が不正です。"
            )

        return rating
