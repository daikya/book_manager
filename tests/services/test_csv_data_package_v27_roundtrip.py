"""完全データZIP Version 2の実DB往復検証。"""
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.repositories.csv_data_package_repository import CsvDataPackageRepository
from book_manager.repositories.csv_data_package_restore_repository import CsvDataPackageRestoreRepository
from book_manager.services.csv_data_package_export_service import CsvDataPackageExportService
from book_manager.services.csv_data_package_archive_validator import CsvDataPackageArchiveValidator
from book_manager.services.csv_data_package_preflight_service import CsvDataPackagePreflightService


def test_version_2_database_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    initialize_database(source)
    initialize_database(target)
    stamp = "2026-09-01 10:00:00"
    with create_connection(source) as connection:
        book_id = connection.execute(
            """INSERT INTO book_items
            (title, reference_isbn, reading_status, is_favorite, created_at, updated_at)
            VALUES (?, ?, NULL, 0, ?, ?)""",
            ("音声版", "9784101010014", stamp, stamp),
        ).lastrowid
        tag_id = connection.execute(
            "INSERT INTO tags (name, created_at, updated_at) VALUES (?, ?, ?)",
            ("移行", stamp, stamp),
        ).lastrowid
        connection.execute(
            "INSERT INTO book_item_tags (book_item_id, tag_id) VALUES (?, ?)",
            (book_id, tag_id),
        )
        connection.execute(
            """INSERT INTO reading_histories
            (book_item_id, started_on, completed_on, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (book_id, "2026-09-20", "2026-09", "月のみ判明", stamp, stamp),
        )
    package = tmp_path / "complete.zip"
    repository = CsvDataPackageRepository(source)
    expected = repository.export_snapshot()
    CsvDataPackageExportService(
        repository, application_version_provider=lambda: "2.7.0",
    ).export(package)
    preview = CsvDataPackagePreflightService(
        CsvDataPackageArchiveValidator(),
    ).preview(package)
    assert preview.can_import
    assert preview.manifest.format_version == 2
    assert preview.book_items[0].reference_isbn == "9784101010014"
    assert preview.reading_histories[0].completed_on == "2026-09"
    with create_connection(target) as connection:
        CsvDataPackageRestoreRepository().restore(connection, preview)
        assert connection.execute("PRAGMA integrity_check").fetchall()[0][0] == "ok"
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    assert CsvDataPackageRepository(target).export_snapshot() == expected
    exported = tmp_path / "exported.zip"
    CsvDataPackageExportService(
        CsvDataPackageRepository(target), application_version_provider=lambda: "2.7.0",
    ).export(exported)
    actual = CsvDataPackagePreflightService(CsvDataPackageArchiveValidator()).preview(exported)
    for field in ("book_items", "tags", "book_item_tags", "reading_histories"):
        assert getattr(preview, field) == getattr(actual, field)


def test_version_1_restore_uses_empty_reference(tmp_path: Path) -> None:
    import csv
    import io
    import zipfile
    from book_manager.models.csv_data_package import (
        BOOK_ITEM_HEADERS_VERSION_1, BOOK_ITEMS_FILE_NAME, MANIFEST_FILE_NAME,
        MANIFEST_HEADERS, PACKAGE_FORMAT, TAG_HEADERS, TAGS_FILE_NAME,
        BOOK_ITEM_TAG_HEADERS, BOOK_ITEM_TAGS_FILE_NAME,
        READING_HISTORY_HEADERS, READING_HISTORIES_FILE_NAME,
    )
    stamp = "2026-09-01 10:00:00"
    rows = {
        MANIFEST_FILE_NAME: [list(MANIFEST_HEADERS),
            ["package_format", PACKAGE_FORMAT], ["format_version", "1"],
            ["application_version", "2.6.0"], ["database_schema_version", "7"],
            ["exported_at", stamp], ["book_item_count", "1"],
            ["tag_count", "0"], ["book_item_tag_count", "0"],
            ["reading_history_count", "0"]],
        BOOK_ITEMS_FILE_NAME: [list(BOOK_ITEM_HEADERS_VERSION_1),
            ["B000001", "", "", "旧形式", "", "", "", "", "", "", "", "いいえ", "", "", stamp, stamp]],
        TAGS_FILE_NAME: [list(TAG_HEADERS)],
        BOOK_ITEM_TAGS_FILE_NAME: [list(BOOK_ITEM_TAG_HEADERS)],
        READING_HISTORIES_FILE_NAME: [list(READING_HISTORY_HEADERS)],
    }
    package = tmp_path / "v1.zip"
    with zipfile.ZipFile(package, "w") as archive:
        for name, content in rows.items():
            text = io.StringIO(newline="")
            csv.writer(text).writerows(content)
            archive.writestr(name, text.getvalue().encode("utf-8-sig"))
    preview = CsvDataPackagePreflightService(CsvDataPackageArchiveValidator()).preview(package)
    assert preview.can_import
    target = tmp_path / "v1.db"
    initialize_database(target)
    with create_connection(target) as connection:
        CsvDataPackageRestoreRepository().restore(connection, preview)
    snapshot = CsvDataPackageRepository(target).export_snapshot()
    assert snapshot.book_items[0].title == "旧形式"
    assert snapshot.book_items[0].reference_isbn is None
