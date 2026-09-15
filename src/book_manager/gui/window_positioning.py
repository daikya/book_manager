"""Tkinterサブウィンドウの表示位置を管理する。"""

from __future__ import annotations

import ctypes
import os
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WindowRectangle:
    """画面上のウィンドウ位置と大きさ。"""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ScreenSize:
    """画面の幅と高さ。"""

    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ScreenWorkArea:
    """タスクバーなどを除いたモニターの作業領域。"""

    left: int
    top: int
    right: int
    bottom: int
    primary: bool = False

    @property
    def width(self) -> int:
        """作業領域の幅を返す。"""
        return self.right - self.left

    @property
    def height(self) -> int:
        """作業領域の高さを返す。"""
        return self.bottom - self.top


def get_screen_work_areas(root: tk.Misc) -> tuple[ScreenWorkArea, ...]:
    """利用可能なモニターの作業領域を返す。

    Windows APIを利用できない場合は、Tkinterが返す画面サイズを
    単一の主モニター作業領域として使用する。
    """
    if os.name == "nt":
        try:
            work_areas = _get_windows_screen_work_areas()
            if work_areas:
                return work_areas
        except (
            AttributeError,
            OSError,
            TypeError,
            ValueError,
            ctypes.ArgumentError,
        ):
            pass

    return (
        ScreenWorkArea(
            left=0,
            top=0,
            right=root.winfo_screenwidth(),
            bottom=root.winfo_screenheight(),
            primary=True,
        ),
    )


def calculate_intersection_area(
    rectangle: WindowRectangle,
    work_area: ScreenWorkArea,
) -> int:
    """ウィンドウ矩形と作業領域が重なる面積を返す。"""
    intersection_width = max(
        0,
        min(rectangle.x + rectangle.width, work_area.right)
        - max(rectangle.x, work_area.left),
    )
    intersection_height = max(
        0,
        min(rectangle.y + rectangle.height, work_area.bottom)
        - max(rectangle.y, work_area.top),
    )
    return intersection_width * intersection_height


def select_work_area(
    rectangle: WindowRectangle,
    work_areas: tuple[ScreenWorkArea, ...],
) -> ScreenWorkArea:
    """交差面積が最大の作業領域を選択する。

    交差面積が同じ場合と、すべて交差しない場合は主モニターを
    優先する。
    """
    _validate_work_areas(work_areas)
    return max(
        work_areas,
        key=lambda area: (
            calculate_intersection_area(rectangle, area),
            area.primary,
        ),
    )


def calculate_safe_window_rectangle(
    saved_rectangle: WindowRectangle,
    work_areas: tuple[ScreenWorkArea, ...],
    *,
    default_width: int,
    default_height: int,
    minimum_width: int,
    minimum_height: int,
) -> WindowRectangle:
    """保存矩形を現在のモニターで操作可能な範囲へ補正する。"""
    _validate_main_window_dimensions(
        saved_rectangle,
        default_width,
        default_height,
        minimum_width,
        minimum_height,
    )
    selected_area = select_work_area(saved_rectangle, work_areas)
    intersects_screen = (
        calculate_intersection_area(saved_rectangle, selected_area) > 0
    )

    source_width = (
        saved_rectangle.width if intersects_screen else default_width
    )
    source_height = (
        saved_rectangle.height if intersects_screen else default_height
    )
    effective_minimum_width = min(minimum_width, selected_area.width)
    effective_minimum_height = min(minimum_height, selected_area.height)
    width = min(
        selected_area.width,
        max(effective_minimum_width, source_width),
    )
    height = min(
        selected_area.height,
        max(effective_minimum_height, source_height),
    )

    if intersects_screen:
        x = min(
            max(saved_rectangle.x, selected_area.left),
            selected_area.right - width,
        )
        y = min(
            max(saved_rectangle.y, selected_area.top),
            selected_area.bottom - height,
        )
    else:
        x = selected_area.left + (selected_area.width - width) // 2
        y = selected_area.top + (selected_area.height - height) // 2

    return WindowRectangle(x=x, y=y, width=width, height=height)


def calculate_centered_position(
    parent: WindowRectangle,
    child_width: int,
    child_height: int,
    screen: ScreenSize,
    margin: int = 0,
) -> tuple[int, int]:
    """親の中央を基準とした画面内の子座標を返す。"""
    _validate_dimensions(
        parent,
        child_width,
        child_height,
        screen,
        margin,
    )

    centered_x = (
        parent.x
        + (parent.width - child_width) // 2
    )
    centered_y = (
        parent.y
        + (parent.height - child_height) // 2
    )

    maximum_x = max(
        margin,
        screen.width - child_width - margin,
    )
    maximum_y = max(
        margin,
        screen.height - child_height - margin,
    )

    x = min(maximum_x, max(margin, centered_x))
    y = min(maximum_y, max(margin, centered_y))

    return x, y


def center_window_on_parent(
    child: tk.Toplevel,
    parent: tk.Misc,
    *,
    margin: int = 0,
) -> None:
    """子ウィンドウを親の中央かつ画面内へ配置する。"""
    try:
        child.update_idletasks()
        child_width = _get_window_width(child)
        child_height = _get_window_height(child)
        screen = ScreenSize(
            width=child.winfo_screenwidth(),
            height=child.winfo_screenheight(),
        )
        parent_rectangle = _get_parent_rectangle(
            parent,
            screen,
        )
        x, y = calculate_centered_position(
            parent=parent_rectangle,
            child_width=child_width,
            child_height=child_height,
            screen=screen,
            margin=margin,
        )
        child.geometry(f"+{x}+{y}")
    except (tk.TclError, ValueError):
        # 配置処理に失敗しても、ウィンドウ自体は
        # Tkの既定位置で表示できるようにする。
        return


def _get_window_width(window: tk.Misc) -> int:
    """確定済みまたは要求中のウィンドウ幅を返す。"""
    width = window.winfo_width()

    if width <= 1:
        return window.winfo_reqwidth()

    return width


def _get_window_height(window: tk.Misc) -> int:
    """確定済みまたは要求中のウィンドウ高さを返す。"""
    height = window.winfo_height()

    if height <= 1:
        return window.winfo_reqheight()

    return height


def _get_parent_rectangle(
    parent: tk.Misc,
    screen: ScreenSize,
) -> WindowRectangle:
    """親ウィンドウまたは画面全体の矩形を返す。"""
    parent.update_idletasks()
    width = parent.winfo_width()
    height = parent.winfo_height()

    if width <= 1 or height <= 1:
        return WindowRectangle(
            x=0,
            y=0,
            width=screen.width,
            height=screen.height,
        )

    return WindowRectangle(
        x=parent.winfo_rootx(),
        y=parent.winfo_rooty(),
        width=width,
        height=height,
    )


def _validate_dimensions(
    parent: WindowRectangle,
    child_width: int,
    child_height: int,
    screen: ScreenSize,
    margin: int,
) -> None:
    """座標計算に使用する大きさを検証する。"""
    if parent.width <= 0 or parent.height <= 0:
        raise ValueError(
            "親ウィンドウの幅と高さは"
            "1以上である必要があります。"
        )

    if child_width <= 0 or child_height <= 0:
        raise ValueError(
            "子ウィンドウの幅と高さは"
            "1以上である必要があります。"
        )

    if screen.width <= 0 or screen.height <= 0:
        raise ValueError(
            "画面の幅と高さは1以上である必要があります。"
        )

    if margin < 0:
        raise ValueError(
            "画面端の余白は0以上である必要があります。"
        )

    if margin * 2 >= screen.width or margin * 2 >= screen.height:
        raise ValueError(
            "画面端の余白が画面サイズに対して"
            "大きすぎます。"
        )


def _validate_work_areas(
    work_areas: tuple[ScreenWorkArea, ...],
) -> None:
    """作業領域が1件以上あり、正の大きさを持つことを検証する。"""
    if not work_areas:
        raise ValueError("モニターの作業領域が必要です。")
    if any(area.width <= 0 or area.height <= 0 for area in work_areas):
        raise ValueError("モニターの作業領域が不正です。")


def _validate_main_window_dimensions(
    rectangle: WindowRectangle,
    default_width: int,
    default_height: int,
    minimum_width: int,
    minimum_height: int,
) -> None:
    """メインウィンドウの補正に使用するサイズを検証する。"""
    dimensions = (
        rectangle.width,
        rectangle.height,
        default_width,
        default_height,
        minimum_width,
        minimum_height,
    )
    if any(value <= 0 for value in dimensions):
        raise ValueError("ウィンドウの幅と高さは1以上である必要があります。")


def _get_windows_screen_work_areas() -> tuple[ScreenWorkArea, ...]:
    """Windows APIで全モニターの作業領域を取得する。"""
    class Rectangle(ctypes.Structure):
        _fields_ = (
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        )

    class MonitorInfo(ctypes.Structure):
        _fields_ = (
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", Rectangle),
            ("rcWork", Rectangle),
            ("dwFlags", wintypes.DWORD),
        )

    monitor_callback = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(Rectangle),
        wintypes.LPARAM,
    )
    user32 = ctypes.windll.user32
    work_areas: list[ScreenWorkArea] = []

    @monitor_callback
    def collect_monitor(
        monitor: Any,
        device_context: Any,
        monitor_rectangle: Any,
        data: Any,
    ) -> bool:
        del device_context, monitor_rectangle, data
        information = MonitorInfo()
        information.cbSize = ctypes.sizeof(MonitorInfo)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(information)):
            return True
        work = information.rcWork
        work_areas.append(
            ScreenWorkArea(
                left=work.left,
                top=work.top,
                right=work.right,
                bottom=work.bottom,
                primary=bool(information.dwFlags & 1),
            )
        )
        return True

    if not user32.EnumDisplayMonitors(None, None, collect_monitor, 0):
        raise OSError("モニター情報を取得できません。")

    return tuple(work_areas)
