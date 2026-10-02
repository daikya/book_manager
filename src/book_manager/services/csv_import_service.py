"""書籍情報のCSVインポート処理。"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from book_manager.models.csv_import_result import (
    CsvImportIssue,
    CsvImportPreview,
    CsvImportResult,
)

if TYPE_CHECKING:
    from book_manager.services.book_service import BookService
    from book_manager.services.backup_service import BackupService


class CsvImportService:
    """書籍情報をCSV形式から取り込む。"""

    HEADERS = (
        "書籍名",
        "ISBN",
        "参照ISBN",
        "雑誌コード",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",
        "読了年月",
        "読書状態",
        "お気に入り",
        "評価",
        "タグ",
        "備考",
        "登録日時",
        "更新日時",
    )

    V26_HEADERS = (
        "書籍名",
        "ISBN",
        "雑誌コード",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",
        "読了年月",
        "読書状態",
        "お気に入り",
        "評価",
        "タグ",
        "備考",
        "登録日時",
        "更新日時",
    )

    LEGACY_HEADERS = (
        "書籍名",
        "ISBN",
        "雑誌コード",
        "著者名",
        "出版社",
        "出版形態",
        "内容紹介",
        "読了年月",
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

    def preview_file(self, input_path: Path) -> CsvImportPreview:
        """CSV全件を検査し、登録やタグ作成を行わずに結果を返す。"""
        input_path = Path(input_path)

        source_bytes = input_path.read_bytes()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        with StringIO(source_bytes.decode("utf-8-sig"), newline="") as file:
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

        if header not in {
            self.HEADERS,
            self.V26_HEADERS,
            self.LEGACY_HEADERS,
        }:
            raise ValueError(
                "CSVヘッダーが仕様と一致しません。"
            )

        books = []
        skipped: list[CsvImportIssue] = []
        errors: list[CsvImportIssue] = []
        seen_isbns: set[str] = set()
        seen_magazine_codes: set[str] = set()
        for row_number, row in enumerate(rows[1:], start=2):
            if len(row) != len(header):
                errors.append(CsvImportIssue(row_number, "列数が不正です。"))
                continue
            values = dict(zip(header, row, strict=True))
            try:
                book = self._book_service.prepare_book(
                    title=values["書籍名"],
                    **({"reference_isbn": values["参照ISBN"]} if "参照ISBN" in values else {}),
                    isbn=values["ISBN"],
                    magazine_code=values["雑誌コード"],
                    author=values["著者名"],
                    publisher=values["出版社"],
                    publication_format=values["出版形態"],
                    description=values["内容紹介"],
                    completion_month=values["読了年月"],
                    reading_status=self._convert_reading_status(values["読書状態"]),
                    is_favorite=self._convert_is_favorite(values["お気に入り"]),
                    rating=self._convert_rating(values["評価"]),
                    tags=self._convert_tags(values.get("タグ", "")),
                    notes=values["備考"],
                )
                message = None
                if book.isbn:
                    if self._book_service.find_books_by_isbn(book.isbn):
                        message = "ISBNが既存データと重複しています。"
                    elif book.isbn in seen_isbns:
                        message = "ISBNがCSV内の登録予定データと重複しています。"
                if message is None and book.magazine_code:
                    if self._book_service.find_books_by_magazine_code(book.magazine_code):
                        message = "雑誌コードが既存データと重複しています。"
                    elif book.magazine_code in seen_magazine_codes:
                        message = "雑誌コードがCSV内の登録予定データと重複しています。"
                if message is not None:
                    skipped.append(CsvImportIssue(row_number, message))
                    continue
            except ValueError as exc:
                errors.append(CsvImportIssue(row_number, str(exc)))
                continue
            books.append(book)
            if book.isbn:
                seen_isbns.add(book.isbn)
            if book.magazine_code:
                seen_magazine_codes.add(book.magazine_code)
        return CsvImportPreview(
            input_path=input_path,
            source_sha256=source_sha256,
            books=tuple(books),
            skipped=tuple(skipped),
            errors=tuple(errors),
        )

    def execute_preview(
        self, preview: CsvImportPreview, *, backup_service: BackupService,
    ) -> CsvImportResult:
        """確認済みCSVを再検査し、バックアップ後に正常行を一括登録する。"""
        def validate_current() -> CsvImportPreview:
            current = self.preview_file(preview.input_path)
            def content(books):
                # 検査時に生成する登録日時は、比較から除外する。
                return tuple(replace(book, created_at=None, updated_at=None) for book in books)
            if (
                current.source_sha256 != preview.source_sha256
                or content(current.books) != content(preview.books)
                or current.skipped != preview.skipped
                or current.errors != preview.errors
            ):
                raise ValueError("検査後にCSVまたは重複状況が変わりました。再検査してください。")
            return current

        current = validate_current()
        backup_path = None
        if current.books:
            backup_path = backup_service.create_backup()
            if backup_path is None or not Path(backup_path).is_file():
                raise RuntimeError("取込前バックアップを確認できません。")
            current = validate_current()
            self._book_service.add_books(current.books)
        return CsvImportResult(
            imported_count=current.importable_count,
            skipped_count=current.skipped_count,
            error_count=current.error_count,
            skipped=current.skipped,
            errors=current.errors,
            backup_path=Path(backup_path) if backup_path is not None else None,
        )

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

        if header not in {
            self.HEADERS,
            self.V26_HEADERS,
            self.LEGACY_HEADERS,
        }:
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
            if len(row) != len(header):
                errors.append(
                    CsvImportIssue(
                        row_number=row_number,
                        message="列数が不正です。",
                    )
                )
                continue

            values = dict(zip(header, row, strict=True))

            try:
                reading_status = self._convert_reading_status(
                    values["読書状態"],
                )
                is_favorite = self._convert_is_favorite(
                    values["お気に入り"],
                )
                rating = self._convert_rating(
                    values["評価"],
                )
                tags = self._convert_tags(
                    values.get("タグ", ""),
                )
            except ValueError as exc:
                errors.append(
                    CsvImportIssue(
                        row_number=row_number,
                        message=str(exc),
                    )
                )
                continue

            isbn = values["ISBN"]
            magazine_code = values["雑誌コード"]

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
                    title=values["書籍名"],
                    **({"reference_isbn": values["参照ISBN"]} if "参照ISBN" in values else {}),
                    isbn=isbn,
                    magazine_code=magazine_code,
                    author=values["著者名"],
                    publisher=values["出版社"],
                    publication_format=values["出版形態"],
                    description=values["内容紹介"],
                    completion_month=values["読了年月"],
                    reading_status=reading_status,
                    is_favorite=is_favorite,
                    rating=rating,
                    tags=tags,
                    notes=values["備考"],
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

    @staticmethod
    def _convert_tags(
        value: str,
    ) -> tuple[str, ...]:
        """CSV上のタグ欄をタグ名のタプルへ変換する。"""
        if value == "":
            return ()

        return tuple(
            tag_name.strip()
            for tag_name in value.split("|")
        )
