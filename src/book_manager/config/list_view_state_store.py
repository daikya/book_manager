"""書籍一覧表示状態のJSON保存処理。"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from book_manager.models.list_view_state import ListViewState


logger = logging.getLogger(__name__)


class ListViewStateStoreError(RuntimeError):
    """一覧表示状態の保存または削除に失敗した場合の例外。"""


class ListViewStateStore:
    """一覧表示状態をJSONファイルで管理する。"""

    def __init__(self, path: Path) -> None:
        """状態ファイルの保存先を受け取る。"""
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """状態ファイルの保存先を返す。"""
        return self._path

    def load(self) -> ListViewState | None:
        """保存状態を読み込む。

        ファイルが存在しない場合や内容を利用できない場合は、
        起動を妨げないようにNoneを返す。
        """
        try:
            with self._path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            return ListViewState.from_dict(data)
        except FileNotFoundError:
            return None
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            logger.warning(
                "一覧表示状態を読み込めないため、"
                "初期状態を使用します: %s",
                self._path,
                exc_info=error,
            )
            return None

    def save(self, state: ListViewState) -> None:
        """一時ファイルを経由して保存先を置換する。"""
        if not isinstance(state, ListViewState):
            raise TypeError(
                "stateにはListViewStateを指定してください。"
            )

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
                    state.to_dict(),
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
            raise ListViewStateStoreError(
                "一覧表示状態を保存できません。"
            ) from error
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning(
                        "一覧表示状態の一時ファイルを"
                        "削除できません: %s",
                        temporary_path,
                        exc_info=True,
                    )

    def delete(self) -> None:
        """保存状態を削除する。存在しない場合は何もしない。"""
        try:
            self._path.unlink(missing_ok=True)
        except OSError as error:
            raise ListViewStateStoreError(
                "一覧表示状態を削除できません。"
            ) from error
