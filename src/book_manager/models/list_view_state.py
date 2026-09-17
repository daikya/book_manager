"""書籍一覧の保存状態を表すModel。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True, slots=True)
class ListViewState:
    """列幅と並び順を保持する。"""

    CURRENT_SCHEMA_VERSION: ClassVar[int] = 1
    MINIMUM_COLUMN_WIDTH: ClassVar[int] = 1
    MAXIMUM_COLUMN_WIDTH: ClassVar[int] = 4_096
    SUPPORTED_SORT_KEYS: ClassVar[tuple[str, ...]] = (
        "registered",
        "title",
        "author",
        "publisher",
        "completion_month",
        "reading_status",
        "is_favorite",
        "rating",
    )

    column_widths: dict[str, int]
    sort_by: str
    descending: bool
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """各項目を検証し、列幅の辞書をコピーする。"""
        self._validate_schema_version(self.schema_version)
        validated_widths = self._validate_column_widths(
            self.column_widths,
        )
        self._validate_sort_by(self.sort_by)

        if type(self.descending) is not bool:
            raise TypeError("descendingは真偽値で指定してください。")

        object.__setattr__(self, "column_widths", validated_widths)

    @classmethod
    def default(cls) -> ListViewState:
        """既定の並び順を持つ状態を返す。"""
        return cls(
            column_widths={},
            sort_by="registered",
            descending=True,
        )

    @classmethod
    def from_dict(cls, data: object) -> ListViewState:
        """JSON由来の辞書を検証して状態へ変換する。"""
        if not isinstance(data, dict):
            raise TypeError("一覧表示状態は辞書で指定してください。")

        required_keys = {
            "schema_version",
            "column_widths",
            "sort_by",
            "descending",
        }
        missing_keys = required_keys.difference(data)
        if missing_keys:
            missing_names = ", ".join(sorted(missing_keys))
            raise ValueError(
                f"一覧表示状態の必須項目がありません: {missing_names}"
            )

        return cls(
            schema_version=data["schema_version"],
            column_widths=data["column_widths"],
            sort_by=data["sort_by"],
            descending=data["descending"],
        )

    def to_dict(self) -> dict[str, Any]:
        """JSONへ保存できる辞書へ変換する。"""
        return {
            "schema_version": self.schema_version,
            "column_widths": dict(self.column_widths),
            "sort_by": self.sort_by,
            "descending": self.descending,
        }

    @classmethod
    def _validate_schema_version(cls, value: object) -> None:
        """schema Versionを検証する。"""
        if type(value) is not int:
            raise TypeError("schema_versionは整数で指定してください。")
        if value != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "schema_versionは"
                f"{cls.CURRENT_SCHEMA_VERSION}で指定してください。"
            )

    @classmethod
    def _validate_column_widths(
        cls,
        value: object,
    ) -> dict[str, int]:
        """列IDと列幅の辞書を検証してコピーする。"""
        if not isinstance(value, dict):
            raise TypeError("column_widthsは辞書で指定してください。")

        validated: dict[str, int] = {}
        for column_id, width in value.items():
            if not isinstance(column_id, str):
                raise TypeError("列IDは文字列で指定してください。")
            if not column_id:
                raise ValueError("列IDに空文字列は指定できません。")
            if type(width) is not int:
                raise TypeError(
                    f"列幅({column_id})は整数で指定してください。"
                )
            if not cls.MINIMUM_COLUMN_WIDTH <= width <= cls.MAXIMUM_COLUMN_WIDTH:
                raise ValueError(
                    f"列幅({column_id})は"
                    f"{cls.MINIMUM_COLUMN_WIDTH}以上"
                    f"{cls.MAXIMUM_COLUMN_WIDTH}以下で指定してください。"
                )
            validated[column_id] = width

        return validated

    @classmethod
    def _validate_sort_by(cls, value: object) -> None:
        """並び替えの内部識別子を検証する。"""
        if not isinstance(value, str):
            raise TypeError("sort_byは文字列で指定してください。")
        if value not in cls.SUPPORTED_SORT_KEYS:
            message = (
                "sort_byには対応している項目を"
                "指定してください。"
            )
            raise ValueError(message)
