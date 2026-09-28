"""Tkinterサブウィンドウ配置処理のテスト。"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from book_manager.gui.window_positioning import (
    ScreenWorkArea,
    ScreenSize,
    WindowRectangle,
    calculate_centered_position,
    calculate_centered_position_in_work_area,
    center_window_on_parent,
)


@pytest.fixture(autouse=True)
def use_test_work_area():
    """OSに依存しない主モニター作業領域を使用する。"""
    with patch(
        "book_manager.gui.window_positioning.get_screen_work_areas",
        return_value=(ScreenWorkArea(0, 0, 1920, 1080, True),),
    ):
        yield


def test_calculate_centered_position_centers_on_parent() -> None:
    """通常位置の親ウィンドウ中央へ配置する。"""
    position = calculate_centered_position(
        parent=WindowRectangle(100, 80, 1000, 700),
        child_width=400,
        child_height=300,
        screen=ScreenSize(1920, 1080),
    )

    assert position == (400, 280)


def test_calculate_centered_position_uses_parent_origin() -> None:
    """親ウィンドウの画面上の原点を考慮する。"""
    position = calculate_centered_position(
        parent=WindowRectangle(350, 220, 800, 600),
        child_width=200,
        child_height=100,
        screen=ScreenSize(1920, 1080),
    )

    assert position == (650, 470)


def test_calculate_centered_position_uses_integer_floor() -> None:
    """親子サイズの差が奇数の場合も整数座標を返す。"""
    position = calculate_centered_position(
        parent=WindowRectangle(10, 10, 501, 401),
        child_width=200,
        child_height=100,
        screen=ScreenSize(1920, 1080),
    )

    assert position == (160, 160)


@pytest.mark.parametrize(
    ("parent", "expected"),
    (
        (WindowRectangle(-500, 200, 600, 500), (0, 300)),
        (WindowRectangle(300, -400, 600, 500), (400, 0)),
        (WindowRectangle(1800, 200, 600, 500), (1520, 300)),
        (WindowRectangle(300, 1000, 600, 500), (400, 780)),
    ),
)
def test_calculate_centered_position_clamps_to_screen(
    parent: WindowRectangle,
    expected: tuple[int, int],
) -> None:
    """四辺を越える子ウィンドウを画面内へ補正する。"""
    position = calculate_centered_position(
        parent=parent,
        child_width=400,
        child_height=300,
        screen=ScreenSize(1920, 1080),
    )

    assert position == expected


def test_calculate_centered_position_handles_oversized_child() -> None:
    """画面より大きい子画面を左上へ配置する。"""
    position = calculate_centered_position(
        parent=WindowRectangle(100, 100, 800, 600),
        child_width=2000,
        child_height=1200,
        screen=ScreenSize(1920, 1080),
    )

    assert position == (0, 0)


def test_calculate_centered_position_respects_margin() -> None:
    """画面端の余白を考慮して座標を補正する。"""
    position = calculate_centered_position(
        parent=WindowRectangle(-500, -400, 600, 500),
        child_width=400,
        child_height=300,
        screen=ScreenSize(1920, 1080),
        margin=20,
    )

    assert position == (20, 20)


@pytest.mark.parametrize(
    ("parent", "child_width", "child_height", "screen", "margin"),
    (
        (
            WindowRectangle(0, 0, 0, 500),
            400,
            300,
            ScreenSize(1920, 1080),
            0,
        ),
        (
            WindowRectangle(0, 0, 800, 500),
            0,
            300,
            ScreenSize(1920, 1080),
            0,
        ),
        (
            WindowRectangle(0, 0, 800, 500),
            400,
            300,
            ScreenSize(0, 1080),
            0,
        ),
        (
            WindowRectangle(0, 0, 800, 500),
            400,
            300,
            ScreenSize(1920, 1080),
            -1,
        ),
        (
            WindowRectangle(0, 0, 800, 500),
            400,
            300,
            ScreenSize(100, 100),
            50,
        ),
    ),
)
def test_calculate_centered_position_rejects_invalid_dimensions(
    parent: WindowRectangle,
    child_width: int,
    child_height: int,
    screen: ScreenSize,
    margin: int,
) -> None:
    """不正なウィンドウサイズと余白を拒否する。"""
    with pytest.raises(ValueError):
        calculate_centered_position(
            parent=parent,
            child_width=child_width,
            child_height=child_height,
            screen=screen,
            margin=margin,
        )


def test_calculate_centered_position_in_work_area_applies_offset() -> None:
    """上方オフセットを適用して親画面中央へ配置する。"""
    position = calculate_centered_position_in_work_area(
        parent=WindowRectangle(100, 80, 1000, 700),
        child_width=400,
        child_height=300,
        work_area=ScreenWorkArea(0, 0, 1920, 1040, True),
        vertical_offset=-40,
    )

    assert position == (400, 240)


def test_calculate_centered_position_in_negative_work_area() -> None:
    """負の座標を持つ作業領域内へ配置する。"""
    position = calculate_centered_position_in_work_area(
        parent=WindowRectangle(-1700, 100, 1200, 800),
        child_width=600,
        child_height=500,
        work_area=ScreenWorkArea(-1920, 0, 0, 1040),
        vertical_offset=-40,
    )

    assert position == (-1400, 210)


def test_calculate_centered_position_in_work_area_clamps_bottom() -> None:
    """タスクバーを除いた作業領域の下端へ補正する。"""
    position = calculate_centered_position_in_work_area(
        parent=WindowRectangle(100, 800, 1000, 300),
        child_width=400,
        child_height=300,
        work_area=ScreenWorkArea(0, 0, 1920, 1040, True),
    )

    assert position == (400, 740)


def test_calculate_centered_position_in_work_area_handles_oversized_child() -> None:
    """作業領域より大きい子画面を作業領域左上へ配置する。"""
    position = calculate_centered_position_in_work_area(
        parent=WindowRectangle(-1500, 100, 1000, 700),
        child_width=2000,
        child_height=1200,
        work_area=ScreenWorkArea(-1920, 0, 0, 1040),
    )

    assert position == (-1920, 0)


def create_window_mock(
    *,
    width: int,
    height: int,
    requested_width: int | None = None,
    requested_height: int | None = None,
) -> MagicMock:
    """配置テスト用のウィンドウMockを生成する。"""
    window = MagicMock()
    window.winfo_width.return_value = width
    window.winfo_height.return_value = height
    window.winfo_reqwidth.return_value = (
        requested_width
        if requested_width is not None
        else width
    )
    window.winfo_reqheight.return_value = (
        requested_height
        if requested_height is not None
        else height
    )

    return window


def test_center_window_on_parent_sets_geometry() -> None:
    """Tkinter子ウィンドウへ計算した位置を設定する。"""
    child = create_window_mock(width=400, height=300)
    child.winfo_screenwidth.return_value = 1920
    child.winfo_screenheight.return_value = 1080
    parent = create_window_mock(width=1000, height=700)
    parent.winfo_rootx.return_value = 100
    parent.winfo_rooty.return_value = 80

    center_window_on_parent(child, parent)

    child.update_idletasks.assert_called_once_with()
    parent.update_idletasks.assert_called_once_with()
    child.geometry.assert_called_once_with("+400+280")


def test_center_window_on_parent_uses_requested_child_size() -> None:
    """未確定の子サイズには要求サイズを使用する。"""
    child = create_window_mock(
        width=1,
        height=1,
        requested_width=400,
        requested_height=300,
    )
    child.winfo_screenwidth.return_value = 1920
    child.winfo_screenheight.return_value = 1080
    parent = create_window_mock(width=1000, height=700)
    parent.winfo_rootx.return_value = 100
    parent.winfo_rooty.return_value = 80

    center_window_on_parent(child, parent)

    child.geometry.assert_called_once_with("+400+280")


def test_center_window_on_parent_applies_vertical_offset() -> None:
    """指定された上方オフセットを子画面へ適用する。"""
    child = create_window_mock(width=400, height=300)
    child.winfo_screenwidth.return_value = 1920
    child.winfo_screenheight.return_value = 1080
    parent = create_window_mock(width=1000, height=700)
    parent.winfo_rootx.return_value = 100
    parent.winfo_rooty.return_value = 80

    center_window_on_parent(
        child,
        parent,
        vertical_offset=-40,
    )

    child.geometry.assert_called_once_with("+400+240")


def test_center_window_on_parent_falls_back_to_screen_center() -> None:
    """親サイズが未確定の場合は画面中央へ配置する。"""
    child = create_window_mock(width=400, height=300)
    child.winfo_screenwidth.return_value = 1920
    child.winfo_screenheight.return_value = 1080
    parent = create_window_mock(width=1, height=1)

    center_window_on_parent(child, parent)

    child.geometry.assert_called_once_with("+760+390")
    parent.winfo_rootx.assert_not_called()
    parent.winfo_rooty.assert_not_called()


def test_center_window_on_parent_does_not_raise_tcl_error() -> None:
    """Tkinterの位置取得失敗で画面表示を妨げない。"""
    child = create_window_mock(width=400, height=300)
    child.update_idletasks.side_effect = tk.TclError
    parent = create_window_mock(width=1000, height=700)

    center_window_on_parent(child, parent)

    child.geometry.assert_not_called()
