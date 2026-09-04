"""タグ名Validatorのテスト。"""

import pytest

from book_manager.validators.tag_validator import (
    MAX_TAG_NAME_LENGTH,
    validate_tag_name,
)


@pytest.mark.parametrize(
    "tag_name",
    [
        "小説",
        "Python 入門",
        "タグ,カンマ",
        'タグ"引用符',
        "あ" * MAX_TAG_NAME_LENGTH,
    ],
)
def test_validate_tag_name_accepts_valid_value(
    tag_name: str,
) -> None:
    """有効なタグ名を許可する。"""
    validate_tag_name(tag_name)


@pytest.mark.parametrize(
    "tag_name",
    [
        "",
        " ",
        "　",
    ],
)
def test_validate_tag_name_rejects_empty_value(
    tag_name: str,
) -> None:
    """空文字または空白だけのタグ名を拒否する。"""
    with pytest.raises(
        ValueError,
        match="タグ名を入力してください。",
    ):
        validate_tag_name(tag_name)


def test_validate_tag_name_rejects_too_long_value() -> None:
    """31文字以上のタグ名を拒否する。"""
    with pytest.raises(
        ValueError,
        match="タグ名は30文字以内で入力してください。",
    ):
        validate_tag_name(
            "あ" * (MAX_TAG_NAME_LENGTH + 1)
        )


@pytest.mark.parametrize(
    "tag_name",
    [
        "小説|歴史",
        "小説\n歴史",
        "小説\r歴史",
        "小説\r\n歴史",
    ],
)
def test_validate_tag_name_rejects_forbidden_character(
    tag_name: str,
) -> None:
    """区切り文字または改行を含むタグ名を拒否する。"""
    with pytest.raises(
        ValueError,
        match="タグ名に",
    ):
        validate_tag_name(tag_name)


@pytest.mark.parametrize(
    "tag_name",
    [
        None,
        1,
        True,
        (),
    ],
)
def test_validate_tag_name_rejects_non_string(
    tag_name: object,
) -> None:
    """文字列以外のタグ名を拒否する。"""
    with pytest.raises(
        ValueError,
        match="タグ名は文字列で指定してください。",
    ):
        validate_tag_name(
            tag_name,  # type: ignore[arg-type]
        )
