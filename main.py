"""book_manager の正式エントリーポイント。"""

from __future__ import annotations

import os
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

import requests

from book_manager.config.backup_settings_store import (
    BackupSettingsStore,
)
from book_manager.config.logging_config import (
    configure_file_logging,
    get_application_logger,
)
from book_manager.config.list_view_state_store import (
    ListViewStateStore,
)
from book_manager.config.paths import (
    ApplicationPaths,
    create_application_paths,
)
from book_manager.config.resource_paths import (
    get_application_icon_path,
    get_application_icon_png_path,
)
from book_manager.config.user_environment import (
    WindowsUserEnvironmentStore,
)
from book_manager.config.window_state_store import (
    WindowStateStore,
)
from book_manager.config.version import (
    get_application_version,
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
from book_manager.models.backup_settings import BackupSettings
from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)
from book_manager.repositories.book_repository import (
    BookRepository,
)
from book_manager.repositories.csv_data_package_repository import (
    CsvDataPackageRepository,
)
from book_manager.repositories.csv_data_package_restore_repository import (
    CsvDataPackageRestoreRepository,
)
from book_manager.repositories.reading_history_repository import (
    ReadingHistoryRepository,
)
from book_manager.services.backup_service import (
    BackupService,
)
from book_manager.services.application_settings_service import (
    ApplicationSettingsService,
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
from book_manager.services.csv_data_package_archive_validator import (
    CsvDataPackageArchiveValidator,
)
from book_manager.services.csv_data_package_export_service import (
    CsvDataPackageExportService,
)
from book_manager.services.csv_data_package_import_service import (
    CsvDataPackageImportService,
)
from book_manager.services.csv_data_package_preflight_service import (
    CsvDataPackagePreflightService,
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


logger = get_application_logger()


def main() -> None:
    """book_manager を起動する。"""
    application_paths: ApplicationPaths | None = None

    try:
        application_paths = create_application_paths()
        configure_file_logging(application_paths.log_path)
        logger.info("Book Managerを起動します。")
        migration_service = DataMigrationService(
            application_paths=application_paths,
            legacy_root_directory=(
                _get_legacy_root_directory()
            ),
        )
    except Exception:
        traceback.print_exc()
        logger.exception(
            "アプリケーションの起動準備に失敗しました。"
        )
        _show_fatal_startup_error(
            _get_log_path(application_paths),
        )
        return

    migration_result, migration_error = try_migrate_data(
        migration_service,
    )

    if migration_error is not None:
        logger.error(
            "利用者データの移行に失敗しました。",
            exc_info=(
                type(migration_error),
                migration_error,
                migration_error.__traceback__,
            ),
        )
        _show_fatal_startup_error(
            application_paths.log_path,
        )
        return

    if migration_result is not None:
        logger.info(
            "利用者データ移行判定: %s",
            migration_result.status.value,
        )

    try:
        _run_application(
            application_paths,
            migration_result,
        )
    except Exception:
        traceback.print_exc()
        logger.exception(
            "アプリケーションの実行中に"
            "致命的なエラーが発生しました。"
        )
        _show_fatal_startup_error(
            application_paths.log_path,
        )
        return


def _run_application(
    application_paths: ApplicationPaths,
    migration_result: DataMigrationResult | None,
) -> None:
    """依存関係を生成し、GUIのメインループを開始する。"""
    database_path = application_paths.database_path

    # 読込失敗時は自動バックアップと世代整理を始めない。
    backup_settings = _load_backup_settings(application_paths)

    initialize_database(database_path)

    backup_service = BackupService(
        database_path=database_path,
        backup_directory=(
            application_paths.backup_directory
        ),
        backup_interval=backup_settings.backup_interval,
        max_backups=backup_settings.max_backups,
    )
    backup_error = try_create_backup(
        backup_service,
    )

    if backup_error is not None:
        logger.error(
            "データベースの自動バックアップに失敗しました。",
            exc_info=(
                type(backup_error),
                backup_error,
                backup_error.__traceback__,
            ),
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
            root_directory=(
                application_paths.root_directory
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
        csv_data_package_repository = CsvDataPackageRepository(
            database_path,
        )
        csv_data_package_restore_repository = (
            CsvDataPackageRestoreRepository()
        )
        csv_data_package_archive_validator = (
            CsvDataPackageArchiveValidator()
        )
        csv_data_package_export_service = (
            CsvDataPackageExportService(
                csv_data_package_repository,
            )
        )
        csv_data_package_preflight_service = (
            CsvDataPackagePreflightService(
                csv_data_package_archive_validator,
            )
        )
        csv_data_package_import_service = (
            CsvDataPackageImportService(
                database_path=database_path,
                backup_service=backup_service,
                archive_validator=(
                    csv_data_package_archive_validator
                ),
                restore_repository=(
                    csv_data_package_restore_repository
                ),
            )
        )
        reading_history_service = ReadingHistoryService(
            reading_history_repository,
            repository,
        )
        application_settings_service = (
            ApplicationSettingsService(
                application_paths=application_paths,
                application_name="Book Manager",
                application_version=get_application_version(),
                user_environment_store=(
                    WindowsUserEnvironmentStore()
                ),
                backup_service=backup_service,
                active_backup_settings=backup_settings,
                cover_image_service=cover_image_service,
            )
        )
        window_state_store = WindowStateStore(
            application_paths.window_state_path,
        )
        list_view_state_store = ListViewStateStore(
            application_paths.list_view_state_path,
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
            application_settings_service,
            google_books_client.set_api_key,
            window_state_store=window_state_store,
            list_view_state_store=list_view_state_store,
            csv_data_package_export_service=(
                csv_data_package_export_service
            ),
            csv_data_package_preflight_service=(
                csv_data_package_preflight_service
            ),
            csv_data_package_import_service=(
                csv_data_package_import_service
            ),
        )
        _apply_window_icon(root)
        root.update_idletasks()
        root.mainloop()
    finally:
        session.close()
        logger.info("Book Managerを終了します。")


def _load_backup_settings(
    application_paths: ApplicationPaths,
) -> BackupSettings:
    """保存済みの設定を起動時に読み込み、未設定なら既定値を返す。"""
    return BackupSettingsStore(
        application_paths.backup_settings_path,
    ).load()


def _get_legacy_root_directory() -> Path:
    """Version 1.9以前の保存先を含むルートを返す。"""
    return Path(__file__).resolve().parent


def _apply_window_icon(root: tk.Tk) -> None:
    """メインウィンドウへアイコンを設定する。"""
    icon_path = get_application_icon_path()
    icon_png_path = get_application_icon_png_path()

    try:
        root.iconbitmap(
            default=str(icon_path),
        )
        root.iconbitmap(str(icon_path))
        icon_photo = tk.PhotoImage(
            master=root,
            file=str(icon_png_path),
        )
        root.iconphoto(True, icon_photo)
        root._book_manager_icon_photo = icon_photo
    except (OSError, tk.TclError):
        logger.warning(
            "アプリケーションアイコンを読み込めませんでした。",
            exc_info=True,
        )


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


def _get_log_path(
    application_paths: ApplicationPaths | None,
) -> Path | None:
    """利用できる場合だけログファイルパスを返す。"""
    if application_paths is None:
        return None

    return application_paths.log_path


def _show_fatal_startup_error(
    log_path: Path | None = None,
) -> None:
    """起動を継続できない場合のエラーを表示する。"""
    root = tk.Tk()
    root.withdraw()

    message = (
        "アプリケーションを起動できませんでした。\n\n"
        "利用者データは削除していません。"
    )

    if log_path is not None:
        message += (
            "\n\n詳細は次のログファイルを確認してください。"
            f"\n{log_path}"
        )

    try:
        messagebox.showerror(
            "起動エラー",
            message,
            parent=root,
        )
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
