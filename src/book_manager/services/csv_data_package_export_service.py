"""Complete CSV data package export service."""

from __future__ import annotations

import csv
import os
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from datetime import datetime
from importlib.metadata import version
from io import TextIOWrapper
from pathlib import Path

from book_manager.database.schema import SCHEMA_VERSION
from book_manager.models.csv_data_package import (
    BOOLEAN_FALSE_TEXT,
    BOOLEAN_TRUE_TEXT,
    BOOK_ITEM_HEADERS,
    BOOK_ITEM_TAG_HEADERS,
    BOOK_ITEM_TAGS_FILE_NAME,
    BOOK_ITEMS_FILE_NAME,
    CSV_ENCODING,
    MANIFEST_FILE_NAME,
    MANIFEST_HEADERS,
    MANIFEST_REQUIRED_KEYS,
    PACKAGE_FORMAT,
    PACKAGE_FORMAT_VERSION,
    READING_HISTORIES_FILE_NAME,
    READING_HISTORY_HEADERS,
    CURRENT_REQUIRED_FILE_NAMES as REQUIRED_FILE_NAMES,
    AUTHORS_FILE_NAME, AUTHOR_ALIASES_FILE_NAME, BOOK_ITEM_AUTHORS_FILE_NAME,
    AUTHOR_HEADERS, AUTHOR_ALIAS_HEADERS, BOOK_ITEM_AUTHOR_HEADERS, AUTHOR_MANIFEST_COUNT_KEYS,
    TAG_HEADERS,
    TAGS_FILE_NAME,
    CsvDataPackageBookItem,
    CsvDataPackageExportResult,
    CsvDataPackageManifest,
    CsvDataPackageReadingHistory,
    CsvDataPackageSnapshot,
)
from book_manager.repositories.csv_data_package_repository import (
    CsvDataPackageRepository,
)


class CsvDataPackageExportService:
    """完全データを8つのCSVを含むZIPへ出力する。"""

    FILE_NAME_DATETIME_FORMAT = "%Y%m%d_%H%M%S"
    EXPORTED_AT_FORMAT = "%Y-%m-%d %H:%M:%S"
    FILE_NAME_PREFIX = "book_manager_data_"
    FILE_NAME_SUFFIX = ".zip"
    TEMPORARY_DIRECTORY_PREFIX = ".book_manager_export_"

    READING_STATUS_LABELS = {
        "unread": "未読",
        "reading": "読書中",
        "completed": "読了",
    }

    def __init__(
        self,
        repository: CsvDataPackageRepository,
        *,
        now_provider: Callable[[], datetime] = datetime.now,
        application_version_provider: Callable[[], str] | None = None,
        database_schema_version: int = SCHEMA_VERSION,
    ) -> None:
        """依存するRepositoryと実行時情報の取得方法を保持する。"""
        self._repository = repository
        self._now_provider = now_provider
        self._application_version_provider = (
            application_version_provider
            if application_version_provider is not None
            else lambda: version("book-manager")
        )
        self._database_schema_version = database_schema_version

    def create_default_file_name(self) -> str:
        """現在日時を含む既定のZIPファイル名を返す。"""
        timestamp = self._now_provider().strftime(
            self.FILE_NAME_DATETIME_FORMAT
        )
        return f"{self.FILE_NAME_PREFIX}{timestamp}{self.FILE_NAME_SUFFIX}"

    def export(self, output_path: Path | str) -> CsvDataPackageExportResult:
        """完全データパッケージを原子的に出力する。"""
        resolved_output_path = Path(output_path)
        output_directory = resolved_output_path.parent

        if not output_directory.is_dir():
            raise FileNotFoundError(
                "CSVデータパッケージの保存先が存在しません。"
            )

        exported_at = self._now_provider()
        snapshot = self._repository.export_snapshot()
        manifest = self._create_manifest(
            snapshot=snapshot,
            exported_at=exported_at,
        )

        with tempfile.TemporaryDirectory(
            prefix=self.TEMPORARY_DIRECTORY_PREFIX,
            dir=output_directory,
        ) as temporary_directory_name:
            temporary_directory = Path(temporary_directory_name)
            temporary_zip_path = temporary_directory / "package.zip"

            self._write_csv_files(
                directory=temporary_directory,
                manifest=manifest,
                snapshot=snapshot,
            )
            self._write_archive(
                directory=temporary_directory,
                archive_path=temporary_zip_path,
            )
            self._validate_archive(temporary_zip_path)
            os.replace(temporary_zip_path, resolved_output_path)

        return CsvDataPackageExportResult(
            output_path=resolved_output_path,
            book_item_count=len(snapshot.book_items),
            tag_count=len(snapshot.tags),
            book_item_tag_count=len(snapshot.book_item_tags),
            reading_history_count=len(snapshot.reading_histories),
            author_count=len(snapshot.authors), author_alias_count=len(snapshot.author_aliases),
            book_item_author_count=len(snapshot.book_item_authors),
        )

    def _create_manifest(
        self,
        *,
        snapshot: CsvDataPackageSnapshot,
        exported_at: datetime,
    ) -> CsvDataPackageManifest:
        """スナップショットの実件数からmanifestを生成する。"""
        return CsvDataPackageManifest(
            application_version=self._application_version_provider(),
            database_schema_version=self._database_schema_version,
            exported_at=exported_at.strftime(self.EXPORTED_AT_FORMAT),
            book_item_count=len(snapshot.book_items),
            tag_count=len(snapshot.tags),
            book_item_tag_count=len(snapshot.book_item_tags),
            reading_history_count=len(snapshot.reading_histories),
            author_count=len(snapshot.authors), author_alias_count=len(snapshot.author_aliases),
            book_item_author_count=len(snapshot.book_item_authors),
        )

    def _write_csv_files(
        self,
        *,
        directory: Path,
        manifest: CsvDataPackageManifest,
        snapshot: CsvDataPackageSnapshot,
    ) -> None:
        """一時ディレクトリへ必須8ファイルを書き込む。"""
        self._write_csv(
            directory / MANIFEST_FILE_NAME,
            MANIFEST_HEADERS,
            self._manifest_rows(manifest),
        )
        self._write_csv(
            directory / BOOK_ITEMS_FILE_NAME,
            BOOK_ITEM_HEADERS,
            (
                self._book_item_row(book)
                for book in snapshot.book_items
            ),
        )
        self._write_csv(
            directory / TAGS_FILE_NAME,
            TAG_HEADERS,
            (
                (
                    tag.tag_key,
                    tag.name,
                    tag.created_at,
                    tag.updated_at,
                )
                for tag in snapshot.tags
            ),
        )
        self._write_csv(
            directory / BOOK_ITEM_TAGS_FILE_NAME,
            BOOK_ITEM_TAG_HEADERS,
            (
                (relation.book_key, relation.tag_key)
                for relation in snapshot.book_item_tags
            ),
        )
        self._write_csv(
            directory / READING_HISTORIES_FILE_NAME,
            READING_HISTORY_HEADERS,
            (
                self._reading_history_row(history)
                for history in snapshot.reading_histories
            ),
        )

        self._write_csv(directory / AUTHORS_FILE_NAME, AUTHOR_HEADERS,
                        ((a.author_key, a.name, a.disambiguation_note or '', a.created_at, a.updated_at) for a in snapshot.authors))
        self._write_csv(directory / AUTHOR_ALIASES_FILE_NAME, AUTHOR_ALIAS_HEADERS,
                        ((a.author_key, a.name) for a in snapshot.author_aliases))
        self._write_csv(directory / BOOK_ITEM_AUTHORS_FILE_NAME, BOOK_ITEM_AUTHOR_HEADERS,
                        ((a.book_key, a.author_key, str(a.position)) for a in snapshot.book_item_authors))

    @staticmethod
    def _write_csv(
        path: Path,
        headers: tuple[str, ...],
        rows: Iterable[tuple[str, ...]],
    ) -> None:
        """UTF-8 BOM付きCSVを書き込む。"""
        with path.open(
            "w",
            encoding=CSV_ENCODING,
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

    @staticmethod
    def _manifest_rows(
        manifest: CsvDataPackageManifest,
    ) -> tuple[tuple[str, str], ...]:
        """manifestを固定順のkey-value行へ変換する。"""
        values = {
            "package_format": manifest.package_format,
            "format_version": str(manifest.format_version),
            "application_version": manifest.application_version,
            "database_schema_version": str(
                manifest.database_schema_version
            ),
            "exported_at": manifest.exported_at,
            "book_item_count": str(manifest.book_item_count),
            "tag_count": str(manifest.tag_count),
            "book_item_tag_count": str(
                manifest.book_item_tag_count
            ),
            "reading_history_count": str(
                manifest.reading_history_count
            ),
        }
        values.update({key: str(getattr(manifest, key)) for key in AUTHOR_MANIFEST_COUNT_KEYS})
        keys = MANIFEST_REQUIRED_KEYS + (AUTHOR_MANIFEST_COUNT_KEYS if manifest.format_version >= 3 else ())
        return tuple((key, values[key]) for key in keys)

    @classmethod
    def _book_item_row(
        cls,
        book: CsvDataPackageBookItem,
    ) -> tuple[str, ...]:
        """書籍Modelをbook_items.csvの1行へ変換する。"""
        return (
            book.book_key,
            book.isbn or "",
            book.reference_isbn or "",
            book.magazine_code or "",
            book.title,
            book.author or "",
            book.publisher or "",
            book.publication_format or "",
            book.description or "",
            book.cover_image_url or "",
            book.completion_month or "",
            cls.READING_STATUS_LABELS.get(book.reading_status, ""),
            BOOLEAN_TRUE_TEXT if book.is_favorite else BOOLEAN_FALSE_TEXT,
            "" if book.rating is None else str(book.rating),
            book.notes or "",
            book.created_at,
            book.updated_at,
        )

    @staticmethod
    def _reading_history_row(
        history: CsvDataPackageReadingHistory,
    ) -> tuple[str, ...]:
        """読書履歴Modelをreading_histories.csvの1行へ変換する。"""
        return (
            history.history_key,
            history.book_key,
            history.started_on or "",
            history.completed_on or "",
            history.notes or "",
            history.created_at,
            history.updated_at,
        )

    @staticmethod
    def _write_archive(
        *,
        directory: Path,
        archive_path: Path,
    ) -> None:
        """必須8ファイルだけをZIP直下へ格納する。"""
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file_name in REQUIRED_FILE_NAMES:
                archive.write(
                    directory / file_name,
                    arcname=file_name,
                )

    @staticmethod
    def _validate_archive(archive_path: Path) -> None:
        """作成したZIPの構成とCSVヘッダーを自己検査する。"""
        expected_headers = {
            AUTHORS_FILE_NAME: AUTHOR_HEADERS,
            AUTHOR_ALIASES_FILE_NAME: AUTHOR_ALIAS_HEADERS,
            BOOK_ITEM_AUTHORS_FILE_NAME: BOOK_ITEM_AUTHOR_HEADERS,
            MANIFEST_FILE_NAME: MANIFEST_HEADERS,
            BOOK_ITEMS_FILE_NAME: BOOK_ITEM_HEADERS,
            TAGS_FILE_NAME: TAG_HEADERS,
            BOOK_ITEM_TAGS_FILE_NAME: BOOK_ITEM_TAG_HEADERS,
            READING_HISTORIES_FILE_NAME: READING_HISTORY_HEADERS,
        }

        with zipfile.ZipFile(archive_path, "r") as archive:
            file_names = tuple(archive.namelist())
            if file_names != REQUIRED_FILE_NAMES:
                raise ValueError(
                    "生成したCSVデータパッケージの構成が"
                    "正しくありません。"
                )

            bad_file = archive.testzip()
            if bad_file is not None:
                raise ValueError(
                    "生成したCSVデータパッケージが破損しています。"
                )

            for file_name, headers in expected_headers.items():
                with archive.open(file_name, "r") as binary_file:
                    with TextIOWrapper(
                        binary_file,
                        encoding=CSV_ENCODING,
                        newline="",
                    ) as text_file:
                        reader = csv.reader(text_file)
                        actual_headers = tuple(next(reader, ()))

                if actual_headers != headers:
                    raise ValueError(
                        f"生成した{file_name}のヘッダーが"
                        "正しくありません。"
                    )
