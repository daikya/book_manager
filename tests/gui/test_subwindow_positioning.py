"""既存サブウィンドウへの中央配置適用を検証する。"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)


def test_wait_for_dialog_centers_before_waiting() -> None:
    """親画面中央へ配置してから待機する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = MagicMock()
    dialog = MagicMock()
    events: list[str] = []

    with patch(
        "book_manager.gui.book_manager_application."
        "center_window_on_parent",
        side_effect=lambda *_: events.append("center"),
    ) as center_window:
        dialog.wait_window.side_effect = (
            lambda: events.append("wait")
        )

        application._wait_for_dialog(dialog)

    center_window.assert_called_once_with(
        dialog,
        application._root,
    )
    dialog.wait_window.assert_called_once_with()
    assert events == ["center", "wait"]


@pytest.mark.parametrize(
    "method_name",
    (
        "_on_select_tags",
        "_on_manage_tags",
        "_open_reading_history_dialog",
        "_open_reading_statistics_dialog",
    ),
)
def test_existing_dialog_uses_common_waiting_process(
    method_name: str,
) -> None:
    """既存サブウィンドウが共通の待機処理を使用する。"""
    method = getattr(BookManagerApplication, method_name)
    source = inspect.getsource(method)

    assert "self._wait_for_dialog(dialog)" in source
    assert "dialog.wait_window()" not in source
