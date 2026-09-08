"""book_manager の正式エントリーポイント。"""

from __future__ import annotations

import os
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

import requests

from book_manager.config.paths import (
    ApplicationPaths,
    create_application_paths,
)
from book_manager.database.initializer import (
    initialize_database,
)
from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.metadata.book_metadata_service import (
    BookMetadataService,
)
from book_manager.metadata.google_books_client import (
    GoogleBooksClient,
)
from book_manager.metadata.openbd_client import (
    OpenBdClient,
)
from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)
from book_manager.repositories.book_repository import (
    BookRepository,
)
from book_manager.repositories.reading_history_repository import (
    ReadingHistoryRepository,
)
from book_manager.services.backup_service import (
    BackupService,
)
from book_manager.services.book_service import (
    BookService,
)
from book_manager.services.cover_image_service import (
    CoverImageService,
)
from book_manager.services.csv_export_service import (
    CsvExportService,
)
from book_manager.services.csv_import_service import (
    CsvImportService,
)
from book_manager.services.data_migration_service import (
    DataMigrationService,
)
from book_manager.services.reading_history_service import (
    ReadingHistoryService,
)
from book_manager.startup import (
    try_create_backup,
    try_migrate_data,
)


def main() -> None:
    """book_manager を起動する。"""
    try:
        application_paths = create_application_paths()
        migration_service = DataMigrationService(
            application_paths=application_paths,
            legacy_root_directory=(
                _get_legacy_root_directory()
            ),
        )
    except Exception as error:
        traceback.print_exc()
        _show_fatal_startup_error()
        return

    migration_result, migration_error = try_migrate_data(
        migration_service,
    )

    if migration_error is not None:
        _show_fatal_startup_error()
        return

    try:
        _run_application(
            application_paths,
            migration_result,
        )
    except Exception:
        traceback.print_exc()
        raise


def _run_application(
    application_paths: ApplicationPaths,
    migration_result: DataMigrationResult | None,
) -> None:
    """依存関係を生成し、GUIのメインループを開始する。"""
    database_path = application_paths.database_path

    initialize_database(database_path)

    backup_service = BackupService(
        database_path=database_path,
        backup_directory=(
            application_paths.backup_directory
        ),
    )
    backup_error = try_create_backup(
        backup_service,
    )

    repository = BookRepository(database_path)
    reading_history_repository = ReadingHistoryRepository(
        database_path,
    )
    session = requests.Session()

    try:
        google_books_client = GoogleBooksClient(
            session=session,
            api_key=os.getenv(
                "GOOGLE_BOOKS_API_KEY"
            ),
        )
        openbd_client = OpenBdClient(
            session=session,
        )
        metadata_service = BookMetadataService(
            clients=[
                google_books_client,
                openbd_client,
            ],
        )
        cover_image_service = CoverImageService(
            session=session,
            cache_directory=(
                application_paths.cover_cache_directory
            ),
        )
        book_service = BookService(
            repository,
            metadata_service=metadata_service,
            cover_image_service=cover_image_service,
        )
        csv_export_service = CsvExportService()
        csv_import_service = CsvImportService(
            book_service=book_service,
        )
        reading_history_service = ReadingHistoryService(
            reading_history_repository,
            repository,
        )
        root = tk.Tk()

        _show_migration_result(
            root,
            migration_result,
        )

        if backup_error is not None:
            messagebox.showwarning(
                "自動バックアップエラー",
                (
                    "データベースの自動バックアップに"
                    "失敗しました。\n\n"
                    "アプリケーションは引き続き利用できます。"
                ),
                parent=root,
            )

        BookManagerApplication(
            root,
            book_service,
            csv_export_service,
            csv_import_service,
            backup_service,
            reading_history_service,
        )
        root.mainloop()
    finally:
        session.close()


def _get_legacy_root_directory() -> Path:
    """Version 1.9以前の保存先を含むルートを返す。"""
    return Path(__file__).resolve().parent


def _show_migration_result(
    root: tk.Tk,
    migration_result: DataMigrationResult | None,
) -> None:
    """必要な場合だけ利用者データ移行結果を通知する。"""
    if migration_result is None:
        return

    if migration_result.status is DataMigrationStatus.MIGRATED:
        messagebox.showinfo(
            "利用者データ移行完了",
            (
                "既存の書籍管理データを新しい保存先へ"
                "移行しました。\n\n"
                "移行前のデータは元の場所に残しています。"
            ),
            parent=root,
        )
    elif (
        migration_result.status
        is DataMigrationStatus.MIGRATED_WITH_WARNINGS
    ):
        messagebox.showwarning(
            "利用者データ移行警告",
            (
                "書籍管理データの移行は完了しましたが、\n"
                "一部のバックアップまたは表紙画像を"
                "コピーできませんでした。\n\n"
                "移行前のファイルは元の場所に残しています。"
            ),
            parent=root,
        )


def _show_fatal_startup_error() -> None:
    """利用者データを準備できない場合のエラーを表示する。"""
    root = tk.Tk()
    root.withdraw()

    try:
        messagebox.showerror(
            "起動エラー",
            (
                "既存データを安全に移行できなかったため、\n"
                "アプリケーションの起動を中止しました。\n\n"
                "移行前のデータは変更していません。"
            ),
            parent=root,
        )
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
