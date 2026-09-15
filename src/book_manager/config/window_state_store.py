"""メインウィンドウ状態のJSON保存処理。"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from book_manager.models.window_state import WindowState


logger = logging.getLogger(__name__)


class WindowStateStoreError(RuntimeError):
    """ウィンドウ状態の保存または削除に失敗した場合の例外。"""


class WindowStateStore:
    """ウィンドウ状態をJSONファイルで管理する。"""

    def __init__(self, path: Path) -> None:
        """状態ファイルの保存先を受け取る。"""
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """状態ファイルの保存先を返す。"""
        return self._path

    def load(self) -> WindowState | None:
        """保存状態を読み込む。

        ファイルが存在しない場合や内容を利用できない場合は、
        起動を妨げないようにNoneを返す。
        """
        try:
            with self._path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            return self._deserialize(data)
        except FileNotFoundError:
            return None
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            logger.warning(
                "ウィンドウ状態を読み込めないため、初期状態を使用します: %s",
                self._path,
                exc_info=error,
            )
            return None

    def save(self, state: WindowState) -> None:
        """状態を一時ファイルへ書き込み、保存先へ原子的に置換する。"""
        if not isinstance(state, WindowState):
            raise TypeError("stateにはWindowStateを指定してください。")

        temporary_path: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(
                    self._serialize(state),
                    stream,
                    ensure_ascii=False,
                    indent=2,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary_path, self._path)
            temporary_path = None
        except OSError as error:
            raise WindowStateStoreError(
                "ウィンドウ状態を保存できません。"
            ) from error
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning(
                        "ウィンドウ状態の一時ファイルを削除できません: %s",
                        temporary_path,
                        exc_info=True,
                    )

    def delete(self) -> None:
        """保存状態を削除する。存在しない場合は何もしない。"""
        try:
            self._path.unlink(missing_ok=True)
        except OSError as error:
            raise WindowStateStoreError(
                "ウィンドウ状態を削除できません。"
            ) from error

    @staticmethod
    def _serialize(state: WindowState) -> dict[str, int | bool]:
        """WindowStateを保存用の辞書へ変換する。"""
        return {
            "schema_version": state.schema_version,
            "x": state.x,
            "y": state.y,
            "width": state.width,
            "height": state.height,
            "maximized": state.maximized,
        }

    @staticmethod
    def _deserialize(data: Any) -> WindowState:
        """JSONから読み込んだ値をWindowStateへ変換する。"""
        if not isinstance(data, dict):
            raise TypeError("ウィンドウ状態のJSONはオブジェクトである必要があります。")

        required_keys = {
            "schema_version",
            "x",
            "y",
            "width",
            "height",
            "maximized",
        }
        if set(data) != required_keys:
            raise ValueError("ウィンドウ状態の項目が正しくありません。")

        return WindowState(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            maximized=data["maximized"],
            schema_version=data["schema_version"],
        )
