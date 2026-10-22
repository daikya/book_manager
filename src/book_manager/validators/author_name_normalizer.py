"""著者表示名を変更せず、検索・索引用のキーを生成する。"""
import unicodedata


def author_search_key(value: str) -> str:
    """NFKC・大文字小文字・空白を検索時だけ吸収する。

    中点・カンマ・ハイフン・生年等は除去しない。この値で人物を確定しない。
    """
    if not isinstance(value, str):
        raise TypeError('著者の検索語は文字列で指定してください。')
    normalized = unicodedata.normalize('NFKC', value).casefold()
    return ''.join(character for character in normalized if not character.isspace())
