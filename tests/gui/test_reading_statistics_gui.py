"""読書集計・可視化画面のGUIロジックを検証する。"""

from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)


def create_application() -> BookManagerApplication:
    """読書集計GUIテスト用Applicationを生成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._reading_history_service = Mock()
    application._reading_statistics_dialog = Mock()
    application._reading_statistics_year_var = Mock()
    application._reading_statistics_year_combobox = Mock()
    application._reading_statistics_summary_vars = {
        "total_history_count": Mock(),
        "books_with_history_count": Mock(),
        "completed_history_count": Mock(),
        "reread_book_count": Mock(),
    }
    application._reading_statistics_month_vars = [
        Mock() for _ in range(12)
    ]
    application._reading_statistics_canvas = Mock()
    application._monthly_reading_counts = []

    return application


def create_monthly_counts(
    *,
    year: int = 2026,
    january: int = 2,
    december: int = 1,
) -> list[MonthlyReadingCount]:
    """12か月分のテスト用集計を生成する。"""
    return [
        MonthlyReadingCount(
            year=year,
            month=month,
            completed_count=(
                january
                if month == 1
                else december
                if month == 12
                else 0
            ),
        )
        for month in range(1, 13)
    ]


def test_show_reading_statistics_opens_without_selected_book() -> None:
    """書籍の選択状態に関係なく読書集計画面を開く。"""
    application = create_application()
    application._selected_book_id = None
    application._open_reading_statistics_dialog = Mock()

    application._on_show_reading_statistics()

    application._open_reading_statistics_dialog.assert_called_once_with()


def test_set_reading_statistics_summary_formats_values() -> None:
    """全体集計値へ回数と冊数の単位を付ける。"""
    application = create_application()
    summary = ReadingStatisticsSummary(12, 8, 10, 3)

    application._set_reading_statistics_summary(summary)

    variables = application._reading_statistics_summary_vars
    variables["total_history_count"].set.assert_called_once_with(
        "12回"
    )
    variables["books_with_history_count"].set.assert_called_once_with(
        "8冊"
    )
    variables["completed_history_count"].set.assert_called_once_with(
        "10回"
    )
    variables["reread_book_count"].set.assert_called_once_with(
        "3冊"
    )


def test_load_reading_statistics_selects_latest_year() -> None:
    """全体集計を表示し、最新の対象年を初期選択する。"""
    application = create_application()
    summary = ReadingStatisticsSummary(12, 8, 10, 3)
    application._reading_history_service.get_statistics_summary.return_value = (
        summary
    )
    application._reading_history_service.get_completed_years.return_value = [
        2026,
        2025,
    ]
    application._set_reading_statistics_summary = Mock()
    application._refresh_monthly_reading_statistics = Mock()

    application._load_reading_statistics()

    application._set_reading_statistics_summary.assert_called_once_with(
        summary
    )
    application._reading_statistics_year_combobox.configure.assert_any_call(
        values=("2026", "2025"),
    )
    application._reading_statistics_year_combobox.configure.assert_any_call(
        state="readonly",
    )
    application._reading_statistics_year_var.set.assert_called_once_with(
        "2026"
    )
    application._refresh_monthly_reading_statistics.assert_called_once_with(
        2026
    )


def test_load_reading_statistics_displays_empty_state() -> None:
    """読了記録がない場合は対象年を無効化する。"""
    application = create_application()
    application._reading_history_service.get_statistics_summary.return_value = (
        ReadingStatisticsSummary(1, 1, 0, 0)
    )
    application._reading_history_service.get_completed_years.return_value = []
    application._set_monthly_reading_counts = Mock()

    application._load_reading_statistics()

    application._reading_statistics_year_var.set.assert_called_once_with("")
    application._reading_statistics_year_combobox.configure.assert_any_call(
        values=(),
    )
    application._reading_statistics_year_combobox.configure.assert_any_call(
        state="disabled",
    )
    application._set_monthly_reading_counts.assert_called_once_with([])


def test_year_changed_refreshes_selected_year() -> None:
    """対象年変更時に選択年の月別集計を更新する。"""
    application = create_application()
    application._reading_statistics_year_var.get.return_value = "2025"
    application._refresh_monthly_reading_statistics = Mock()

    application._on_reading_statistics_year_changed()

    application._refresh_monthly_reading_statistics.assert_called_once_with(
        2025
    )


def test_year_changed_handles_empty_value() -> None:
    """対象年が空の場合は空状態を表示する。"""
    application = create_application()
    application._reading_statistics_year_var.get.return_value = ""
    application._set_monthly_reading_counts = Mock()

    application._on_reading_statistics_year_changed()

    application._set_monthly_reading_counts.assert_called_once_with([])


def test_year_changed_displays_unexpected_error() -> None:
    """月別集計の予期しないエラーを利用者へ通知する。"""
    application = create_application()
    application._reading_statistics_year_var.get.return_value = "2026"
    application._refresh_monthly_reading_statistics = Mock(
        side_effect=RuntimeError("test error")
    )

    with (
        patch(
            "book_manager.gui.book_manager_application.traceback.print_exc"
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror"
        ) as showerror,
    ):
        application._on_reading_statistics_year_changed()

    showerror.assert_called_once_with(
        "読書集計エラー",
        "読書集計を表示できませんでした。",
        parent=application._reading_statistics_dialog,
    )


def test_refresh_monthly_reading_statistics_uses_service() -> None:
    """Serviceから指定年の月別集計を取得する。"""
    application = create_application()
    monthly_counts = create_monthly_counts()
    service = application._reading_history_service
    service.get_monthly_reading_counts.return_value = monthly_counts
    application._set_monthly_reading_counts = Mock()

    application._refresh_monthly_reading_statistics(2026)

    service.get_monthly_reading_counts.assert_called_once_with(2026)
    application._set_monthly_reading_counts.assert_called_once_with(
        monthly_counts
    )


def test_set_monthly_reading_counts_formats_all_months() -> None:
    """1月から12月までの数値を件数付きで表示する。"""
    application = create_application()
    monthly_counts = create_monthly_counts()
    application._draw_monthly_reading_chart = Mock()

    application._set_monthly_reading_counts(monthly_counts)

    month_vars = application._reading_statistics_month_vars
    month_vars[0].set.assert_called_once_with("1月 2件")
    month_vars[1].set.assert_called_once_with("2月 0件")
    month_vars[11].set.assert_called_once_with("12月 1件")
    assert application._monthly_reading_counts == monthly_counts
    application._draw_monthly_reading_chart.assert_called_once_with(
        application._reading_statistics_canvas,
        monthly_counts,
    )


def test_draw_monthly_reading_chart_displays_empty_message() -> None:
    """読了記録がない場合は空状態メッセージを描画する。"""
    canvas = Mock()
    canvas.winfo_width.return_value = 720
    canvas.winfo_height.return_value = 360

    BookManagerApplication._draw_monthly_reading_chart(
        canvas,
        create_monthly_counts(january=0, december=0),
    )

    canvas.delete.assert_called_once_with("all")
    canvas.create_rectangle.assert_not_called()
    assert canvas.create_text.call_args.kwargs["text"] == (
        "読了記録がありません。"
    )


def test_draw_monthly_reading_chart_draws_bars_and_labels() -> None:
    """件数がある月の棒と12か月分のラベルを描画する。"""
    canvas = Mock()
    canvas.winfo_width.return_value = 720
    canvas.winfo_height.return_value = 360
    monthly_counts = create_monthly_counts()

    BookManagerApplication._draw_monthly_reading_chart(
        canvas,
        monthly_counts,
    )

    assert canvas.create_rectangle.call_count == 2
    assert canvas.create_line.call_count == 2
    texts = [
        call.kwargs["text"]
        for call in canvas.create_text.call_args_list
    ]
    assert "1月" in texts
    assert "12月" in texts
    assert texts.count("0") == 10
    assert "2" in texts
    assert "1" in texts


def test_canvas_configure_redraws_current_counts() -> None:
    """Canvasのサイズ変更時に現在の集計値で再描画する。"""
    application = create_application()
    monthly_counts = create_monthly_counts()
    application._monthly_reading_counts = monthly_counts
    application._draw_monthly_reading_chart = Mock()

    application._on_reading_statistics_canvas_configure()

    application._draw_monthly_reading_chart.assert_called_once_with(
        application._reading_statistics_canvas,
        monthly_counts,
    )
