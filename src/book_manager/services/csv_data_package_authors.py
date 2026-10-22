"""形式3の著者CSVの検査。共通CSV検査・日時検査は既存Preflightを利用する。"""
from book_manager.models.author import Author
from book_manager.models.csv_data_package import (
    AUTHORS_FILE_NAME, AUTHOR_ALIASES_FILE_NAME, BOOK_ITEM_AUTHORS_FILE_NAME,
    AUTHOR_HEADERS, AUTHOR_ALIAS_HEADERS, BOOK_ITEM_AUTHOR_HEADERS,
    AUTHOR_MANIFEST_COUNT_KEYS, AUTHOR_KEY_PREFIX, CURRENT_REQUIRED_FILE_NAMES, REQUIRED_FILE_NAMES,
    CsvDataPackageAuthor, CsvDataPackageAuthorAlias, CsvDataPackageBookItemAuthor,
)


def parse_author_csvs(parser, archive, manifest, books, issues):
    """全行の参照先・重複・順序・件数を検査して有効行を返す。"""
    version = manifest.format_version if manifest else None
    expected = CURRENT_REQUIRED_FILE_NAMES if version == 3 else REQUIRED_FILE_NAMES
    if version is not None and set(archive.namelist()) != set(expected):
        parser._add_error(issues, 'manifest.csv', None, 'format_version', str(version),
                          '形式VersionとZIP内のファイル構成が一致しません。')
    if version != 3:
        return (), (), ()
    authors, aliases, relations = [], [], []
    author_keys = {}
    contents = []
    for file_name, headers in ((AUTHORS_FILE_NAME, AUTHOR_HEADERS), (AUTHOR_ALIASES_FILE_NAME, AUTHOR_ALIAS_HEADERS),
                               (BOOK_ITEM_AUTHORS_FILE_NAME, BOOK_ITEM_AUTHOR_HEADERS)):
        if file_name not in archive.namelist():
            parser._add_error(issues, file_name, None, None, None, '形式3の必須CSVがありません。')
            return (), (), ()
        contents.append(parser._read_csv(archive, file_name=file_name, expected_headers=headers, issues=issues))
    for row_number, row in contents[0].rows:
        key, name, note, created, updated = row
        initial_count = len(issues)
        parser._validate_key(key, AUTHOR_KEY_PREFIX, AUTHORS_FILE_NAME, row_number, 'author_key', author_keys, issues)
        try:
            Author(name, disambiguation_note=note or None)
        except (TypeError, ValueError) as error:
            parser._add_error(issues, AUTHORS_FILE_NAME, row_number, '表示名／識別メモ', None, str(error))
        parser._validate_timestamp_pair(created, updated, AUTHORS_FILE_NAME, row_number, issues)
        if len(issues) == initial_count:
            authors.append(CsvDataPackageAuthor(key, name, created, updated, note or None))
    valid_author_keys = {author.author_key for author in authors}
    seen_aliases = set()
    for row_number, row in contents[1].rows:
        key, name = row
        initial_count = len(issues)
        if key not in valid_author_keys:
            parser._add_error(issues, AUTHOR_ALIASES_FILE_NAME, row_number, 'author_key', key, '参照する著者が存在しません。')
        try:
            Author(name)
        except (TypeError, ValueError) as error:
            parser._add_error(issues, AUTHOR_ALIASES_FILE_NAME, row_number, '別名', name, str(error))
        if (key, name) in seen_aliases:
            parser._add_error(issues, AUTHOR_ALIASES_FILE_NAME, row_number, '別名', name, '同じ著者の別名が重複しています。')
        seen_aliases.add((key, name))
        if len(issues) == initial_count:
            aliases.append(CsvDataPackageAuthorAlias(key, name))
    book_keys = {book.book_key for book in books}
    pairs, positions = set(), set()
    for row_number, row in contents[2].rows:
        book_key, author_key, position_text = row
        initial_count = len(issues)
        if book_key not in book_keys:
            parser._add_error(issues, BOOK_ITEM_AUTHORS_FILE_NAME, row_number, 'book_key', book_key, '参照する書籍が存在しません。')
        if author_key not in valid_author_keys:
            parser._add_error(issues, BOOK_ITEM_AUTHORS_FILE_NAME, row_number, 'author_key', author_key, '参照する著者が存在しません。')
        if (book_key, author_key) in pairs:
            parser._add_error(issues, BOOK_ITEM_AUTHORS_FILE_NAME, row_number, 'author_key', author_key, '同じ書籍・著者の関連が重複しています。')
        pairs.add((book_key, author_key))
        # ASCII decimal only; do not accept signs, floats or SQL integer overflow.
        if not position_text.isascii() or not position_text.isdecimal() or len(position_text) > 10:
            position = None
        else:
            position = int(position_text)
            if position > 2147483647:
                position = None
        if position is None:
            parser._add_error(issues, BOOK_ITEM_AUTHORS_FILE_NAME, row_number, '表示順', position_text, '表示順は0以上2147483647以下の整数で指定してください。')
        elif (book_key, position) in positions:
            parser._add_error(issues, BOOK_ITEM_AUTHORS_FILE_NAME, row_number, '表示順', position_text, '同じ書籍の表示順が重複しています。')
        positions.add((book_key, position))
        if len(issues) == initial_count:
            relations.append(CsvDataPackageBookItemAuthor(book_key, author_key, position))
    for key, content in zip(AUTHOR_MANIFEST_COUNT_KEYS, contents):
        if getattr(manifest, key) != content.physical_count:
            parser._add_error(issues, 'manifest.csv', None, key, str(getattr(manifest, key)),
                              f'manifest件数と実件数が一致しません: {content.physical_count}')
    return tuple(authors), tuple(aliases), tuple(relations)
