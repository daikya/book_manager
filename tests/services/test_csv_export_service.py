"""CsvExportServiceのテスト。"""

import csv
from pathlib import Path
import pytest
from book_manager.models.book_item import BookItem
from book_manager.services.csv_export_service import (
    CsvExportService,
)


def _read_csv(
    csv_path: Path,
) -> list[list[str]]:
    """CSVファイルを読み込む。"""
    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(
            csv.reader(file)
        )


def test_export_writes_headers(
    tmp_path: Path,
) -> None:
    """CSVヘッダーを仕様どおり出力する。"""
    output_path = tmp_path / "books.csv"

    service = CsvExportService()

    service.export(
        [],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows == [
        [
            "書籍名",
            "ISBN",
            "雑誌コード",
            "著者名",
            "出版社",
            "出版形態",
            "内容紹介",
            "読了年月",
            "読書状態",
            "お気に入り",
            "備考",
            "登録日時",
            "更新日時",
        ]
    ]


def test_export_writes_book_values(
    tmp_path: Path,
) -> None:
    """BookItemの値を正しい列順で出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="テスト書籍",
        isbn="9784000000000",
        magazine_code="12345",
        author="テスト著者",
        publisher="テスト出版社",
        publication_format="単行本",
        description="内容紹介",
        completion_month="2026-08",
        reading_status="reading",
        is_favorite=True,
        notes="備考",
        created_at="2026-08-20 10:00:00",
        updated_at="2026-08-20 11:00:00",
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1] == [
        "テスト書籍",
        "9784000000000",
        "12345",
        "テスト著者",
        "テスト出版社",
        "単行本",
        "内容紹介",
        "2026-08",
        "読書中",
        "はい",
        "備考",
        "2026-08-20 10:00:00",
        "2026-08-20 11:00:00",
    ]


def test_export_writes_multiple_books(
    tmp_path: Path,
) -> None:
    """複数書籍を複数行で出力する。"""
    output_path = tmp_path / "books.csv"

    books = [
        BookItem(
            title="書籍A",
        ),
        BookItem(
            title="書籍B",
        ),
    ]

    service = CsvExportService()

    service.export(
        books,
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert len(rows) == 3
    assert rows[1][0] == "書籍A"
    assert rows[2][0] == "書籍B"


def test_export_writes_none_as_empty_string(
    tmp_path: Path,
) -> None:
    """Noneを空欄として出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="テスト書籍",
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1] == [
        "テスト書籍",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "いいえ",
        "",
        "",
        "",
    ]


def test_export_preserves_newlines(
    tmp_path: Path,
) -> None:
    """内容紹介と備考の改行を保持する。"""
    output_path = tmp_path / "books.csv"

    description = (
        "1行目\n"
        "2行目"
    )
    notes = (
        "備考1\n"
        "備考2"
    )

    book = BookItem(
        title="テスト書籍",
        description=description,
        notes=notes,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][6] == description
    assert rows[1][10] == notes


def test_export_preserves_comma(
    tmp_path: Path,
) -> None:
    """カンマを含む文字列を保持する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="テスト,書籍",
        notes="メモ,追記",
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][0] == "テスト,書籍"
    assert rows[1][10] == "メモ,追記"


def test_export_preserves_double_quote(
    tmp_path: Path,
) -> None:
    """ダブルクォートを含む文字列を保持する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title='「"引用"」を含む書籍',
        notes='メモに"引用"あり',
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][0] == '「"引用"」を含む書籍'
    assert rows[1][10] == 'メモに"引用"あり'


def test_export_writes_utf8_bom(
    tmp_path: Path,
) -> None:
    """UTF-8 BOM付きで出力する。"""
    output_path = tmp_path / "books.csv"

    service = CsvExportService()

    service.export(
        [
            BookItem(
                title="日本語の書籍",
            )
        ],
        output_path,
    )

    data = output_path.read_bytes()

    assert data.startswith(
        b"\xef\xbb\xbf"
    )


def test_export_preserves_japanese_text(
    tmp_path: Path,
) -> None:
    """日本語を文字化けせず読み戻せる。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="日本語タイトル",
        author="日本語著者",
        publisher="日本語出版社",
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][0] == "日本語タイトル"
    assert rows[1][3] == "日本語著者"
    assert rows[1][4] == "日本語出版社"


def test_export_propagates_write_error(
    tmp_path: Path,
) -> None:
    """書き込みに失敗した場合は例外を呼び出し元へ伝える。"""
    output_path = tmp_path / "missing" / "books.csv"

    service = CsvExportService()

    book = BookItem(
        title="テスト書籍",
    )

    with pytest.raises(
        FileNotFoundError,
    ):
        service.export(
            [book],
            output_path,
        )

@pytest.mark.parametrize(
    (
        "reading_status",
        "expected",
    ),
    [
        ("unread", "未読"),
        ("reading", "読書中"),
        ("completed", "読了"),
    ],
)


def test_export_converts_reading_status_to_japanese(
    tmp_path: Path,
    reading_status: str,
    expected: str,
) -> None:
    """読書ステータスを日本語表示で出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="テスト書籍",
        reading_status=reading_status,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][8] == expected


def test_export_writes_none_reading_status_as_empty_string(
    tmp_path: Path,
) -> None:
    """未設定の読書ステータスを空欄として出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="テスト書籍",
        reading_status=None,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][8] == ""


def test_export_preserves_completion_month_with_reading_status(
    tmp_path: Path,
) -> None:
    """読了年月と読書状態を独立して出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="再読する書籍",
        completion_month="2025-05",
        reading_status="reading",
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][7] == "2025-05"
    assert rows[1][8] == "読書中"


def test_export_writes_true_is_favorite_as_yes(
    tmp_path: Path,
) -> None:
    """お気に入りONを「はい」として出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="お気に入り書籍",
        is_favorite=True,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][9] == "はい"


def test_export_writes_false_is_favorite_as_no(
    tmp_path: Path,
) -> None:
    """お気に入りOFFを「いいえ」として出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="通常書籍",
        is_favorite=False,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][9] == "いいえ"


def test_export_preserves_reading_status_with_is_favorite(
    tmp_path: Path,
) -> None:
    """読書状態とお気に入りを独立して出力する。"""
    output_path = tmp_path / "books.csv"

    book = BookItem(
        title="再読するお気に入り書籍",
        completion_month="2025-05",
        reading_status="reading",
        is_favorite=True,
    )

    service = CsvExportService()

    service.export(
        [book],
        output_path,
    )

    rows = _read_csv(
        output_path,
    )

    assert rows[1][7] == "2025-05"
    assert rows[1][8] == "読書中"
    assert rows[1][9] == "はい"