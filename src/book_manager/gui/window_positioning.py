"""Tkinterサブウィンドウの表示位置を管理する。"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass


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
