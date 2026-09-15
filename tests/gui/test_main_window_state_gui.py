"""メインウィンドウ状態の復元・保存に関するGUIロジックテスト。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from book_manager.config.window_state_store import WindowStateStoreError
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.gui.window_positioning import (
    ScreenWorkArea,
    WindowRectangle,
)
from book_manager.models.window_state import WindowState


PRIMARY = ScreenWorkArea(0, 0, 1920, 1040, True)
LEFT = ScreenWorkArea(-1920, 0, 0, 1040, False)


def _create_application(
    saved_state: WindowState | None = None,
) -> tuple[BookManagerApplication, Mock, Mock]:
    application = BookManagerApplication.__new__(BookManagerApplication)
    root = Mock()
    store = Mock()
    store.load.return_value = saved_state
    application._root = root
    application._window_state_store = store
    application._last_normal_rectangle = None
    application._window_state_save_suppressed = False
    return application, root, store


def test_configure_root_restores_saved_rectangle() -> None:
    """保存された通常矩形を復元する。"""
    saved = WindowState(-1700, 100, 1350, 800, False)
    application, root, store = _create_application(saved)

    with patch(
        "book_manager.gui.book_manager_application.get_screen_work_areas",
        return_value=(PRIMARY, LEFT),
    ):
        application._configure_root()

    root.geometry.assert_called_once_with("1350x800-1700+100")
    root.state.assert_not_called()
    store.load.assert_called_once_with()


def test_configure_root_restores_maximized_after_normal_geometry() -> None:
    """通常矩形を設定してから最大化状態を復元する。"""
    saved = WindowState(200, 100, 1350, 800, True)
    application, root, _ = _create_application(saved)

    with patch(
        "book_manager.gui.book_manager_application.get_screen_work_areas",
        return_value=(PRIMARY,),
    ):
        application._configure_root()

    root.geometry.assert_called_once_with("1350x800+200+100")
    root.update_idletasks.assert_called_once_with()
    root.state.assert_called_once_with("zoomed")


def test_configure_root_uses_centered_default_without_saved_state() -> None:
    """保存状態がない場合は既定サイズで主モニター中央へ配置する。"""
    application, root, _ = _create_application()

    with patch(
        "book_manager.gui.book_manager_application.get_screen_work_areas",
        return_value=(PRIMARY,),
    ):
        application._configure_root()

    root.geometry.assert_called_once_with("1350x800+285+120")


def test_configure_root_uses_effective_minimum_on_small_screen() -> None:
    """小さい作業領域では最小サイズを画面内へ縮める。"""
    small = ScreenWorkArea(0, 0, 1024, 600, True)
    application, root, _ = _create_application()

    with patch(
        "book_manager.gui.book_manager_application.get_screen_work_areas",
        return_value=(small,),
    ):
        application._configure_root()

    root.geometry.assert_called_once_with("1024x600+0+0")
    root.minsize.assert_called_once_with(1024, 600)


def test_configure_root_registers_configure_event() -> None:
    """通常矩形を追跡するConfigureイベントを登録する。"""
    application, root, _ = _create_application()

    with patch(
        "book_manager.gui.book_manager_application.get_screen_work_areas",
        return_value=(PRIMARY,),
    ):
        application._configure_root()

    root.bind.assert_called_once_with(
        "<Configure>",
        application._on_root_configure,
        add="+",
    )


def test_configure_event_updates_normal_rectangle_in_memory() -> None:
    """通常表示時の位置とサイズをメモリだけへ反映する。"""
    application, root, store = _create_application()
    root.state.return_value = "normal"
    root.winfo_x.return_value = -1500
    root.winfo_y.return_value = 120
    root.winfo_width.return_value = 1400
    root.winfo_height.return_value = 850

    application._on_root_configure(SimpleNamespace(widget=root))

    assert application._last_normal_rectangle == WindowRectangle(
        -1500,
        120,
        1400,
        850,
    )
    store.save.assert_not_called()


def test_configure_event_ignores_child_widget() -> None:
    """子ウィジェット由来のConfigureイベントを無視する。"""
    application, _, _ = _create_application()

    application._on_root_configure(SimpleNamespace(widget=Mock()))

    assert application._last_normal_rectangle is None


def test_configure_event_does_not_replace_rectangle_while_maximized() -> None:
    """最大化中の矩形で通常矩形を上書きしない。"""
    application, root, _ = _create_application()
    expected = WindowRectangle(200, 100, 1350, 800)
    application._last_normal_rectangle = expected
    root.state.return_value = "zoomed"

    application._on_root_configure(SimpleNamespace(widget=root))

    assert application._last_normal_rectangle == expected


def test_exit_saves_latest_normal_rectangle_once() -> None:
    """終了時に最新の通常矩形を一度保存して破棄する。"""
    application, root, store = _create_application()
    application._last_normal_rectangle = WindowRectangle(10, 20, 1200, 700)
    root.state.return_value = "normal"
    root.winfo_x.return_value = 30
    root.winfo_y.return_value = 40
    root.winfo_width.return_value = 1300
    root.winfo_height.return_value = 750

    application._on_exit()

    store.save.assert_called_once_with(WindowState(30, 40, 1300, 750, False))
    root.destroy.assert_called_once_with()


def test_exit_saves_last_normal_rectangle_as_maximized() -> None:
    """最大化終了時は最後の通常矩形と最大化状態を保存する。"""
    application, root, store = _create_application()
    application._last_normal_rectangle = WindowRectangle(10, 20, 1200, 700)
    root.state.return_value = "zoomed"

    application._on_exit()

    store.save.assert_called_once_with(WindowState(10, 20, 1200, 700, True))
    root.destroy.assert_called_once_with()


def test_exit_does_not_save_when_suppressed() -> None:
    """リセット後の保存抑止中は状態ファイルを再作成しない。"""
    application, root, store = _create_application()
    application._last_normal_rectangle = WindowRectangle(10, 20, 1200, 700)
    application._window_state_save_suppressed = True

    application._on_exit()

    store.save.assert_not_called()
    root.destroy.assert_called_once_with()


def test_exit_continues_when_save_fails() -> None:
    """状態保存に失敗してもウィンドウを破棄する。"""
    application, root, store = _create_application()
    application._last_normal_rectangle = WindowRectangle(10, 20, 1200, 700)
    root.state.return_value = "zoomed"
    store.save.side_effect = WindowStateStoreError("save failed")

    with patch(
        "book_manager.gui.book_manager_application.logger.warning"
    ) as warning:
        application._on_exit()

    warning.assert_called_once()
    root.destroy.assert_called_once_with()
