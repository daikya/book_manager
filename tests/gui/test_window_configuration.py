"""メインウィンドウ設定に関するGUIロジックのテスト。"""

from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)


def create_application() -> BookManagerApplication:
    """テスト用のBookManagerApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._root = Mock()

    return application


def test_configure_root_centers_window() -> None:
    """メインウィンドウを画面中央へ配置する。"""
    application = create_application()

    with patch.object(
        application,
        "_get_available_screen_size",
        return_value=(1920, 1040),
    ):
        application._configure_root()

    application._root.geometry.assert_called_once_with(
        "1350x800+285+120"
    )


def test_configure_root_does_not_use_negative_position() -> None:
    """画面がウィンドウより小さい場合も負の位置にしない。"""
    application = create_application()

    with patch.object(
        application,
        "_get_available_screen_size",
        return_value=(1280, 680),
    ):
        application._configure_root()

    application._root.geometry.assert_called_once_with(
        "1350x800+0+0"
    )


def test_configure_root_sets_minimum_size() -> None:
    """メインウィンドウの最小サイズを設定する。"""
    application = create_application()

    with patch.object(
        application,
        "_get_available_screen_size",
        return_value=(1920, 1040),
    ):
        application._configure_root()

    application._root.minsize.assert_called_once_with(
        1150,
        650,
    )


def test_get_available_screen_size_uses_tkinter_on_non_windows() -> None:
    """Windows以外ではTkinterの画面サイズを使用する。"""
    application = create_application()

    application._root.winfo_screenwidth.return_value = 1920
    application._root.winfo_screenheight.return_value = 1080

    with patch(
        "book_manager.gui.book_manager_application.sys.platform",
        "linux",
    ):
        result = application._get_available_screen_size()

    assert result == (
        1920,
        1080,
    )


def test_get_available_screen_size_uses_windows_work_area() -> None:
    """Windowsではタスクバーを除いた作業領域を使用する。"""
    application = create_application()

    def set_work_area(
        action: int,
        parameter: int,
        rect_pointer: object,
        flags: int,
    ) -> int:
        del action
        del parameter
        del flags

        rect = rect_pointer._obj
        rect.left = 0
        rect.top = 0
        rect.right = 1920
        rect.bottom = 1040

        return 1

    system_parameters_info = Mock(
        side_effect=set_work_area,
    )

    mock_user32 = Mock()
    mock_user32.SystemParametersInfoW = (
        system_parameters_info
    )

    mock_windll = Mock()
    mock_windll.user32 = mock_user32

    with (
        patch(
            "book_manager.gui.book_manager_application.sys.platform",
            "win32",
        ),
        patch(
            "book_manager.gui.book_manager_application.ctypes.windll",
            mock_windll,
        ),
    ):
        result = application._get_available_screen_size()

    assert result == (
        1920,
        1040,
    )

    system_parameters_info.assert_called_once()


def test_get_available_screen_size_falls_back_when_windows_api_fails() -> None:
    """Windows API取得失敗時はTkinterの画面サイズへ戻す。"""
    application = create_application()

    application._root.winfo_screenwidth.return_value = 1920
    application._root.winfo_screenheight.return_value = 1080

    mock_user32 = Mock()
    mock_user32.SystemParametersInfoW.return_value = 0

    mock_windll = Mock()
    mock_windll.user32 = mock_user32

    with (
        patch(
            "book_manager.gui.book_manager_application.sys.platform",
            "win32",
        ),
        patch(
            "book_manager.gui.book_manager_application.ctypes.windll",
            mock_windll,
        ),
    ):
        result = application._get_available_screen_size()

    assert result == (
        1920,
        1080,
    )
