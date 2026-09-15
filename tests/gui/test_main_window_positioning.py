"""メインウィンドウの安全な復元位置計算のテスト。"""

from __future__ import annotations

import pytest

from book_manager.gui.window_positioning import (
    ScreenWorkArea,
    WindowRectangle,
    calculate_intersection_area,
    calculate_safe_window_rectangle,
    select_work_area,
)


PRIMARY = ScreenWorkArea(
    left=0,
    top=0,
    right=1920,
    bottom=1040,
    primary=True,
)
LEFT = ScreenWorkArea(
    left=-1920,
    top=0,
    right=0,
    bottom=1040,
)
ABOVE = ScreenWorkArea(
    left=0,
    top=-1080,
    right=1920,
    bottom=0,
)


def _safe(
    rectangle: WindowRectangle,
    work_areas: tuple[ScreenWorkArea, ...] = (PRIMARY,),
) -> WindowRectangle:
    return calculate_safe_window_rectangle(
        rectangle,
        work_areas,
        default_width=1350,
        default_height=800,
        minimum_width=1150,
        minimum_height=650,
    )


def test_screen_work_area_calculates_size() -> None:
    """端の座標から作業領域の幅と高さを計算する。"""
    assert LEFT.width == 1920
    assert ABOVE.height == 1080


def test_calculate_intersection_area_returns_overlap() -> None:
    """重なった部分の面積を返す。"""
    rectangle = WindowRectangle(x=-100, y=100, width=200, height=300)

    assert calculate_intersection_area(rectangle, PRIMARY) == 100 * 300


def test_calculate_intersection_area_returns_zero_without_overlap() -> None:
    """矩形が作業領域外なら0を返す。"""
    rectangle = WindowRectangle(x=3000, y=2000, width=500, height=400)

    assert calculate_intersection_area(rectangle, PRIMARY) == 0


def test_select_work_area_uses_largest_intersection() -> None:
    """ウィンドウとの交差面積が最大のモニターを選ぶ。"""
    rectangle = WindowRectangle(x=-1500, y=100, width=1350, height=800)

    assert select_work_area(rectangle, (PRIMARY, LEFT)) == LEFT


def test_select_work_area_prefers_primary_for_equal_intersection() -> None:
    """交差面積が同じ場合は主モニターを選ぶ。"""
    rectangle = WindowRectangle(x=-100, y=100, width=200, height=300)

    assert select_work_area(rectangle, (LEFT, PRIMARY)) == PRIMARY


def test_select_work_area_uses_primary_when_rectangle_is_off_screen() -> None:
    """どの画面とも交差しない場合は主モニターを選ぶ。"""
    rectangle = WindowRectangle(x=5000, y=5000, width=1350, height=800)

    assert select_work_area(rectangle, (LEFT, PRIMARY)) == PRIMARY


def test_safe_rectangle_keeps_visible_position_and_size() -> None:
    """画面内に収まっている矩形を変更しない。"""
    rectangle = WindowRectangle(x=200, y=100, width=1350, height=800)

    assert _safe(rectangle) == rectangle


def test_safe_rectangle_keeps_negative_coordinate_on_left_monitor() -> None:
    """左側モニター上の負のX座標を維持する。"""
    rectangle = WindowRectangle(x=-1700, y=100, width=1350, height=800)

    assert _safe(rectangle, (PRIMARY, LEFT)) == rectangle


def test_safe_rectangle_keeps_negative_coordinate_on_upper_monitor() -> None:
    """上側モニター上の負のY座標を維持する。"""
    rectangle = WindowRectangle(x=200, y=-1000, width=1350, height=800)

    assert _safe(rectangle, (PRIMARY, ABOVE)) == rectangle


def test_safe_rectangle_moves_right_edge_inside_work_area() -> None:
    """右端のはみ出しを作業領域内へ移動する。"""
    rectangle = WindowRectangle(x=1000, y=100, width=1350, height=800)

    assert _safe(rectangle).x == 570


def test_safe_rectangle_moves_bottom_edge_inside_work_area() -> None:
    """下端のはみ出しを作業領域内へ移動する。"""
    rectangle = WindowRectangle(x=200, y=500, width=1350, height=800)

    assert _safe(rectangle).y == 240


def test_safe_rectangle_shrinks_window_to_work_area() -> None:
    """作業領域より大きいウィンドウを縮小する。"""
    rectangle = WindowRectangle(x=0, y=0, width=3000, height=2000)

    assert _safe(rectangle) == WindowRectangle(
        x=0,
        y=0,
        width=1920,
        height=1040,
    )


def test_safe_rectangle_centers_default_size_when_fully_off_screen() -> None:
    """完全に画面外なら既定サイズで主モニター中央へ戻す。"""
    rectangle = WindowRectangle(x=4000, y=3000, width=1600, height=900)

    assert _safe(rectangle, (LEFT, PRIMARY)) == WindowRectangle(
        x=285,
        y=120,
        width=1350,
        height=800,
    )


def test_safe_rectangle_fits_work_area_smaller_than_minimum_size() -> None:
    """最小サイズより小さい作業領域にも全体を収める。"""
    small = ScreenWorkArea(
        left=0,
        top=0,
        right=1024,
        bottom=600,
        primary=True,
    )
    rectangle = WindowRectangle(x=3000, y=3000, width=1350, height=800)

    assert _safe(rectangle, (small,)) == WindowRectangle(
        x=0,
        y=0,
        width=1024,
        height=600,
    )


def test_safe_rectangle_expands_size_to_effective_minimum() -> None:
    """保存サイズが最小値未満なら最小サイズへ拡大する。"""
    rectangle = WindowRectangle(x=100, y=100, width=800, height=500)

    assert _safe(rectangle) == WindowRectangle(
        x=100,
        y=100,
        width=1150,
        height=650,
    )


def test_select_work_area_rejects_empty_areas() -> None:
    """作業領域が空の場合は拒否する。"""
    rectangle = WindowRectangle(x=0, y=0, width=1350, height=800)

    with pytest.raises(ValueError, match="作業領域"):
        select_work_area(rectangle, ())


def test_select_work_area_rejects_invalid_area() -> None:
    """幅または高さが正でない作業領域を拒否する。"""
    rectangle = WindowRectangle(x=0, y=0, width=1350, height=800)
    invalid = ScreenWorkArea(left=0, top=0, right=0, bottom=100)

    with pytest.raises(ValueError, match="不正"):
        select_work_area(rectangle, (invalid,))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("rectangle_width", 0),
        ("rectangle_height", 0),
        ("default_width", 0),
        ("default_height", 0),
        ("minimum_width", 0),
        ("minimum_height", 0),
    ],
)
def test_safe_rectangle_rejects_non_positive_dimensions(
    field_name: str,
    value: int,
) -> None:
    """補正に使用する幅と高さは正の値に限定する。"""
    arguments = {
        "saved_rectangle": WindowRectangle(0, 0, 1350, 800),
        "work_areas": (PRIMARY,),
        "default_width": 1350,
        "default_height": 800,
        "minimum_width": 1150,
        "minimum_height": 650,
    }
    if field_name == "rectangle_width":
        arguments["saved_rectangle"] = WindowRectangle(0, 0, value, 800)
    elif field_name == "rectangle_height":
        arguments["saved_rectangle"] = WindowRectangle(0, 0, 1350, value)
    else:
        arguments[field_name] = value

    with pytest.raises(ValueError, match="1以上"):
        calculate_safe_window_rectangle(**arguments)
