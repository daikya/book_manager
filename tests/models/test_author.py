"""人物IDと同名許可、入力境界を検証する。"""
from dataclasses import FrozenInstanceError
import pytest

from book_manager.models.author import Author


def test_same_name_can_belong_to_distinct_ids():
    first = Author('山田太郎', id=1)
    second = Author('山田太郎', id=2)
    assert first != second
    assert first.name == second.name


def test_valid_boundaries_and_note_newlines():
    author = Author('あ' * 200, aliases=('別名',), disambiguation_note='分野\n所属\t' + 'あ' * 1994)
    assert len(author.disambiguation_note) == 2000


@pytest.mark.parametrize('name', ['', '　', 'あ' * 201, '姓名\n別名', '姓名\t別名', '氏名\x00'])
def test_invalid_names(name):
    with pytest.raises(ValueError):
        Author(name)


@pytest.mark.parametrize('value', [None, 1, True])
def test_name_requires_text(value):
    with pytest.raises(TypeError):
        Author(value)


@pytest.mark.parametrize('author_id', [0, -1, True, '1', 1.0])
def test_id_requires_positive_integer(author_id):
    with pytest.raises(ValueError):
        Author('著者', id=author_id)


def test_aliases_are_immutable_and_validated():
    with pytest.raises(TypeError):
        Author('著者', aliases=['別名'])
    with pytest.raises(ValueError):
        Author('著者', aliases=('',))
    author = Author('著者', aliases=('別名',))
    with pytest.raises(FrozenInstanceError):
        author.name = '変更'


def test_invalid_notes():
    with pytest.raises(TypeError):
        Author('著者', disambiguation_note=42)
    with pytest.raises(ValueError):
        Author('著者', disambiguation_note='あ' * 2001)
    with pytest.raises(ValueError):
        Author('著者', disambiguation_note='メモ\x00')
