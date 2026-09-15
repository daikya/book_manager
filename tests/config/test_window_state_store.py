"""ウィンドウ状態のJSON保存処理のテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_manager.config.window_state_store import (
    WindowStateStore,
    WindowStateStoreError,
)
from book_manager.models.window_state import WindowState


def _create_state() -> WindowState:
    return WindowState(
        x=-1920,
        y=80,
        width=1350,
        height=800,
        maximized=True,
    )


def test_path_returns_configured_path(tmp_path: Path) -> None:
    """設定した保存先を公開する。"""
    path = tmp_path / "window_state.json"

    assert WindowStateStore(path).path == path


def test_load_returns_none_when_file_does_not_exist(tmp_path: Path) -> None:
    """状態ファイルが存在しない場合はNoneを返す。"""
    store = WindowStateStore(tmp_path / "window_state.json")

    assert store.load() is None


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    """保存した状態を同じ値で読み込める。"""
    store = WindowStateStore(tmp_path / "window_state.json")
    expected = _create_state()

    store.save(expected)

    assert store.load() == expected


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    """存在しない保存先ディレクトリを作成する。"""
    path = tmp_path / "settings" / "window_state.json"

    WindowStateStore(path).save(_create_state())

    assert path.is_file()


def test_save_writes_readable_utf8_json_with_trailing_newline(
    tmp_path: Path,
) -> None:
    """UTF-8で整形されたJSONと末尾改行を書き込む。"""
    path = tmp_path / "window_state.json"

    WindowStateStore(path).save(_create_state())

    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert json.loads(content) == {
        "schema_version": 1,
        "x": -1920,
        "y": 80,
        "width": 1350,
        "height": 800,
        "maximized": True,
    }


def test_save_replaces_existing_file(tmp_path: Path) -> None:
    """既存ファイルを新しい状態で置換する。"""
    path = tmp_path / "window_state.json"
    path.write_text("old content", encoding="utf-8")

    WindowStateStore(path).save(_create_state())

    assert json.loads(path.read_text(encoding="utf-8"))["x"] == -1920


def test_save_leaves_no_temporary_file(tmp_path: Path) -> None:
    """保存成功後に一時ファイルを残さない。"""
    path = tmp_path / "window_state.json"

    WindowStateStore(path).save(_create_state())

    assert list(tmp_path.glob(f".{path.name}.*.tmp")) == []


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        "[]",
        json.dumps({"schema_version": 1}),
        json.dumps(
            {
                "schema_version": 1,
                "x": 0,
                "y": 0,
                "width": 1350,
                "height": 800,
                "maximized": False,
                "unexpected": True,
            }
        ),
        json.dumps(
            {
                "schema_version": 2,
                "x": 0,
                "y": 0,
                "width": 1350,
                "height": 800,
                "maximized": False,
            }
        ),
        json.dumps(
            {
                "schema_version": 1,
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 800,
                "maximized": False,
            }
        ),
    ],
)
def test_load_returns_none_and_logs_warning_for_invalid_content(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    content: str,
) -> None:
    """壊れた形式や不正値を安全に無視して警告を記録する。"""
    path = tmp_path / "window_state.json"
    path.write_text(content, encoding="utf-8")

    result = WindowStateStore(path).load()

    assert result is None
    assert "初期状態を使用します" in caplog.text


def test_load_returns_none_for_invalid_utf8(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """UTF-8として読み込めない内容を安全に無視する。"""
    path = tmp_path / "window_state.json"
    path.write_bytes(b"\x80\x81")

    assert WindowStateStore(path).load() is None
    assert "初期状態を使用します" in caplog.text


def test_save_rejects_non_window_state(tmp_path: Path) -> None:
    """WindowState以外の値を保存対象として受け入れない。"""
    store = WindowStateStore(tmp_path / "window_state.json")

    with pytest.raises(TypeError, match="WindowState"):
        store.save(object())


def test_save_wraps_file_system_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """保存時のファイルシステムエラーを専用例外へ変換する。"""
    store = WindowStateStore(tmp_path / "window_state.json")

    def raise_error(*args: object, **kwargs: object) -> None:
        raise OSError("write failed")

    monkeypatch.setattr("tempfile.NamedTemporaryFile", raise_error)

    with pytest.raises(WindowStateStoreError, match="保存できません"):
        store.save(_create_state())


def test_delete_removes_existing_file(tmp_path: Path) -> None:
    """存在する状態ファイルを削除する。"""
    path = tmp_path / "window_state.json"
    path.write_text("{}", encoding="utf-8")

    WindowStateStore(path).delete()

    assert not path.exists()


def test_delete_accepts_missing_file(tmp_path: Path) -> None:
    """状態ファイルが存在しない場合も正常終了する。"""
    WindowStateStore(tmp_path / "window_state.json").delete()


def test_delete_wraps_file_system_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """削除時のファイルシステムエラーを専用例外へ変換する。"""
    path = tmp_path / "window_state.json"
    store = WindowStateStore(path)

    def raise_error(*args: object, **kwargs: object) -> None:
        raise OSError("delete failed")

    monkeypatch.setattr(Path, "unlink", raise_error)

    with pytest.raises(WindowStateStoreError, match="削除できません"):
        store.delete()
