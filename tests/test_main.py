"""正式エントリーポイントのテスト。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from book_manager.config.paths import (
    ApplicationPaths,
    create_application_paths,
)
from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)


MAIN_MODULE_NAME = "book_manager_main_entrypoint"
MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
MAIN_SPEC = importlib.util.spec_from_file_location(
    MAIN_MODULE_NAME,
    MAIN_PATH,
)

assert MAIN_SPEC is not None
assert MAIN_SPEC.loader is not None

main_module = importlib.util.module_from_spec(MAIN_SPEC)
sys.modules[MAIN_MODULE_NAME] = main_module
MAIN_SPEC.loader.exec_module(main_module)


def create_paths(tmp_path: Path) -> ApplicationPaths:
    """テスト用ApplicationPathsを生成する。"""
    return create_application_paths(
        tmp_path / "application",
    )


def test_get_legacy_root_directory_uses_main_file() -> None:
    """旧保存先をmain.pyが存在するルートから決定する。"""
    assert main_module._get_legacy_root_directory() == (
        Path(main_module.__file__).resolve().parent
    )


def test_show_migration_result_shows_success(
    tmp_path: Path,
) -> None:
    """DB移行成功時は完了メッセージを表示する。"""
    root = Mock()
    result = DataMigrationResult(
        status=DataMigrationStatus.MIGRATED,
        source_database_path=tmp_path / "old.db",
        destination_database_path=tmp_path / "new.db",
    )

    with patch.object(
        main_module.messagebox,
        "showinfo",
    ) as showinfo:
        main_module._show_migration_result(root, result)

    showinfo.assert_called_once()
    assert showinfo.call_args.kwargs["parent"] is root


def test_show_migration_result_shows_warning(
    tmp_path: Path,
) -> None:
    """任意ファイルの移行失敗時は警告を表示する。"""
    root = Mock()
    result = DataMigrationResult(
        status=(
            DataMigrationStatus.MIGRATED_WITH_WARNINGS
        ),
        source_database_path=tmp_path / "old.db",
        destination_database_path=tmp_path / "new.db",
        warnings=("表紙画像をコピーできませんでした。",),
    )

    with patch.object(
        main_module.messagebox,
        "showwarning",
    ) as showwarning:
        main_module._show_migration_result(root, result)

    showwarning.assert_called_once()
    assert showwarning.call_args.kwargs["parent"] is root


def test_show_migration_result_does_not_show_for_normal_start(
    tmp_path: Path,
) -> None:
    """移行不要の通常起動ではメッセージを表示しない。"""
    root = Mock()
    result = DataMigrationResult(
        status=DataMigrationStatus.NOT_NEEDED,
        source_database_path=None,
        destination_database_path=tmp_path / "new.db",
    )

    with (
        patch.object(
            main_module.messagebox,
            "showinfo",
        ) as showinfo,
        patch.object(
            main_module.messagebox,
            "showwarning",
        ) as showwarning,
    ):
        main_module._show_migration_result(root, result)

    showinfo.assert_not_called()
    showwarning.assert_not_called()


def test_show_migration_result_accepts_none() -> None:
    """結果がない場合はメッセージを表示しない。"""
    root = Mock()

    with (
        patch.object(
            main_module.messagebox,
            "showinfo",
        ) as showinfo,
        patch.object(
            main_module.messagebox,
            "showwarning",
        ) as showwarning,
    ):
        main_module._show_migration_result(root, None)

    showinfo.assert_not_called()
    showwarning.assert_not_called()


def test_show_fatal_startup_error_uses_hidden_root() -> None:
    """致命的エラーを非表示の一時rootで通知する。"""
    root = Mock()

    with (
        patch.object(
            main_module.tk,
            "Tk",
            return_value=root,
        ),
        patch.object(
            main_module.messagebox,
            "showerror",
        ) as showerror,
    ):
        main_module._show_fatal_startup_error()

    root.withdraw.assert_called_once_with()
    showerror.assert_called_once()
    assert showerror.call_args.kwargs["parent"] is root
    root.destroy.assert_called_once_with()


def test_main_stops_when_path_creation_fails() -> None:
    """保存先を決定できない場合は通常起動しない。"""
    with (
        patch.object(
            main_module,
            "create_application_paths",
            side_effect=RuntimeError("path failed"),
        ),
        patch.object(
            main_module,
            "_show_fatal_startup_error",
        ) as show_error,
        patch.object(
            main_module,
            "_run_application",
        ) as run_application,
        patch.object(
            main_module.traceback,
            "print_exc",
        ) as print_exc,
    ):
        main_module.main()

    show_error.assert_called_once_with()
    run_application.assert_not_called()
    print_exc.assert_called_once_with()


def test_main_stops_when_migration_fails(
    tmp_path: Path,
) -> None:
    """DB移行失敗時は空DBを作らず通常起動しない。"""
    paths = create_paths(tmp_path)
    migration_error = RuntimeError("migration failed")

    with (
        patch.object(
            main_module,
            "create_application_paths",
            return_value=paths,
        ),
        patch.object(main_module, "DataMigrationService"),
        patch.object(
            main_module,
            "try_migrate_data",
            return_value=(None, migration_error),
        ),
        patch.object(
            main_module,
            "_show_fatal_startup_error",
        ) as show_error,
        patch.object(
            main_module,
            "_run_application",
        ) as run_application,
    ):
        main_module.main()

    show_error.assert_called_once_with()
    run_application.assert_not_called()
    assert not paths.database_path.exists()


def test_main_passes_migration_result_to_application(
    tmp_path: Path,
) -> None:
    """移行結果と新保存先を通常起動処理へ渡す。"""
    paths = create_paths(tmp_path)
    result = DataMigrationResult(
        status=DataMigrationStatus.NO_LEGACY_DATA,
        source_database_path=None,
        destination_database_path=paths.database_path,
    )
    migration_service = Mock()

    with (
        patch.object(
            main_module,
            "create_application_paths",
            return_value=paths,
        ),
        patch.object(
            main_module,
            "DataMigrationService",
            return_value=migration_service,
        ) as service_class,
        patch.object(
            main_module,
            "try_migrate_data",
            return_value=(result, None),
        ) as migrate,
        patch.object(
            main_module,
            "_run_application",
        ) as run_application,
    ):
        main_module.main()

    service_class.assert_called_once_with(
        application_paths=paths,
        legacy_root_directory=(
            main_module._get_legacy_root_directory()
        ),
    )
    migrate.assert_called_once_with(migration_service)
    run_application.assert_called_once_with(paths, result)


def test_run_application_injects_new_paths(
    tmp_path: Path,
) -> None:
    """新保存先をDB、バックアップ、表紙画像へ注入する。"""
    paths = create_paths(tmp_path)
    root = Mock()
    session = Mock()
    repository = Mock()
    reading_history_repository = Mock()
    backup_service = Mock()
    cover_service = Mock()
    book_service = Mock()

    with (
        patch.object(
            main_module,
            "initialize_database",
        ) as initialize_database,
        patch.object(
            main_module,
            "BackupService",
            return_value=backup_service,
        ) as backup_class,
        patch.object(
            main_module,
            "try_create_backup",
            return_value=None,
        ),
        patch.object(
            main_module,
            "BookRepository",
            return_value=repository,
        ) as repository_class,
        patch.object(
            main_module,
            "ReadingHistoryRepository",
            return_value=reading_history_repository,
        ) as reading_repository_class,
        patch.object(
            main_module.requests,
            "Session",
            return_value=session,
        ),
        patch.object(main_module, "GoogleBooksClient"),
        patch.object(main_module, "OpenBdClient"),
        patch.object(main_module, "BookMetadataService"),
        patch.object(
            main_module,
            "CoverImageService",
            return_value=cover_service,
        ) as cover_class,
        patch.object(
            main_module,
            "BookService",
            return_value=book_service,
        ),
        patch.object(main_module, "CsvExportService"),
        patch.object(main_module, "CsvImportService"),
        patch.object(main_module, "ReadingHistoryService"),
        patch.object(
            main_module.tk,
            "Tk",
            return_value=root,
        ),
        patch.object(main_module, "BookManagerApplication"),
    ):
        main_module._run_application(paths, None)

    initialize_database.assert_called_once_with(
        paths.database_path
    )
    backup_class.assert_called_once_with(
        database_path=paths.database_path,
        backup_directory=paths.backup_directory,
    )
    repository_class.assert_called_once_with(
        paths.database_path
    )
    reading_repository_class.assert_called_once_with(
        paths.database_path
    )
    cover_class.assert_called_once_with(
        session=session,
        cache_directory=paths.cover_cache_directory,
        root_directory=paths.root_directory,
    )
    root.mainloop.assert_called_once_with()
    session.close.assert_called_once_with()


def test_run_application_closes_session_when_mainloop_fails(
    tmp_path: Path,
) -> None:
    """GUIで例外が発生してもHTTP Sessionを閉じる。"""
    paths = create_paths(tmp_path)
    root = Mock()
    root.mainloop.side_effect = RuntimeError("GUI failed")
    session = Mock()

    with (
        patch.object(main_module, "initialize_database"),
        patch.object(main_module, "BackupService"),
        patch.object(
            main_module,
            "try_create_backup",
            return_value=None,
        ),
        patch.object(main_module, "BookRepository"),
        patch.object(main_module, "ReadingHistoryRepository"),
        patch.object(
            main_module.requests,
            "Session",
            return_value=session,
        ),
        patch.object(main_module, "GoogleBooksClient"),
        patch.object(main_module, "OpenBdClient"),
        patch.object(main_module, "BookMetadataService"),
        patch.object(main_module, "CoverImageService"),
        patch.object(main_module, "BookService"),
        patch.object(main_module, "CsvExportService"),
        patch.object(main_module, "CsvImportService"),
        patch.object(main_module, "ReadingHistoryService"),
        patch.object(
            main_module.tk,
            "Tk",
            return_value=root,
        ),
        patch.object(main_module, "BookManagerApplication"),
    ):
        try:
            main_module._run_application(paths, None)
        except RuntimeError as error:
            assert str(error) == "GUI failed"
        else:
            raise AssertionError("RuntimeError was not raised")

    session.close.assert_called_once_with()


def test_run_application_shows_backup_warning(
    tmp_path: Path,
) -> None:
    """バックアップ失敗時もGUIを起動して警告する。"""
    paths = create_paths(tmp_path)
    root = Mock()

    with (
        patch.object(main_module, "initialize_database"),
        patch.object(main_module, "BackupService"),
        patch.object(
            main_module,
            "try_create_backup",
            return_value=RuntimeError("backup failed"),
        ),
        patch.object(main_module, "BookRepository"),
        patch.object(main_module, "ReadingHistoryRepository"),
        patch.object(main_module.requests, "Session"),
        patch.object(main_module, "GoogleBooksClient"),
        patch.object(main_module, "OpenBdClient"),
        patch.object(main_module, "BookMetadataService"),
        patch.object(main_module, "CoverImageService"),
        patch.object(main_module, "BookService"),
        patch.object(main_module, "CsvExportService"),
        patch.object(main_module, "CsvImportService"),
        patch.object(main_module, "ReadingHistoryService"),
        patch.object(
            main_module.tk,
            "Tk",
            return_value=root,
        ),
        patch.object(main_module, "BookManagerApplication"),
        patch.object(
            main_module.messagebox,
            "showwarning",
        ) as showwarning,
    ):
        main_module._run_application(paths, None)

    showwarning.assert_called_once()
    assert showwarning.call_args.kwargs["parent"] is root
