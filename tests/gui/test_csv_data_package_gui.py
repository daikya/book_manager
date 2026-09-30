"""Tests for complete CSV data package GUI operations."""

from pathlib import Path
from unittest.mock import Mock, call, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.csv_data_package import (
    CsvDataPackageExportResult,
    CsvDataPackageImportResult,
    CsvDataPackageIssue,
    CsvDataPackageIssueLevel,
    CsvDataPackageManifest,
    CsvDataPackagePreview,
)


def create_application() -> BookManagerApplication:
    """完全データ操作用の最小限のApplicationを返す。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication
    )
    application._root = Mock()
    application._csv_data_package_export_service = Mock()
    export_service = application._csv_data_package_export_service
    export_service.create_default_file_name.return_value = (
        "book_manager_data_20260930_140000.zip"
    )
    application._csv_data_package_preflight_service = Mock()
    application._csv_data_package_import_service = Mock()
    application._refresh_tag_options = Mock()
    application._load_all_books = Mock()
    return application


def create_preview(
    source_path: Path,
    *,
    issues: tuple[CsvDataPackageIssue, ...] = (),
) -> CsvDataPackagePreview:
    """GUI確認に必要な事前検査結果を返す。"""
    return CsvDataPackagePreview(
        source_path=source_path,
        source_size=100,
        source_modified_ns=200,
        source_sha256="a" * 64,
        manifest=CsvDataPackageManifest(
            application_version="2.6.0",
            database_schema_version=7,
            exported_at="2026-09-30 14:00:00",
            book_item_count=3,
            tag_count=2,
            book_item_tag_count=4,
            reading_history_count=5,
        ),
        issues=issues,
    )


def test_data_io_operations_are_grouped_in_one_row_menu() -> None:
    """4つの入出力操作を1段目のドロップダウンへまとめる。"""
    application = create_application()
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
        application._create_button_frame(Mock())

    data_io_calls = [
        (index, item)
        for index, item in enumerate(button_class.call_args_list)
        if item.kwargs.get("text") == "データ入出力 ▼"
    ]
    assert len(data_io_calls) == 1
    index, data_io_call = data_io_calls[0]
    assert data_io_call.kwargs["command"] == (
        application._show_data_io_menu
    )
    data_io_button = created_buttons[index]
    data_io_button.grid.assert_called_once_with(
        row=0,
        column=6,
        padx=(0, 6),
    )
    for button in created_buttons:
        assert button.grid.call_args.kwargs["row"] == 0


def test_show_data_io_menu_lists_four_operations() -> None:
    """データ入出力メニューへ既存CSVと完全データ操作を表示する。"""
    application = create_application()
    application._data_io_button = Mock()
    application._data_io_button.winfo_rootx.return_value = 100
    application._data_io_button.winfo_rooty.return_value = 200
    application._data_io_button.winfo_height.return_value = 30
    data_io_menu = Mock()

    with patch(
        "book_manager.gui.book_manager_application.tk.Menu",
        return_value=data_io_menu,
    ) as menu_class:
        application._show_data_io_menu()

    menu_class.assert_called_once_with(
        application._root,
        tearoff=False,
    )
    assert data_io_menu.add_command.call_args_list == [
        call(
            label="書籍一覧をCSVへエクスポート",
            command=application._on_export_csv,
        ),
        call(
            label="書籍一覧CSVをインポート",
            command=application._on_import_csv,
        ),
        call(
            label="完全データをZIPへエクスポート",
            command=application._on_export_csv_data_package,
        ),
        call(
            label="完全データZIPをインポート",
            command=application._on_import_csv_data_package,
        ),
    ]
    data_io_menu.add_separator.assert_called_once_with()
    data_io_menu.tk_popup.assert_called_once_with(100, 230)
    data_io_menu.grab_release.assert_called_once_with()


def test_export_package_does_nothing_when_selection_is_cancelled() -> None:
    """保存先選択をキャンセルした場合は出力しない。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application."
        "filedialog.asksaveasfilename",
        return_value="",
    ):
        application._on_export_csv_data_package()

    application._csv_data_package_export_service.export.assert_not_called()


def test_export_package_calls_service_and_shows_counts() -> None:
    """選択したZIPへ出力し、4種類の件数を表示する。"""
    application = create_application()
    output_path = Path("C:/temp/complete.zip")
    application._csv_data_package_export_service.export.return_value = (
        CsvDataPackageExportResult(
            output_path=output_path,
            book_item_count=3,
            tag_count=2,
            book_item_tag_count=4,
            reading_history_count=5,
        )
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.asksaveasfilename",
            return_value=str(output_path),
        ) as save_dialog,
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showinfo",
        ) as showinfo,
    ):
        application._on_export_csv_data_package()

    assert save_dialog.call_args.kwargs["initialfile"].endswith(".zip")
    application._csv_data_package_export_service.export.assert_called_once_with(
        output_path
    )
    message = showinfo.call_args.args[1]
    assert "書籍: 3件" in message
    assert "タグ: 2件" in message
    assert "書籍タグ関連: 4件" in message
    assert "読書履歴: 5件" in message


def test_export_package_shows_error_details() -> None:
    """出力失敗時は未完成ZIPが残らないことを表示する。"""
    application = create_application()
    application._csv_data_package_export_service.export.side_effect = (
        OSError("保存失敗")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.asksaveasfilename",
            return_value="C:/temp/complete.zip",
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
    ):
        application._on_export_csv_data_package()

    message = showerror.call_args.args[1]
    assert "未完成のZIPを残していません" in message
    assert "保存失敗" in message


def test_import_package_does_nothing_when_selection_is_cancelled() -> None:
    """ZIP選択をキャンセルした場合は事前検査しない。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application."
        "filedialog.askopenfilename",
        return_value="",
    ):
        application._on_import_csv_data_package()

    application._csv_data_package_preflight_service.preview.assert_not_called()
    application._csv_data_package_import_service.import_preview.assert_not_called()


def test_import_package_rejects_preflight_errors() -> None:
    """事前検査エラーがある場合は実行確認へ進まない。"""
    application = create_application()
    source_path = Path("C:/temp/complete.zip")
    preview = create_preview(
        source_path,
        issues=(
            CsvDataPackageIssue(
                level=CsvDataPackageIssueLevel.ERROR,
                file_name="book_item_tags.csv",
                row_number=3,
                column_name="tag_key",
                message="参照先のタグが存在しません。",
            ),
        ),
    )
    application._csv_data_package_preflight_service.preview.return_value = (
        preview
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=str(source_path),
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
        ) as askyesno,
    ):
        application._on_import_csv_data_package()

    message = showerror.call_args.args[1]
    assert "book_item_tags.csv 3行目 tag_key" in message
    assert "参照先のタグが存在しません" in message
    askyesno.assert_not_called()
    application._csv_data_package_import_service.import_preview.assert_not_called()


def test_import_package_warning_can_be_cancelled() -> None:
    """警告を含む正常データでも利用者が実行を中止できる。"""
    application = create_application()
    source_path = Path("C:/temp/complete.zip")
    preview = create_preview(
        source_path,
        issues=(
            CsvDataPackageIssue(
                level=CsvDataPackageIssueLevel.WARNING,
                file_name="book_items.csv",
                row_number=2,
                message="確認が必要です。",
            ),
        ),
    )
    application._csv_data_package_preflight_service.preview.return_value = (
        preview
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=str(source_path),
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=False,
        ) as askyesno,
    ):
        application._on_import_csv_data_package()

    message = askyesno.call_args.args[1]
    assert "【警告】" in message
    assert "空のデータベースだけ" in message
    application._csv_data_package_import_service.import_preview.assert_not_called()


def test_import_package_restores_and_refreshes_screen() -> None:
    """確認後に復元し、一覧とタグ候補を再読込する。"""
    application = create_application()
    source_path = Path("C:/temp/complete.zip")
    preview = create_preview(source_path)
    backup_path = Path("C:/temp/backups/before.db")
    application._csv_data_package_preflight_service.preview.return_value = (
        preview
    )
    application._csv_data_package_import_service.import_preview.return_value = (
        CsvDataPackageImportResult(
            book_item_count=3,
            tag_count=2,
            book_item_tag_count=4,
            reading_history_count=5,
            backup_path=backup_path,
        )
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=str(source_path),
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showinfo",
        ) as showinfo,
    ):
        application._on_import_csv_data_package()

    application._csv_data_package_preflight_service.preview.assert_called_once_with(
        source_path
    )
    application._csv_data_package_import_service.import_preview.assert_called_once_with(
        preview
    )
    application._refresh_tag_options.assert_called_once_with()
    application._load_all_books.assert_called_once_with()
    message = showinfo.call_args.args[1]
    assert str(backup_path) in message
    assert "読書履歴: 5件" in message


def test_import_package_shows_preflight_exception() -> None:
    """ZIPの安全検査例外を利用者へ表示する。"""
    application = create_application()
    application._csv_data_package_preflight_service.preview.side_effect = (
        ValueError("必須ファイルが不足しています。")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value="C:/temp/complete.zip",
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
    ):
        application._on_import_csv_data_package()

    assert "必須ファイルが不足" in showerror.call_args.args[1]
    application._csv_data_package_import_service.import_preview.assert_not_called()


def test_import_package_shows_execution_failure_without_refresh() -> None:
    """復元失敗時は画面を再読込せずロールバック済みと表示する。"""
    application = create_application()
    source_path = Path("C:/temp/complete.zip")
    preview = create_preview(source_path)
    application._csv_data_package_preflight_service.preview.return_value = (
        preview
    )
    application._csv_data_package_import_service.import_preview.side_effect = (
        ValueError("データベースが空ではありません。")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=str(source_path),
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
    ):
        application._on_import_csv_data_package()

    application._refresh_tag_options.assert_not_called()
    application._load_all_books.assert_not_called()
    message = showerror.call_args.args[1]
    assert "変更は保存されていません" in message
    assert "データベースが空ではありません" in message


def test_preview_message_limits_issue_details() -> None:
    """大量のIssueは先頭20件と残件数だけを表示する。"""
    issues = tuple(
        CsvDataPackageIssue(
            level=CsvDataPackageIssueLevel.ERROR,
            file_name="book_items.csv",
            row_number=index + 2,
            message=f"エラー{index}",
        )
        for index in range(22)
    )
    preview = create_preview(Path("package.zip"), issues=issues)

    message = BookManagerApplication._format_csv_data_package_preview(
        preview
    )

    assert "エラー19" in message
    assert "エラー20" not in message
    assert "ほか2件" in message
