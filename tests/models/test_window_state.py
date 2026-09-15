"""メインウィンドウ状態Modelのテスト。"""

from __future__ import annotations

import pytest

from book_manager.models.window_state import WindowState


def test_window_state_keeps_normal_window_values() -> None:
    """通常表示時の矩形と最大化状態を保持する。"""
    state = WindowState(
        x=120,
        y=80,
        width=1350,
        height=800,
        maximized=False,
    )

    assert state.x == 120
    assert state.y == 80
    assert state.width == 1350
    assert state.height == 800
    assert state.maximized is False
    assert state.schema_version == 1


def test_window_state_accepts_negative_coordinates() -> None:
    """主モニターの左側・上側にあるモニターの座標を受け入れる。"""
    state = WindowState(
        x=-1920,
        y=-1080,
        width=1350,
        height=800,
        maximized=True,
    )

    assert state.x == -1920
    assert state.y == -1080
    assert state.maximized is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("x", WindowState.MINIMUM_COORDINATE),
        ("x", WindowState.MAXIMUM_COORDINATE),
        ("y", WindowState.MINIMUM_COORDINATE),
        ("y", WindowState.MAXIMUM_COORDINATE),
        ("width", WindowState.MINIMUM_SIZE),
        ("width", WindowState.MAXIMUM_SIZE),
        ("height", WindowState.MINIMUM_SIZE),
        ("height", WindowState.MAXIMUM_SIZE),
    ],
)
def test_window_state_accepts_boundary_values(
    field_name: str,
    value: int,
) -> None:
    """座標とサイズの境界値を受け入れる。"""
    values = {
        "x": 0,
        "y": 0,
        "width": 1350,
        "height": 800,
        "maximized": False,
    }
    values[field_name] = value

    state = WindowState(**values)

    assert getattr(state, field_name) == value


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("x", WindowState.MINIMUM_COORDINATE - 1),
        ("x", WindowState.MAXIMUM_COORDINATE + 1),
        ("y", WindowState.MINIMUM_COORDINATE - 1),
        ("y", WindowState.MAXIMUM_COORDINATE + 1),
        ("width", WindowState.MINIMUM_SIZE - 1),
        ("width", WindowState.MAXIMUM_SIZE + 1),
        ("height", WindowState.MINIMUM_SIZE - 1),
        ("height", WindowState.MAXIMUM_SIZE + 1),
    ],
)
def test_window_state_rejects_values_outside_range(
    field_name: str,
    value: int,
) -> None:
    """許容範囲外の座標とサイズを拒否する。"""
    values = {
        "x": 0,
        "y": 0,
        "width": 1350,
        "height": 800,
        "maximized": False,
    }
    values[field_name] = value

    with pytest.raises(ValueError, match=field_name):
        WindowState(**values)


@pytest.mark.parametrize(
    "field_name",
    ["x", "y", "width", "height", "schema_version"],
)
@pytest.mark.parametrize("value", [True, False])
def test_window_state_rejects_boolean_for_integer_field(
    field_name: str,
    value: bool,
) -> None:
    """Pythonで整数として扱われる真偽値を整数項目では拒否する。"""
    values = {
        "x": 0,
        "y": 0,
        "width": 1350,
        "height": 800,
        "maximized": False,
        "schema_version": 1,
    }
    values[field_name] = value

    with pytest.raises(TypeError, match=field_name):
        WindowState(**values)


@pytest.mark.parametrize("value", [0, 1, "true", None])
def test_window_state_rejects_non_boolean_maximized(
    value: object,
) -> None:
    """maximizedには真偽値だけを受け入れる。"""
    with pytest.raises(TypeError, match="maximized"):
        WindowState(
            x=0,
            y=0,
            width=1350,
            height=800,
            maximized=value,
        )


@pytest.mark.parametrize("value", [0, 2, -1])
def test_window_state_rejects_unsupported_schema_version(
    value: int,
) -> None:
    """現在対応していない保存形式Versionを拒否する。"""
    with pytest.raises(ValueError, match="schema_version"):
        WindowState(
            x=0,
            y=0,
            width=1350,
            height=800,
            maximized=False,
            schema_version=value,
        )


def test_window_state_is_immutable() -> None:
    """生成後の状態を変更できない。"""
    state = WindowState(
        x=0,
        y=0,
        width=1350,
        height=800,
        maximized=False,
    )

    with pytest.raises(AttributeError):
        state.width = 1600
