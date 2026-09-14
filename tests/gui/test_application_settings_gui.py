"""アプリケーション設定画面のGUIロジックを検証する。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.application_settings import (
    ApplicationSettingsSnapshot,
    BackupSettingsSnapshot,
)
from book_manager.models.backup_settings import BackupSettings
from book_manager.services.application_settings_service import (
    ApplicationSettingsError,
    DirectoryOpenError,
)


def create_snapshot(
    tmp_path: Path,
    *,
    api_key_is_configured: bool = True,
) -> ApplicationSettingsSnapshot:
    """設定画面用のSnapshotを生成する。"""
    root_directory = tmp_path / "book_manager"

    return ApplicationSettingsSnapshot(
        google_books_api_key_is_configured=(
            api_key_is_configured
        ),
        application_name="Book Manager",
        application_version="2.1.0",
        root_directory=root_directory,
        database_path=root_directory / "data" / "books.db",
        backup_directory=root_directory / "backups",
        cover_cache_directory=(
            root_directory
            / "cache"
            / "covers"
        ),
        log_path=(
            root_directory
            / "logs"
            / "book_manager.log"
        ),
    )


def create_backup_snapshot(
    tmp_path: Path,
    *,
    latest: bool = False,
    pending: bool = False,
) -> BackupSettingsSnapshot:
    """設定画面用のバックアップ表示値。"""
    directory = tmp_path / "backups"
    return BackupSettingsSnapshot(
        active_settings=BackupSettings(),
        saved_settings=(BackupSettings(48, 3) if pending else BackupSettings()),
        backup_directory=directory,
        backup_count=1 if latest else 0,
        latest_backup_path=(
            directory / "books_20260914_090000.db" if latest else None
        ),
        latest_backup_datetime=(
            datetime(2026, 9, 14, 9) if latest else None
        ),
    )


def create_application() -> BookManagerApplication:
    """設定画面テスト用Applicationを生成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._application_settings_service = Mock()
    application._on_google_books_api_key_changed = Mock()

    return application


def test_create_button_frame_adds_settings_button() -> None:
    """メイン画面の操作領域へ設定ボタンを追加する。"""
    application = create_application()
    parent = Mock()
    button_frame = Mock()
    created_buttons: list[Mock] = []

    def create_button(*_args: object, **_kwargs: object) -> Mock:
        button = Mock()
        created_buttons.append(button)
        return button

    with (
        patch(
            "book_manager.gui.book_manager_application.ttk.Frame",
            return_value=button_frame,
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.Button",
            side_effect=create_button,
        ) as button_class,
    ):
        application._create_button_frame(parent)

    settings_calls = [
        item
        for item in button_class.call_args_list
        if item.kwargs.get("text") == "設定"
    ]
    assert len(settings_calls) == 1
    assert settings_calls[0].kwargs["command"] == (
        application._on_open_settings
    )
    application._settings_button.grid.assert_called_once_with(
        row=0,
        column=12,
        padx=(0, 6),
    )
    application._exit_button.grid.assert_called_once_with(
        row=0,
        column=13,
        sticky="e",
    )
    button_frame.columnconfigure.assert_called_once_with(
        13,
        weight=1,
    )


def test_open_settings_displays_snapshot_and_centers_dialog(
    tmp_path: Path,
) -> None:
    """Snapshotを表示する設定画面を中央へ配置する。"""
    application = create_application()
    snapshot = create_snapshot(tmp_path)
    application._application_settings_service.get_snapshot.return_value = (
        snapshot
    )
    application._application_settings_service.get_backup_settings_snapshot.return_value = (
        create_backup_snapshot(tmp_path)
    )
    application._create_settings_path_row = Mock()
    application._wait_for_dialog = Mock()
    dialog = Mock()
    api_key_variable = Mock()
    status_variable = Mock()
    string_variable = MagicMock(
        side_effect=(
            api_key_variable, status_variable,
            Mock(), Mock(), Mock(), Mock(), Mock(),
        ),
    )

    with (
        patch(
            "book_manager.gui.book_manager_application.tk.Toplevel",
            return_value=dialog,
        ),
        patch(
            "book_manager.gui.book_manager_application.tk.StringVar",
            string_variable,
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.LabelFrame",
            side_effect=lambda *_args, **_kwargs: Mock(),
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.Frame",
            side_effect=lambda *_args, **_kwargs: Mock(),
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.Label",
            side_effect=lambda *_args, **_kwargs: Mock(),
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.Entry",
            side_effect=lambda *_args, **_kwargs: Mock(),
        ),
        patch(
            "book_manager.gui.book_manager_application.ttk.Button",
            side_effect=lambda *_args, **_kwargs: Mock(),
        ),
    ):
        application._on_open_settings()

    assert string_variable.call_args_list[:2] == [
        call(master=dialog),
        call(master=dialog, value="設定済み"),
    ]
    api_key_variable.get.assert_not_called()
    assert application._create_settings_path_row.call_count == 4
    application._wait_for_dialog.assert_called_once_with(dialog)
    dialog.title.assert_called_once_with("設定")
    dialog.transient.assert_called_once_with(application._root)
    dialog.grab_set.assert_called_once_with()


def test_open_settings_shows_snapshot_error() -> None:
    """設定状態を取得できない場合は画面を生成しない。"""
    application = create_application()
    application._application_settings_service.get_snapshot.side_effect = (
        ApplicationSettingsError("設定状態を取得できません。")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application.tk.Toplevel",
        ) as toplevel,
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
    ):
        application._on_open_settings()

    toplevel.assert_not_called()
    showerror.assert_called_once_with(
        "設定エラー",
        "設定状態を取得できません。",
        parent=application._root,
    )


def test_open_settings_shows_backup_snapshot_error(tmp_path: Path) -> None:
    """バックアップ状態を取得できなければ設定画面を開かない。"""
    app = create_application()
    app._application_settings_service.get_snapshot.return_value = (
        create_snapshot(tmp_path)
    )
    app._application_settings_service.get_backup_settings_snapshot.side_effect = (
        ApplicationSettingsError("backup read failed")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application.tk.Toplevel"
        ) as toplevel,
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror"
        ) as showerror,
    ):
        app._on_open_settings()

    toplevel.assert_not_called()
    showerror.assert_called_once_with(
        "設定エラー", "backup read failed", parent=app._root,
    )


def test_save_google_books_api_key_updates_client_and_view() -> None:
    """保存後にクライアントと画面表示を更新する。"""
    application = create_application()
    settings_service = application._application_settings_service
    settings_service.save_google_books_api_key.return_value = (
        "normalized-key"
    )
    api_key_variable = Mock()
    api_key_variable.get.return_value = "  normalized-key  "
    status_variable = Mock()
    dialog = Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo",
    ) as showinfo:
        application._save_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    settings_service.save_google_books_api_key.assert_called_once_with(
        "  normalized-key  "
    )
    application._on_google_books_api_key_changed.assert_called_once_with(
        "normalized-key"
    )
    api_key_variable.set.assert_called_once_with("")
    status_variable.set.assert_called_once_with("設定済み")
    showinfo.assert_called_once()


def test_save_google_books_api_key_shows_service_error() -> None:
    """APIキーの保存失敗を表示して画面状態を変えない。"""
    application = create_application()
    settings_service = application._application_settings_service
    settings_service.save_google_books_api_key.side_effect = (
        ApplicationSettingsError("APIキーを保存できません。")
    )
    api_key_variable = Mock()
    api_key_variable.get.return_value = "secret-key"
    status_variable = Mock()
    dialog = Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror",
    ) as showerror:
        application._save_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    showerror.assert_called_once_with(
        "設定エラー",
        "APIキーを保存できません。",
        parent=dialog,
    )
    application._on_google_books_api_key_changed.assert_not_called()
    api_key_variable.set.assert_not_called()
    status_variable.set.assert_not_called()


def test_save_google_books_api_key_warns_when_client_update_fails(
) -> None:
    """即時反映に失敗した場合は再起動を案内する。"""
    application = create_application()
    settings_service = application._application_settings_service
    settings_service.save_google_books_api_key.return_value = (
        "normalized-key"
    )
    application._on_google_books_api_key_changed.side_effect = (
        RuntimeError("client update failed")
    )
    api_key_variable = Mock()
    api_key_variable.get.return_value = "normalized-key"
    status_variable = Mock()
    dialog = Mock()

    with (
        patch(
            "book_manager.gui.book_manager_application.traceback.print_exc",
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showwarning",
        ) as showwarning,
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ) as showinfo,
    ):
        application._save_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    api_key_variable.set.assert_called_once_with("")
    status_variable.set.assert_called_once_with("設定済み")
    showwarning.assert_called_once()
    assert "再起動" in showwarning.call_args.args[1]
    showinfo.assert_not_called()


def test_delete_google_books_api_key_reports_unconfigured(
    tmp_path: Path,
) -> None:
    """APIキーが未設定の場合は削除確認を表示しない。"""
    application = create_application()
    application._application_settings_service.get_snapshot.return_value = (
        create_snapshot(
            tmp_path,
            api_key_is_configured=False,
        )
    )
    api_key_variable = Mock()
    status_variable = Mock()
    dialog = Mock()

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ) as showinfo,
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
        ) as askyesno,
    ):
        application._delete_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    showinfo.assert_called_once()
    askyesno.assert_not_called()
    settings_service = application._application_settings_service
    settings_service.delete_google_books_api_key.assert_not_called()


def test_delete_google_books_api_key_cancels(
    tmp_path: Path,
) -> None:
    """削除確認を取り消した場合はAPIキーを削除しない。"""
    application = create_application()
    application._application_settings_service.get_snapshot.return_value = (
        create_snapshot(tmp_path)
    )

    with patch(
        "book_manager.gui.book_manager_application.messagebox.askyesno",
        return_value=False,
    ):
        application._delete_google_books_api_key(
            Mock(),
            Mock(),
            Mock(),
        )

    settings_service = application._application_settings_service
    settings_service.delete_google_books_api_key.assert_not_called()
    application._on_google_books_api_key_changed.assert_not_called()


def test_delete_google_books_api_key_updates_client_and_view(
    tmp_path: Path,
) -> None:
    """削除後にクライアントと画面表示を更新する。"""
    application = create_application()
    settings_service = application._application_settings_service
    application._application_settings_service.get_snapshot.return_value = (
        create_snapshot(tmp_path)
    )
    api_key_variable = Mock()
    status_variable = Mock()
    dialog = Mock()

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ) as showinfo,
    ):
        application._delete_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    settings_service.delete_google_books_api_key.assert_called_once_with()
    application._on_google_books_api_key_changed.assert_called_once_with(
        None
    )
    api_key_variable.set.assert_called_once_with("")
    status_variable.set.assert_called_once_with("未設定")
    showinfo.assert_called_once()


def test_delete_google_books_api_key_shows_service_error(
    tmp_path: Path,
) -> None:
    """APIキーの削除失敗を表示して画面状態を変えない。"""
    application = create_application()
    settings_service = application._application_settings_service
    application._application_settings_service.get_snapshot.return_value = (
        create_snapshot(tmp_path)
    )
    settings_service.delete_google_books_api_key.side_effect = (
        ApplicationSettingsError("APIキーを削除できません。")
    )
    api_key_variable = Mock()
    status_variable = Mock()
    dialog = Mock()

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror",
        ) as showerror,
    ):
        application._delete_google_books_api_key(
            api_key_variable,
            status_variable,
            dialog,
        )

    showerror.assert_called_once_with(
        "設定エラー",
        "APIキーを削除できません。",
        parent=dialog,
    )
    application._on_google_books_api_key_changed.assert_not_called()
    api_key_variable.set.assert_not_called()
    status_variable.set.assert_not_called()


def test_open_settings_directory_uses_service(
    tmp_path: Path,
) -> None:
    """選択したフォルダーを設定Serviceで開く。"""
    application = create_application()
    directory = tmp_path / "backups"
    dialog = Mock()

    application._open_settings_directory(directory, dialog)

    settings_service = application._application_settings_service
    settings_service.open_directory.assert_called_once_with(
        directory
    )


def test_open_settings_directory_shows_error(
    tmp_path: Path,
) -> None:
    """フォルダーを開けない場合はエラーを表示する。"""
    application = create_application()
    application._application_settings_service.open_directory.side_effect = (
        DirectoryOpenError("フォルダーを開けません。")
    )
    directory = tmp_path / "logs"
    dialog = Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror",
    ) as showerror:
        application._open_settings_directory(directory, dialog)

    showerror.assert_called_once_with(
        "フォルダーエラー",
        "フォルダーを開けません。",
        parent=dialog,
    )


def test_backup_status_displays_empty_and_pending_values(tmp_path: Path) -> None:
    """空状態と次回起動待ちの設定を区別して表示する。"""
    last, count, active = Mock(), Mock(), Mock()

    BookManagerApplication._set_backup_settings_view(
        create_backup_snapshot(tmp_path, pending=True), last, count, active,
    )

    last.set.assert_called_once_with("バックアップなし")
    count.set.assert_called_once_with("0件")
    assert "次回起動" in active.set.call_args.args[0]


def test_backup_status_displays_latest_file(tmp_path: Path) -> None:
    """日時とファイル名を画面へ反映する。"""
    last, count, active = Mock(), Mock(), Mock()

    BookManagerApplication._set_backup_settings_view(
        create_backup_snapshot(tmp_path, latest=True), last, count, active,
    )

    assert "2026/09/14 09:00:00" in last.set.call_args.args[0]
    assert "books_20260914_090000.db" in last.set.call_args.args[0]
    count.set.assert_called_once_with("1件")


def test_save_backup_settings_refreshes_view(tmp_path: Path) -> None:
    """保存後の情報をServiceから再取得して表示する。"""
    app = create_application()
    interval, generations = Mock(), Mock()
    interval.get.return_value = "48"
    generations.get.return_value = "3"
    app._refresh_backup_settings_view = Mock(return_value=True)
    last, count, active, dialog = Mock(), Mock(), Mock(), Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo"
    ) as showinfo:
        app._save_backup_settings(
            interval, generations, last, count, active, dialog,
        )

    app._application_settings_service.save_backup_settings.assert_called_once_with(
        "48", "3"
    )
    app._refresh_backup_settings_view.assert_called_once_with(
        last, count, active, dialog,
    )
    assert "次回起動" in showinfo.call_args.args[1]


def test_save_backup_settings_keeps_input_on_failure() -> None:
    app = create_application()
    app._application_settings_service.save_backup_settings.side_effect = (
        ApplicationSettingsError("invalid value")
    )
    app._refresh_backup_settings_view = Mock()
    interval, generations = Mock(), Mock()
    interval.get.return_value = "0"
    generations.get.return_value = "10"

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror"
    ) as showerror:
        app._save_backup_settings(
            interval, generations, Mock(), Mock(), Mock(), Mock(),
        )

    showerror.assert_called_once()
    app._refresh_backup_settings_view.assert_not_called()
    interval.set.assert_not_called()


def test_manual_backup_disables_button_and_refreshes(tmp_path: Path) -> None:
    app = create_application()
    app._refresh_backup_settings_view = Mock(return_value=True)
    target = tmp_path / "books.db"
    button = Mock()
    app._application_settings_service.create_backup_now.return_value = target
    last, count, active, dialog = Mock(), Mock(), Mock(), Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo"
    ) as showinfo:
        app._create_backup_from_settings(
            button, last, count, active, dialog,
        )

    assert button.configure.call_args_list == [
        call(state="disabled"), call(state="normal"),
    ]
    app._refresh_backup_settings_view.assert_called_once_with(
        last, count, active, dialog,
    )
    assert str(target) in showinfo.call_args.args[1]


def test_manual_backup_reports_missing_database() -> None:
    app = create_application()
    button = Mock()
    app._application_settings_service.create_backup_now.return_value = None
    app._refresh_backup_settings_view = Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showwarning"
    ) as showwarning:
        app._create_backup_from_settings(
            button, Mock(), Mock(), Mock(), Mock(),
        )

    showwarning.assert_called_once()
    button.configure.assert_any_call(state="normal")
    app._refresh_backup_settings_view.assert_not_called()


def test_manual_backup_failure_reenables_button() -> None:
    app = create_application()
    button = Mock()
    app._application_settings_service.create_backup_now.side_effect = (
        ApplicationSettingsError("backup failed")
    )

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror"
    ) as showerror:
        app._create_backup_from_settings(
            button, Mock(), Mock(), Mock(), Mock(),
        )

    showerror.assert_called_once()
    assert button.configure.call_args_list[-1] == call(state="normal")
