"""一覧表示状態Storeのテスト。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from book_manager.config.list_view_state_store import (
    ListViewStateStore,
    ListViewStateStoreError,
)
from book_manager.models.list_view_state import ListViewState


def create_state() -> ListViewState:
    """テスト用の一覧表示状態を生成する。"""
    return ListViewState(
        column_widths={
            "#0": 60,
            "id": 60,
            "title": 280,
            "author": 190,
        },
        sort_by="author",
        descending=False,
    )


def write_json(path: Path, data: object) -> None:
    """テスト用JSONを書き込む。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )


def test_list_view_state_store_holds_path(tmp_path: Path) -> None:
    """状態ファイルの保存先を保持する。"""
    path = tmp_path / "settings" / "list_view_state.json"

    store = ListViewStateStore(path)

    assert store.path == path


def test_list_view_state_store_accepts_path_like_string(
    tmp_path: Path,
) -> None:
    """文字列の保存先をPathへ変換する。"""
    path = tmp_path / "list_view_state.json"

    store = ListViewStateStore(str(path))  # type: ignore[arg-type]

    assert store.path == path


def test_load_returns_none_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    """保存ファイルがなければNoneを返す。"""
    store = ListViewStateStore(tmp_path / "list_view_state.json")

    assert store.load() is None


def test_load_restores_list_view_state(tmp_path: Path) -> None:
    """保存済みJSONから一覧表示状態を復元する。"""
    path = tmp_path / "list_view_state.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "column_widths": {
                "#0": 60,
                "title": 280,
                "author": 190,
            },
            "sort_by": "author",
            "descending": False,
        },
    )

    state = ListViewStateStore(path).load()

    assert state == ListViewState(
        column_widths={
            "#0": 60,
            "title": 280,
            "author": 190,
        },
        sort_by="author",
        descending=False,
    )


def test_load_accepts_partial_and_unknown_columns(
    tmp_path: Path,
) -> None:
    """部分的な列幅と未知の列IDを読み込める。"""
    path = tmp_path / "list_view_state.json"
    write_json(
        path,
        {
            "schema_version": 1,
            "column_widths": {
                "title": 300,
                "removed_column": 120,
            },
            "sort_by": "registered",
            "descending": True,
        },
    )

    state = ListViewStateStore(path).load()

    assert state is not None
    assert state.column_widths == {
        "title": 300,
        "removed_column": 120,
    }


def test_load_ignores_unknown_top_level_key(tmp_path: Path) -> None:
    """将来追加された未知のトップレベル項目を無視する。"""
    path = tmp_path / "list_view_state.json"
    data = create_state().to_dict()
    data["future_setting"] = "value"
    write_json(path, data)

    assert ListViewStateStore(path).load() == create_state()


@pytest.mark.parametrize(
    "data",
    [
        [],
        {
            "column_widths": {},
            "sort_by": "registered",
            "descending": True,
        },
        {
            "schema_version": 2,
            "column_widths": {},
            "sort_by": "registered",
            "descending": True,
        },
        {
            "schema_version": 1,
            "column_widths": {"title": 0},
            "sort_by": "registered",
            "descending": True,
        },
        {
            "schema_version": 1,
            "column_widths": {},
            "sort_by": "isbn",
            "descending": True,
        },
        {
            "schema_version": 1,
            "column_widths": {},
            "sort_by": "registered",
            "descending": 1,
        },
    ],
    ids=[
        "non-object",
        "missing-key",
        "unsupported-schema",
        "invalid-width",
        "invalid-sort-key",
        "invalid-direction",
    ],
)
def test_load_returns_none_for_unusable_data(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    data: object,
) -> None:
    """利用できない内容を無視して警告を記録する。"""
    path = tmp_path / "list_view_state.json"
    write_json(path, data)

    with caplog.at_level(logging.WARNING):
        state = ListViewStateStore(path).load()

    assert state is None
    assert "初期状態を使用します" in caplog.text
    assert str(path) in caplog.text


def test_load_returns_none_for_invalid_json(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """壊れたJSONを無視して警告を記録する。"""
    path = tmp_path / "list_view_state.json"
    path.write_text("{invalid", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        state = ListViewStateStore(path).load()

    assert state is None
    assert "初期状態を使用します" in caplog.text


def test_load_returns_none_for_invalid_utf8(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """UTF-8でないファイルを無視して警告を記録する。"""
    path = tmp_path / "list_view_state.json"
    path.write_bytes(b"\xff\xfe")

    with caplog.at_level(logging.WARNING):
        state = ListViewStateStore(path).load()

    assert state is None
    assert "初期状態を使用します" in caplog.text


def test_load_returns_none_for_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """読み込み時のOSエラーを無視して警告を記録する。"""
    path = tmp_path / "list_view_state.json"
    path.write_text("{}", encoding="utf-8")
    original_open = Path.open

    def raise_for_target(
        self: Path,
        *args: object,
        **kwargs: object,
    ) -> object:
        if self == path:
            raise PermissionError("read denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raise_for_target)

    with caplog.at_level(logging.WARNING):
        state = ListViewStateStore(path).load()

    assert state is None
    assert "初期状態を使用します" in caplog.text


def test_save_creates_parent_and_writes_expected_json(
    tmp_path: Path,
) -> None:
    """親ディレクトリを作成して期待するJSONを保存する。"""
    path = tmp_path / "settings" / "list_view_state.json"

    ListViewStateStore(path).save(create_state())

    assert json.loads(path.read_text(encoding="utf-8")) == (
        create_state().to_dict()
    )


def test_save_uses_utf8_indent_and_trailing_newline(
    tmp_path: Path,
) -> None:
    """UTF-8、インデント2、末尾改行で保存する。"""
    path = tmp_path / "list_view_state.json"

    ListViewStateStore(path).save(create_state())

    content = path.read_text(encoding="utf-8")
    assert content.startswith('{\n  "schema_version": 1,')
    assert '\n  "column_widths": {\n    "#0": 60,' in content
    assert content.endswith("\n")
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_save_replaces_existing_file(tmp_path: Path) -> None:
    """既存ファイルを新しい状態で置き換える。"""
    path = tmp_path / "list_view_state.json"
    path.write_text("old content", encoding="utf-8")

    ListViewStateStore(path).save(create_state())

    assert ListViewStateStore(path).load() == create_state()


def test_save_uses_temporary_file_and_os_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同じディレクトリの一時ファイルから原子的に置換する。"""
    path = tmp_path / "list_view_state.json"
    actual_replace = os.replace
    replacements: list[tuple[Path, Path]] = []

    def record_replace(source: object, destination: object) -> None:
        source_path = Path(source)  # type: ignore[arg-type]
        destination_path = Path(destination)  # type: ignore[arg-type]
        replacements.append((source_path, destination_path))
        assert source_path.parent == path.parent
        assert source_path.name.startswith(f".{path.name}.")
        assert source_path.suffix == ".tmp"
        actual_replace(source_path, destination_path)

    monkeypatch.setattr(os, "replace", record_replace)

    ListViewStateStore(path).save(create_state())

    assert len(replacements) == 1
    assert replacements[0][1] == path
    assert path.exists()


def test_save_rejects_non_list_view_state(tmp_path: Path) -> None:
    """ListViewState以外の保存を拒否する。"""
    store = ListViewStateStore(tmp_path / "list_view_state.json")

    with pytest.raises(
        TypeError,
        match="stateにはListViewState",
    ):
        store.save({})  # type: ignore[arg-type]


def test_save_wraps_os_error_and_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置換失敗を専用例外へ変換し、一時ファイルを削除する。"""
    path = tmp_path / "list_view_state.json"
    path.write_text("old content", encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        del source, destination
        raise PermissionError("replace denied")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(
        ListViewStateStoreError,
        match="保存できません",
    ):
        ListViewStateStore(path).save(create_state())

    assert path.read_text(encoding="utf-8") == "old content"
    assert list(tmp_path.glob(f".{path.name}.*.tmp")) == []


def test_save_logs_temporary_file_cleanup_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """一時ファイル削除失敗を記録する。"""
    path = tmp_path / "list_view_state.json"

    def fail_replace(source: object, destination: object) -> None:
        del source, destination
        raise PermissionError("replace denied")

    def fail_unlink(
        self: Path,
        missing_ok: bool = False,
    ) -> None:
        del self, missing_ok
        raise PermissionError("cleanup denied")

    monkeypatch.setattr(os, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_unlink)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(
            ListViewStateStoreError,
            match="保存できません",
        ):
            ListViewStateStore(path).save(create_state())

    assert "一時ファイルを削除できません" in caplog.text


def test_delete_removes_existing_file(tmp_path: Path) -> None:
    """保存済みファイルを削除する。"""
    path = tmp_path / "list_view_state.json"
    ListViewStateStore(path).save(create_state())

    ListViewStateStore(path).delete()

    assert not path.exists()


def test_delete_succeeds_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    """保存ファイルがなくても削除を成功扱いにする。"""
    path = tmp_path / "list_view_state.json"

    ListViewStateStore(path).delete()

    assert not path.exists()


def test_delete_wraps_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """削除失敗を専用例外へ変換する。"""
    path = tmp_path / "list_view_state.json"
    path.write_text("content", encoding="utf-8")
    original_unlink = Path.unlink

    def fail_for_target(
        self: Path,
        missing_ok: bool = False,
    ) -> None:
        if self == path:
            raise PermissionError("delete denied")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_for_target)

    with pytest.raises(
        ListViewStateStoreError,
        match="削除できません",
    ):
        ListViewStateStore(path).delete()

    assert path.exists()
