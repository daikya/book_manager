"""メインウィンドウの保存状態を表すModel。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class WindowState:
    """通常表示時の矩形と終了時の最大化状態を保持する。"""

    MINIMUM_COORDINATE: ClassVar[int] = -100_000
    MAXIMUM_COORDINATE: ClassVar[int] = 100_000
    MINIMUM_SIZE: ClassVar[int] = 1
    MAXIMUM_SIZE: ClassVar[int] = 32_767
    CURRENT_SCHEMA_VERSION: ClassVar[int] = 1

    x: int
    y: int
    width: int
    height: int
    maximized: bool
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """各項目の型と範囲を検証する。"""
        self._validate_integer(
            "x",
            self.x,
            self.MINIMUM_COORDINATE,
            self.MAXIMUM_COORDINATE,
        )
        self._validate_integer(
            "y",
            self.y,
            self.MINIMUM_COORDINATE,
            self.MAXIMUM_COORDINATE,
        )
        self._validate_integer(
            "width",
            self.width,
            self.MINIMUM_SIZE,
            self.MAXIMUM_SIZE,
        )
        self._validate_integer(
            "height",
            self.height,
            self.MINIMUM_SIZE,
            self.MAXIMUM_SIZE,
        )
        self._validate_integer(
            "schema_version",
            self.schema_version,
            self.CURRENT_SCHEMA_VERSION,
            self.CURRENT_SCHEMA_VERSION,
        )

        if type(self.maximized) is not bool:
            raise TypeError("maximizedは真偽値で指定してください。")

    @staticmethod
    def _validate_integer(
        field_name: str,
        value: object,
        minimum: int,
        maximum: int,
    ) -> None:
        """真偽値を除く整数であり、指定範囲内であることを検証する。"""
        if type(value) is not int:
            raise TypeError(f"{field_name}は整数で指定してください。")
        if not minimum <= value <= maximum:
            raise ValueError(
                f"{field_name}は{minimum}以上{maximum}以下で指定してください。"
            )
