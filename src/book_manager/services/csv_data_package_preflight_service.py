"""Preflight validation for complete CSV data packages."""

from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from io import TextIOWrapper
from pathlib import Path
from urllib.parse import urlparse

from book_manager.models.csv_data_package import (
    BOOLEAN_FALSE_TEXT,
    BOOLEAN_TRUE_TEXT,
    BOOK_ITEM_HEADERS,
    BOOK_ITEM_TAG_HEADERS,
    BOOK_ITEM_TAGS_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    BOOK_KEY_PREFIX,
    CSV_ENCODING,
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
    TAG_HEADERS,
    TAG_KEY_PREFIX,
    TAGS_FILE_NAME,
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageIssue,
    CsvDataPackageIssueLevel,
    CsvDataPackageManifest,
    CsvDataPackagePreview,
    CsvDataPackageReadingHistory,
    CsvDataPackageTag,
    is_valid_package_key,
)
from book_manager.services.csv_data_package_archive_validator import (
    CsvDataPackageArchiveValidator,
)
from book_manager.validators.completion_month_validator import (
    validate_completion_month,
)
from book_manager.validators.isbn_validator import validate_isbn
from book_manager.validators.magazine_code_validator import (
    validate_magazine_code,
)
from book_manager.validators.tag_validator import validate_tag_name


@dataclass(frozen=True, slots=True)
class _CsvContent:
    """ヘッダー検査後のCSVデータ行と物理件数。"""

    rows: tuple[tuple[int, list[str]], ...]
    physical_count: int


class CsvDataPackagePreflightService:
    """安全検査済みZIP内の5つのCSVを全件検査する。"""

    READING_STATUS_VALUES = {
        "未読": "unread",
        "読書中": "reading",
        "読了": "completed",
    }

    def __init__(
        self,
        archive_validator: CsvDataPackageArchiveValidator,
    ) -> None:
        """ZIP構造の安全検査を行うValidatorを保持する。"""
        self._archive_validator = archive_validator

    def preview(
        self,
        source_path: Path | str,
    ) -> CsvDataPackagePreview:
        """ZIPと全CSVを検査し、DBを変更せずプレビューを返す。"""
        fingerprint = self._archive_validator.validate(source_path)
        issues: list[CsvDataPackageIssue] = []

        with zipfile.ZipFile(fingerprint.source_path, "r") as archive:
            manifest_content = self._read_csv(
                archive,
                file_name=MANIFEST_FILE_NAME,
                expected_headers=MANIFEST_HEADERS,
                issues=issues,
            )
            book_content = self._read_csv(
                archive,
                file_name=BOOK_ITEMS_FILE_NAME,
                expected_headers=BOOK_ITEM_HEADERS,
                issues=issues,
            )
            tag_content = self._read_csv(
                archive,
                file_name=TAGS_FILE_NAME,
                expected_headers=TAG_HEADERS,
                issues=issues,
            )
            relation_content = self._read_csv(
                archive,
                file_name=BOOK_ITEM_TAGS_FILE_NAME,
                expected_headers=BOOK_ITEM_TAG_HEADERS,
                issues=issues,
            )
            history_content = self._read_csv(
                archive,
                file_name=READING_HISTORIES_FILE_NAME,
                expected_headers=READING_HISTORY_HEADERS,
                issues=issues,
            )

        manifest = self._parse_manifest(manifest_content, issues)
        book_items, book_rows = self._parse_books(book_content, issues)
        tags, tag_rows = self._parse_tags(tag_content, issues)
        relations, relation_rows = self._parse_relations(
            relation_content,
            issues,
        )
        histories, history_rows = self._parse_histories(
            history_content,
            issues,
        )

        self._validate_references(
            book_items=book_items,
            book_rows=book_rows,
            tags=tags,
            tag_rows=tag_rows,
            relations=relations,
            relation_rows=relation_rows,
            histories=histories,
            history_rows=history_rows,
            issues=issues,
        )
        self._validate_manifest_counts(
            manifest=manifest,
            counts={
                "book_item_count": book_content.physical_count,
                "tag_count": tag_content.physical_count,
                "book_item_tag_count": relation_content.physical_count,
                "reading_history_count": history_content.physical_count,
            },
            issues=issues,
        )

        return CsvDataPackagePreview(
            source_path=fingerprint.source_path,
            source_size=fingerprint.source_size,
            source_modified_ns=fingerprint.source_modified_ns,
            source_sha256=fingerprint.source_sha256,
            manifest=manifest,
            book_items=tuple(book_items),
            tags=tuple(tags),
            book_item_tags=tuple(relations),
            reading_histories=tuple(histories),
            issues=tuple(issues),
        )

    @staticmethod
    def _read_csv(
        archive: zipfile.ZipFile,
        *,
        file_name: str,
        expected_headers: tuple[str, ...],
        issues: list[CsvDataPackageIssue],
    ) -> _CsvContent:
        """ZIP内CSVを厳密に読み、ヘッダーと列数を検査する。"""
        try:
            with archive.open(file_name, "r") as binary_file:
                with TextIOWrapper(
                    binary_file,
                    encoding=CSV_ENCODING,
                    newline="",
                ) as text_file:
                    rows = list(csv.reader(text_file, strict=True))
        except (UnicodeDecodeError, csv.Error) as error:
            issues.append(
                CsvDataPackageIssue(
                    level=CsvDataPackageIssueLevel.ERROR,
                    file_name=file_name,
                    message="CSVとして正常に解析できません。",
                    value=str(error),
                )
            )
            return _CsvContent((), 0)

        if not rows:
            issues.append(
                CsvDataPackageIssue(
                    level=CsvDataPackageIssueLevel.ERROR,
                    file_name=file_name,
                    row_number=1,
                    message="CSVヘッダーが存在しません。",
                )
            )
            return _CsvContent((), 0)

        if tuple(rows[0]) != expected_headers:
            issues.append(
                CsvDataPackageIssue(
                    level=CsvDataPackageIssueLevel.ERROR,
                    file_name=file_name,
                    row_number=1,
                    message="CSVヘッダーが仕様と一致しません。",
                    value=",".join(rows[0]),
                )
            )
            return _CsvContent((), max(len(rows) - 1, 0))

        valid_rows: list[tuple[int, list[str]]] = []
        for row_number, row in enumerate(rows[1:], start=2):
            if len(row) != len(expected_headers):
                issues.append(
                    CsvDataPackageIssue(
                        level=CsvDataPackageIssueLevel.ERROR,
                        file_name=file_name,
                        row_number=row_number,
                        message="列数が不正です。",
                        value=str(len(row)),
                    )
                )
                continue
            valid_rows.append((row_number, row))

        return _CsvContent(
            rows=tuple(valid_rows),
            physical_count=len(rows) - 1,
        )

    def _parse_manifest(
        self,
        content: _CsvContent,
        issues: list[CsvDataPackageIssue],
    ) -> CsvDataPackageManifest | None:
        """manifestの必須key、型、Versionを検査する。"""
        initial_error_count = sum(
            issue.level is CsvDataPackageIssueLevel.ERROR
            for issue in issues
        )
        values: dict[str, str] = {}
        for row_number, row in content.rows:
            key, value = row
            if not key:
                self._add_error(
                    issues,
                    MANIFEST_FILE_NAME,
                    row_number,
                    "key",
                    key,
                    "manifestのkeyは必須です。",
                )
                continue
            if key in values:
                self._add_error(
                    issues,
                    MANIFEST_FILE_NAME,
                    row_number,
                    "key",
                    key,
                    "manifestのkeyが重複しています。",
                )
                continue
            values[key] = value
            if key not in MANIFEST_REQUIRED_KEYS:
                issues.append(
                    CsvDataPackageIssue(
                        level=CsvDataPackageIssueLevel.WARNING,
                        file_name=MANIFEST_FILE_NAME,
                        row_number=row_number,
                        column_name="key",
                        value=key,
                        message="未知のmanifest keyを無視します。",
                    )
                )

        missing = [
            key for key in MANIFEST_REQUIRED_KEYS if key not in values
        ]
        for key in missing:
            self._add_error(
                issues,
                MANIFEST_FILE_NAME,
                None,
                "key",
                key,
                "manifestの必須keyがありません。",
            )
        if missing:
            return None

        if values["package_format"] != PACKAGE_FORMAT:
            self._add_error(
                issues,
                MANIFEST_FILE_NAME,
                None,
                "package_format",
                values["package_format"],
                "パッケージ形式が正しくありません。",
            )

        format_version = self._parse_non_negative_integer(
            values["format_version"],
            minimum=1,
            file_name=MANIFEST_FILE_NAME,
            column_name="format_version",
            issues=issues,
        )
        if (
            format_version is not None
            and format_version != PACKAGE_FORMAT_VERSION
        ):
            self._add_error(
                issues,
                MANIFEST_FILE_NAME,
                None,
                "format_version",
                values["format_version"],
                "未対応のパッケージ形式Versionです。",
            )

        if not values["application_version"].strip():
            self._add_error(
                issues,
                MANIFEST_FILE_NAME,
                None,
                "application_version",
                values["application_version"],
                "アプリケーションVersionは必須です。",
            )
        schema_version = self._parse_non_negative_integer(
            values["database_schema_version"],
            minimum=1,
            file_name=MANIFEST_FILE_NAME,
            column_name="database_schema_version",
            issues=issues,
        )
        self._parse_datetime(
            values["exported_at"],
            file_name=MANIFEST_FILE_NAME,
            row_number=None,
            column_name="exported_at",
            issues=issues,
        )

        counts = {
            key: self._parse_non_negative_integer(
                values[key],
                minimum=0,
                file_name=MANIFEST_FILE_NAME,
                column_name=key,
                issues=issues,
            )
            for key in (
                "book_item_count",
                "tag_count",
                "book_item_tag_count",
                "reading_history_count",
            )
        }
        current_error_count = sum(
            issue.level is CsvDataPackageIssueLevel.ERROR
            for issue in issues
        )
        if current_error_count != initial_error_count:
            return None
        assert format_version is not None
        assert schema_version is not None
        assert all(value is not None for value in counts.values())

        return CsvDataPackageManifest(
            package_format=values["package_format"],
            format_version=format_version,
            application_version=values["application_version"],
            database_schema_version=schema_version,
            exported_at=values["exported_at"],
            book_item_count=counts["book_item_count"],  # type: ignore[arg-type]
            tag_count=counts["tag_count"],  # type: ignore[arg-type]
            book_item_tag_count=counts["book_item_tag_count"],  # type: ignore[arg-type]
            reading_history_count=counts[
                "reading_history_count"
            ],  # type: ignore[arg-type]
        )

    def _parse_books(
        self,
        content: _CsvContent,
        issues: list[CsvDataPackageIssue],
    ) -> tuple[list[CsvDataPackageBookItem], dict[str, int]]:
        """book_items.csvを全行検査して正規化する。"""
        books: list[CsvDataPackageBookItem] = []
        key_rows: dict[str, int] = {}
        isbn_rows: dict[str, int] = {}
        magazine_rows: dict[str, int] = {}

        for row_number, row in content.rows:
            values = dict(zip(BOOK_ITEM_HEADERS, row, strict=True))
            row_issue_count = len(issues)
            book_key = values["book_key"]
            self._validate_key(
                book_key,
                BOOK_KEY_PREFIX,
                BOOK_ITEMS_FILE_NAME,
                row_number,
                "book_key",
                key_rows,
                issues,
            )
            title = values["書籍名"]
            if not title.strip():
                self._add_error(
                    issues,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "書籍名",
                    title,
                    "書籍名は必須です。",
                )

            isbn = self._optional(values["ISBN"])
            if isbn is not None:
                self._validate_with(
                    validate_isbn,
                    isbn,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "ISBN",
                    issues,
                )
                self._validate_duplicate(
                    isbn,
                    isbn_rows,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "ISBN",
                    "ISBNが重複しています。",
                    issues,
                )

            magazine_code = self._optional(values["雑誌コード"])
            if magazine_code is not None:
                self._validate_with(
                    validate_magazine_code,
                    magazine_code,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "雑誌コード",
                    issues,
                )
                self._validate_duplicate(
                    magazine_code,
                    magazine_rows,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "雑誌コード",
                    "雑誌コードが重複しています。",
                    issues,
                )

            completion_month = self._optional(values["読了年月"])
            if completion_month is not None:
                self._validate_with(
                    validate_completion_month,
                    completion_month,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "読了年月",
                    issues,
                )
            reading_status = self.READING_STATUS_VALUES.get(
                values["読書状態"]
            )
            if reading_status is None:
                self._add_error(
                    issues,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "読書状態",
                    values["読書状態"],
                    "読書状態が不正です。",
                )
            is_favorite = self._parse_boolean(
                values["お気に入り"],
                BOOK_ITEMS_FILE_NAME,
                row_number,
                "お気に入り",
                issues,
            )
            rating = self._parse_rating(
                values["評価"],
                BOOK_ITEMS_FILE_NAME,
                row_number,
                issues,
            )
            cover_image_url = self._optional(values["表紙画像URL"])
            if (
                cover_image_url is not None
                and not self._is_http_url(cover_image_url)
            ):
                self._add_error(
                    issues,
                    BOOK_ITEMS_FILE_NAME,
                    row_number,
                    "表紙画像URL",
                    cover_image_url,
                    "表紙画像URLが不正です。",
                )
            created_at, updated_at = self._validate_timestamp_pair(
                values["登録日時"],
                values["更新日時"],
                BOOK_ITEMS_FILE_NAME,
                row_number,
                issues,
            )

            if len(issues) != row_issue_count:
                continue
            assert reading_status is not None
            assert is_favorite is not None
            assert created_at is not None
            assert updated_at is not None
            books.append(
                CsvDataPackageBookItem(
                    book_key=book_key,
                    isbn=isbn,
                    magazine_code=magazine_code,
                    title=title,
                    author=self._optional(values["著者名"]),
                    publisher=self._optional(values["出版社"]),
                    publication_format=self._optional(values["出版形態"]),
                    description=self._optional(values["内容紹介"]),
                    cover_image_url=cover_image_url,
                    completion_month=completion_month,
                    reading_status=reading_status,
                    is_favorite=is_favorite,
                    rating=rating,
                    notes=self._optional(values["備考"]),
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )

        return books, key_rows

    def _parse_tags(
        self,
        content: _CsvContent,
        issues: list[CsvDataPackageIssue],
    ) -> tuple[list[CsvDataPackageTag], dict[str, int]]:
        """tags.csvを全行検査して正規化する。"""
        tags: list[CsvDataPackageTag] = []
        key_rows: dict[str, int] = {}
        name_rows: dict[str, int] = {}

        for row_number, row in content.rows:
            values = dict(zip(TAG_HEADERS, row, strict=True))
            row_issue_count = len(issues)
            tag_key = values["tag_key"]
            self._validate_key(
                tag_key,
                TAG_KEY_PREFIX,
                TAGS_FILE_NAME,
                row_number,
                "tag_key",
                key_rows,
                issues,
            )
            name = values["タグ名"]
            self._validate_with(
                validate_tag_name,
                name,
                TAGS_FILE_NAME,
                row_number,
                "タグ名",
                issues,
            )
            self._validate_duplicate(
                name,
                name_rows,
                TAGS_FILE_NAME,
                row_number,
                "タグ名",
                "タグ名が重複しています。",
                issues,
            )
            created_at, updated_at = self._validate_timestamp_pair(
                values["登録日時"],
                values["更新日時"],
                TAGS_FILE_NAME,
                row_number,
                issues,
            )
            if len(issues) != row_issue_count:
                continue
            assert created_at is not None
            assert updated_at is not None
            tags.append(
                CsvDataPackageTag(
                    tag_key=tag_key,
                    name=name,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )

        return tags, key_rows

    def _parse_relations(
        self,
        content: _CsvContent,
        issues: list[CsvDataPackageIssue],
    ) -> tuple[list[CsvDataPackageBookItemTag], list[int]]:
        """book_item_tags.csvを全行検査する。"""
        relations: list[CsvDataPackageBookItemTag] = []
        row_numbers: list[int] = []
        relation_rows: dict[tuple[str, str], int] = {}

        for row_number, row in content.rows:
            values = dict(zip(BOOK_ITEM_TAG_HEADERS, row, strict=True))
            row_issue_count = len(issues)
            book_key = values["book_key"]
            tag_key = values["tag_key"]
            self._validate_key_format(
                book_key,
                BOOK_KEY_PREFIX,
                BOOK_ITEM_TAGS_FILE_NAME,
                row_number,
                "book_key",
                issues,
            )
            self._validate_key_format(
                tag_key,
                TAG_KEY_PREFIX,
                BOOK_ITEM_TAGS_FILE_NAME,
                row_number,
                "tag_key",
                issues,
            )
            relation = (book_key, tag_key)
            if relation in relation_rows:
                self._add_error(
                    issues,
                    BOOK_ITEM_TAGS_FILE_NAME,
                    row_number,
                    None,
                    f"{book_key},{tag_key}",
                    "書籍とタグの関連が重複しています。",
                )
            else:
                relation_rows[relation] = row_number

            if len(issues) != row_issue_count:
                continue
            relations.append(CsvDataPackageBookItemTag(*relation))
            row_numbers.append(row_number)

        return relations, row_numbers

    def _parse_histories(
        self,
        content: _CsvContent,
        issues: list[CsvDataPackageIssue],
    ) -> tuple[list[CsvDataPackageReadingHistory], list[int]]:
        """reading_histories.csvを全行検査して正規化する。"""
        histories: list[CsvDataPackageReadingHistory] = []
        row_numbers: list[int] = []
        key_rows: dict[str, int] = {}

        for row_number, row in content.rows:
            values = dict(zip(READING_HISTORY_HEADERS, row, strict=True))
            row_issue_count = len(issues)
            history_key = values["history_key"]
            book_key = values["book_key"]
            self._validate_key(
                history_key,
                HISTORY_KEY_PREFIX,
                READING_HISTORIES_FILE_NAME,
                row_number,
                "history_key",
                key_rows,
                issues,
            )
            self._validate_key_format(
                book_key,
                BOOK_KEY_PREFIX,
                READING_HISTORIES_FILE_NAME,
                row_number,
                "book_key",
                issues,
            )
            started_on = self._parse_date(
                values["読書開始日"],
                READING_HISTORIES_FILE_NAME,
                row_number,
                "読書開始日",
                issues,
            )
            completed_on = self._parse_date(
                values["読了日"],
                READING_HISTORIES_FILE_NAME,
                row_number,
                "読了日",
                issues,
            )
            notes = self._optional(values["読書メモ"])
            if started_on is None and completed_on is None and notes is None:
                self._add_error(
                    issues,
                    READING_HISTORIES_FILE_NAME,
                    row_number,
                    None,
                    None,
                    "読書履歴には日付またはメモが必要です。",
                )
            if (
                started_on is not None
                and completed_on is not None
                and started_on > completed_on
            ):
                self._add_error(
                    issues,
                    READING_HISTORIES_FILE_NAME,
                    row_number,
                    "読了日",
                    completed_on,
                    "読書開始日は読了日以前である"
                    "必要があります。",
                )
            created_at, updated_at = self._validate_timestamp_pair(
                values["登録日時"],
                values["更新日時"],
                READING_HISTORIES_FILE_NAME,
                row_number,
                issues,
            )

            if len(issues) != row_issue_count:
                continue
            assert created_at is not None
            assert updated_at is not None
            histories.append(
                CsvDataPackageReadingHistory(
                    history_key=history_key,
                    book_key=book_key,
                    started_on=started_on,
                    completed_on=completed_on,
                    notes=notes,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
            row_numbers.append(row_number)

        return histories, row_numbers

    def _validate_references(
        self,
        *,
        book_items: list[CsvDataPackageBookItem],
        book_rows: dict[str, int],
        tags: list[CsvDataPackageTag],
        tag_rows: dict[str, int],
        relations: list[CsvDataPackageBookItemTag],
        relation_rows: list[int],
        histories: list[CsvDataPackageReadingHistory],
        history_rows: list[int],
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """ファイル間の参照整合性を検査する。"""
        valid_book_keys = {book.book_key for book in book_items}
        valid_tag_keys = {tag.tag_key for tag in tags}
        declared_book_keys = set(book_rows)
        declared_tag_keys = set(tag_rows)

        for relation, row_number in zip(
            relations,
            relation_rows,
            strict=True,
        ):
            if relation.book_key not in declared_book_keys:
                self._add_error(
                    issues,
                    BOOK_ITEM_TAGS_FILE_NAME,
                    row_number,
                    "book_key",
                    relation.book_key,
                    "参照先の書籍が存在しません。",
                )
            elif relation.book_key not in valid_book_keys:
                self._add_error(
                    issues,
                    BOOK_ITEM_TAGS_FILE_NAME,
                    row_number,
                    "book_key",
                    relation.book_key,
                    "参照先の書籍に入力エラーがあります。",
                )
            if relation.tag_key not in declared_tag_keys:
                self._add_error(
                    issues,
                    BOOK_ITEM_TAGS_FILE_NAME,
                    row_number,
                    "tag_key",
                    relation.tag_key,
                    "参照先のタグが存在しません。",
                )
            elif relation.tag_key not in valid_tag_keys:
                self._add_error(
                    issues,
                    BOOK_ITEM_TAGS_FILE_NAME,
                    row_number,
                    "tag_key",
                    relation.tag_key,
                    "参照先のタグに入力エラーがあります。",
                )

        for history, row_number in zip(
            histories,
            history_rows,
            strict=True,
        ):
            if history.book_key not in declared_book_keys:
                self._add_error(
                    issues,
                    READING_HISTORIES_FILE_NAME,
                    row_number,
                    "book_key",
                    history.book_key,
                    "参照先の書籍が存在しません。",
                )
            elif history.book_key not in valid_book_keys:
                self._add_error(
                    issues,
                    READING_HISTORIES_FILE_NAME,
                    row_number,
                    "book_key",
                    history.book_key,
                    "参照先の書籍に入力エラーがあります。",
                )

    def _validate_manifest_counts(
        self,
        *,
        manifest: CsvDataPackageManifest | None,
        counts: dict[str, int],
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """manifestの件数と各CSVの物理データ行数を比較する。"""
        if manifest is None:
            return
        expected_counts = {
            "book_item_count": manifest.book_item_count,
            "tag_count": manifest.tag_count,
            "book_item_tag_count": manifest.book_item_tag_count,
            "reading_history_count": manifest.reading_history_count,
        }
        for key, actual_count in counts.items():
            if expected_counts[key] == actual_count:
                continue
            self._add_error(
                issues,
                MANIFEST_FILE_NAME,
                None,
                key,
                str(expected_counts[key]),
                f"manifest件数と実件数が一致しません: {actual_count}",
            )

    def _validate_key(
        self,
        value: str,
        prefix: str,
        file_name: str,
        row_number: int,
        column_name: str,
        seen_rows: dict[str, int],
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """キー形式と同一ファイル内の重複を検査する。"""
        self._validate_key_format(
            value,
            prefix,
            file_name,
            row_number,
            column_name,
            issues,
        )
        self._validate_duplicate(
            value,
            seen_rows,
            file_name,
            row_number,
            column_name,
            f"{column_name}が重複しています。",
            issues,
        )

    @staticmethod
    def _validate_key_format(
        value: str,
        prefix: str,
        file_name: str,
        row_number: int,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """パッケージ内キーの形式を検査する。"""
        if is_valid_package_key(value, prefix):
            return
        CsvDataPackagePreflightService._add_error(
            issues,
            file_name,
            row_number,
            column_name,
            value,
            "パッケージ内キーの形式が不正です。",
        )

    @staticmethod
    def _validate_duplicate(
        value: str,
        seen_rows: dict[str, int],
        file_name: str,
        row_number: int,
        column_name: str,
        message: str,
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """値の重複を検査し、初出行を保持する。"""
        if value in seen_rows:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                row_number,
                column_name,
                value,
                f"{message} 初出行: {seen_rows[value]}",
            )
            return
        seen_rows[value] = row_number

    @staticmethod
    def _validate_with(
        validator: object,
        value: str,
        file_name: str,
        row_number: int,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> None:
        """既存ValidatorのValueErrorをIssueへ変換する。"""
        try:
            validator(value)  # type: ignore[operator]
        except (TypeError, ValueError) as error:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                row_number,
                column_name,
                value,
                str(error),
            )

    def _validate_timestamp_pair(
        self,
        created_text: str,
        updated_text: str,
        file_name: str,
        row_number: int,
        issues: list[CsvDataPackageIssue],
    ) -> tuple[str | None, str | None]:
        """登録・更新日時の形式と前後関係を検査する。"""
        created = self._parse_datetime(
            created_text,
            file_name=file_name,
            row_number=row_number,
            column_name="登録日時",
            issues=issues,
        )
        updated = self._parse_datetime(
            updated_text,
            file_name=file_name,
            row_number=row_number,
            column_name="更新日時",
            issues=issues,
        )
        if created is not None and updated is not None and updated < created:
            self._add_error(
                issues,
                file_name,
                row_number,
                "更新日時",
                updated_text,
                "更新日時は登録日時以降である必要があります。",
            )
            return None, None
        return (
            created_text if created is not None else None,
            updated_text if updated is not None else None,
        )

    @staticmethod
    def _parse_datetime(
        value: str,
        *,
        file_name: str,
        row_number: int | None,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> datetime | None:
        """固定書式の日時を検査する。"""
        try:
            parsed = datetime.strptime(value, DATETIME_FORMAT)
        except ValueError:
            parsed = None
        if parsed is None or parsed.strftime(DATETIME_FORMAT) != value:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                row_number,
                column_name,
                value,
                "日時はYYYY-MM-DD HH:MM:SS形式で入力してください。",
            )
            return None
        return parsed

    @staticmethod
    def _parse_date(
        value: str,
        file_name: str,
        row_number: int,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> str | None:
        """空値または固定書式の日付を検査する。"""
        if value == "":
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            parsed = None
        if parsed is None or parsed.strftime(DATE_FORMAT) != value:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                row_number,
                column_name,
                value,
                "日付はYYYY-MM-DD形式で入力してください。",
            )
            return None
        return value

    @staticmethod
    def _parse_boolean(
        value: str,
        file_name: str,
        row_number: int,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> bool | None:
        """はい・いいえをboolへ変換する。"""
        if value == BOOLEAN_TRUE_TEXT:
            return True
        if value == BOOLEAN_FALSE_TEXT:
            return False
        CsvDataPackagePreflightService._add_error(
            issues,
            file_name,
            row_number,
            column_name,
            value,
            "お気に入りが不正です。",
        )
        return None

    @staticmethod
    def _parse_rating(
        value: str,
        file_name: str,
        row_number: int,
        issues: list[CsvDataPackageIssue],
    ) -> int | None:
        """空値または1～5の評価を変換する。"""
        if value == "":
            return None
        try:
            rating = int(value)
        except ValueError:
            rating = 0
        if str(rating) != value or not 1 <= rating <= 5:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                row_number,
                "評価",
                value,
                "評価は1から5の整数で指定してください。",
            )
            return None
        return rating

    @staticmethod
    def _parse_non_negative_integer(
        value: str,
        *,
        minimum: int,
        file_name: str,
        column_name: str,
        issues: list[CsvDataPackageIssue],
    ) -> int | None:
        """ASCII表記の指定値以上の整数を変換する。"""
        if not value or not all("0" <= char <= "9" for char in value):
            parsed = None
        else:
            parsed = int(value)
        if parsed is None or parsed < minimum or str(parsed) != value:
            CsvDataPackagePreflightService._add_error(
                issues,
                file_name,
                None,
                column_name,
                value,
                f"{column_name}が不正です。",
            )
            return None
        return parsed

    @staticmethod
    def _optional(value: str) -> str | None:
        """CSVの空文字列だけをNoneへ変換する。"""
        return value if value != "" else None

    @staticmethod
    def _is_http_url(value: str) -> bool:
        """HTTPまたはHTTPSの絶対URLか返す。"""
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _add_error(
        issues: list[CsvDataPackageIssue],
        file_name: str,
        row_number: int | None,
        column_name: str | None,
        value: str | None,
        message: str,
    ) -> None:
        """エラーIssueを追加する。"""
        issues.append(
            CsvDataPackageIssue(
                level=CsvDataPackageIssueLevel.ERROR,
                file_name=file_name,
                row_number=row_number,
                column_name=column_name,
                value=value,
                message=message,
            )
        )
