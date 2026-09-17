"""一覧表示状態Modelのテスト。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from book_manager.models.list_view_state import ListViewState


def create_state() -> ListViewState:
    """テスト用の一覧表示状態を生成する。"""
    return ListViewState(
        column_widths={
            "#0": 60,
            "id": 60,
            "title": 250,
        },
        sort_by="title",
        descending=False,
    )


def test_list_view_state_holds_values() -> None:
    """列幅と並び順を保持できる。"""
    state = create_state()

    assert state.schema_version == 1
    assert state.column_widths == {
        "#0": 60,
        "id": 60,
        "title": 250,
    }
    assert state.sort_by == "title"
    assert state.descending is False


def test_list_view_state_default_uses_registered_descending() -> None:
    """既定状態は登録順の降順で列幅を持たない。"""
    state = ListViewState.default()

    assert state == ListViewState(
        column_widths={},
        sort_by="registered",
        descending=True,
    )


def test_list_view_state_accepts_partial_column_widths() -> None:
    """旧形式を想定した部分的な列幅を保持できる。"""
    state = ListViewState(
        column_widths={"title": 300},
        sort_by="registered",
        descending=True,
    )

    assert state.column_widths == {"title": 300}


def test_list_view_state_accepts_unknown_column() -> None:
    """将来削除された可能性がある未知の列IDを保持できる。"""
    state = ListViewState(
        column_widths={"removed_column": 100},
        sort_by="registered",
        descending=True,
    )

    assert state.column_widths == {"removed_column": 100}


@pytest.mark.parametrize(
    "sort_by",
    ListViewState.SUPPORTED_SORT_KEYS,
)
def test_list_view_state_accepts_supported_sort_key(
    sort_by: str,
) -> None:
    """対応しているすべての並び替え項目を保持できる。"""
    state = ListViewState(
        column_widths={},
        sort_by=sort_by,
        descending=True,
    )

    assert state.sort_by == sort_by


def test_list_view_state_copies_input_column_widths() -> None:
    """生成後の入力辞書変更が状態へ影響しない。"""
    widths = {"title": 250}
    state = ListViewState(
        column_widths=widths,
        sort_by="registered",
        descending=True,
    )

    widths["title"] = 500
    widths["author"] = 200

    assert state.column_widths == {"title": 250}


def test_list_view_state_is_frozen() -> None:
    """生成後にフィールドを再代入できない。"""
    state = create_state()

    with pytest.raises(FrozenInstanceError):
        state.sort_by = "author"  # type: ignore[misc]


def test_list_view_state_uses_slots() -> None:
    """動的属性を持たない。"""
    state = create_state()

    assert not hasattr(state, "__dict__")


def test_list_view_state_to_dict_returns_json_compatible_values() -> None:
    """保存用の辞書へ変換できる。"""
    state = create_state()

    assert state.to_dict() == {
        "schema_version": 1,
        "column_widths": {
            "#0": 60,
            "id": 60,
            "title": 250,
        },
        "sort_by": "title",
        "descending": False,
    }


def test_list_view_state_to_dict_returns_column_widths_copy() -> None:
    """保存用辞書の変更が状態へ影響しない。"""
    state = create_state()
    data = state.to_dict()
    column_widths = data["column_widths"]

    assert isinstance(column_widths, dict)
    column_widths["title"] = 500

    assert state.column_widths["title"] == 250


def test_list_view_state_from_dict_restores_state() -> None:
    """JSON由来の辞書から状態を復元できる。"""
    state = ListViewState.from_dict(
        {
            "schema_version": 1,
            "column_widths": {"title": 280, "author": 190},
            "sort_by": "author",
            "descending": True,
        }
    )

    assert state == ListViewState(
        column_widths={"title": 280, "author": 190},
        sort_by="author",
        descending=True,
    )


def test_list_view_state_from_dict_ignores_unknown_top_level_key() -> None:
    """将来追加された未知のトップレベル項目を無視する。"""
    state = ListViewState.from_dict(
        {
            "schema_version": 1,
            "column_widths": {},
            "sort_by": "registered",
            "descending": True,
            "future_setting": "value",
        }
    )

    assert state == ListViewState.default()


def test_list_view_state_round_trip() -> None:
    """辞書への変換と復元を往復できる。"""
    state = create_state()

    assert ListViewState.from_dict(state.to_dict()) == state


@pytest.mark.parametrize(
    "data",
    [None, [], "state", 1, True],
)
def test_list_view_state_from_dict_rejects_non_dict(
    data: object,
) -> None:
    """一覧表示状態全体の辞書以外を拒否する。"""
    with pytest.raises(
        TypeError,
        match="一覧表示状態は辞書",
    ):
        ListViewState.from_dict(data)


@pytest.mark.parametrize(
    "missing_key",
    [
        "schema_version",
        "column_widths",
        "sort_by",
        "descending",
    ],
)
def test_list_view_state_from_dict_rejects_missing_required_key(
    missing_key: str,
) -> None:
    """必須項目がない辞書を拒否する。"""
    data: dict[str, object] = {
        "schema_version": 1,
        "column_widths": {},
        "sort_by": "registered",
        "descending": True,
    }
    del data[missing_key]

    with pytest.raises(ValueError, match=missing_key):
        ListViewState.from_dict(data)


@pytest.mark.parametrize(
    "schema_version",
    [True, 1.0, "1", None],
)
def test_list_view_state_rejects_non_integer_schema_version(
    schema_version: object,
) -> None:
    """真偽値を含む整数以外のschema Versionを拒否する。"""
    with pytest.raises(
        TypeError,
        match="schema_versionは整数",
    ):
        ListViewState(
            column_widths={},
            sort_by="registered",
            descending=True,
            schema_version=schema_version,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("schema_version", [0, 2, -1])
def test_list_view_state_rejects_unsupported_schema_version(
    schema_version: int,
) -> None:
    """未対応のschema Versionを拒否する。"""
    with pytest.raises(ValueError, match="schema_version"):
        ListViewState(
            column_widths={},
            sort_by="registered",
            descending=True,
            schema_version=schema_version,
        )


@pytest.mark.parametrize(
    "column_widths",
    [None, [], "widths", 1, True],
)
def test_list_view_state_rejects_non_dict_column_widths(
    column_widths: object,
) -> None:
    """列幅の辞書以外を拒否する。"""
    with pytest.raises(TypeError, match="column_widthsは辞書"):
        ListViewState(
            column_widths=column_widths,  # type: ignore[arg-type]
            sort_by="registered",
            descending=True,
        )


@pytest.mark.parametrize("column_id", [1, True, None])
def test_list_view_state_rejects_non_string_column_id(
    column_id: object,
) -> None:
    """文字列以外の列IDを拒否する。"""
    with pytest.raises(TypeError, match="列IDは文字列"):
        ListViewState(
            column_widths={column_id: 100},  # type: ignore[dict-item]
            sort_by="registered",
            descending=True,
        )


def test_list_view_state_rejects_empty_column_id() -> None:
    """空の列IDを拒否する。"""
    with pytest.raises(ValueError, match="空文字列"):
        ListViewState(
            column_widths={"": 100},
            sort_by="registered",
            descending=True,
        )


@pytest.mark.parametrize("width", [True, 100.0, "100", None])
def test_list_view_state_rejects_non_integer_column_width(
    width: object,
) -> None:
    """真偽値を含む整数以外の列幅を拒否する。"""
    with pytest.raises(TypeError, match=r"列幅\(title\)は整数"):
        ListViewState(
            column_widths={"title": width},  # type: ignore[dict-item]
            sort_by="registered",
            descending=True,
        )


@pytest.mark.parametrize("width", [0, -1, 4_097])
def test_list_view_state_rejects_out_of_range_column_width(
    width: int,
) -> None:
    """許容範囲外の列幅を拒否する。"""
    with pytest.raises(ValueError, match=r"列幅\(title\)"):
        ListViewState(
            column_widths={"title": width},
            sort_by="registered",
            descending=True,
        )


@pytest.mark.parametrize("width", [1, 4_096])
def test_list_view_state_accepts_boundary_column_width(
    width: int,
) -> None:
    """列幅の下限値と上限値を受け入れる。"""
    state = ListViewState(
        column_widths={"title": width},
        sort_by="registered",
        descending=True,
    )

    assert state.column_widths["title"] == width


@pytest.mark.parametrize("sort_by", [None, 1, True, []])
def test_list_view_state_rejects_non_string_sort_by(
    sort_by: object,
) -> None:
    """文字列以外の並び替え項目を拒否する。"""
    with pytest.raises(TypeError, match="sort_byは文字列"):
        ListViewState(
            column_widths={},
            sort_by=sort_by,  # type: ignore[arg-type]
            descending=True,
        )


@pytest.mark.parametrize("sort_by", ["", "isbn", "unknown"])
def test_list_view_state_rejects_unsupported_sort_by(
    sort_by: str,
) -> None:
    """未対応の並び替え項目を拒否する。"""
    with pytest.raises(ValueError, match="sort_by"):
        ListViewState(
            column_widths={},
            sort_by=sort_by,
            descending=True,
        )


@pytest.mark.parametrize("descending", [None, 0, 1, "true"])
def test_list_view_state_rejects_non_boolean_descending(
    descending: object,
) -> None:
    """真偽値以外の並び方向を拒否する。"""
    with pytest.raises(TypeError, match="descendingは真偽値"):
        ListViewState(
            column_widths={},
            sort_by="registered",
            descending=descending,  # type: ignore[arg-type]
        )
