"""Tests for CsvImportService."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import csv
from datetime import datetime

from book_manager.services.book_service import BookService
from book_manager.services.csv_export_service import (
    CsvExportService,
)
from book_manager.services.csv_import_service import CsvImportService
from book_manager.models.csv_import_result import (
    CsvImportIssue,
    CsvImportResult,
)
from book_manager.database.initializer import initialize_database
from book_manager.repositories.book_repository import BookRepository


def test_csv_import_service_can_be_created() -> None:
    """BookServiceを指定して生成できることを確認する。"""
    book_service = Mock(spec=BookService)

    service = CsvImportService(
        book_service=book_service,
    )

    assert service._book_service is book_service


def test_import_file_accepts_valid_header(
    tmp_path: Path,
) -> None:
    """正しいCSVヘッダーを受け付けることを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        (
            "書籍名,ISBN,雑誌コード,著者名,出版社,出版形態,"
            "内容紹介,読了年月,読書状態,お気に入り,評価,備考,"
            "登録日時,更新日時\n"
        ),
        encoding="utf-8-sig",
    )

    result = service.import_file(input_path)

    assert result.imported_count == 0
    assert result.skipped_count == 0
    assert result.error_count == 0
    assert result.skipped == ()
    assert result.errors == ()


def test_import_file_rejects_invalid_header_name(
    tmp_path: Path,
) -> None:
    """ヘッダー名が不正なCSVを拒否することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        (
            "タイトル,ISBN,雑誌コード,著者名,出版社,出版形態,"
            "内容紹介,読了年月,読書状態,お気に入り,評価,備考,"
            "登録日時,更新日時\n"
        ),
        encoding="utf-8-sig",
    )

    with pytest.raises(ValueError):
        service.import_file(input_path)


def test_import_file_rejects_invalid_header_order(
    tmp_path: Path,
) -> None:
    """ヘッダーの列順が不正なCSVを拒否することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        (
            "ISBN,書籍名,雑誌コード,著者名,出版社,出版形態,"
            "内容紹介,読了年月,読書状態,お気に入り,評価,備考,"
            "登録日時,更新日時\n"
        ),
        encoding="utf-8-sig",
    )

    with pytest.raises(ValueError):
        service.import_file(input_path)


def test_import_file_rejects_empty_file(
    tmp_path: Path,
) -> None:
    """空のCSVファイルを拒否することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        "",
        encoding="utf-8-sig",
    )

    with pytest.raises(
        ValueError,
        match="CSVヘッダーが存在しません。",
    ):
        service.import_file(input_path)


def test_import_file_accepts_header_only_file(
    tmp_path: Path,
) -> None:
    """ヘッダーだけのCSVを空のインポート結果として扱うことを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        (
            "書籍名,ISBN,雑誌コード,著者名,出版社,出版形態,"
            "内容紹介,読了年月,読書状態,お気に入り,評価,備考,"
            "登録日時,更新日時\n"
        ),
        encoding="utf-8-sig",
    )

    result = service.import_file(input_path)

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )


def test_import_file_rejects_malformed_csv(
    tmp_path: Path,
) -> None:
    """CSVとして正常に解析できないファイルを拒否することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"
    input_path.write_text(
        (
            "書籍名,ISBN,雑誌コード,著者名,出版社,出版形態,"
            "内容紹介,読了年月,読書状態,お気に入り,評価,備考,"
            "登録日時,更新日時\n"
            '"閉じられていない引用符,9784101010014,,,,,,,,,,,,\n'
        ),
        encoding="utf-8-sig",
    )

    with pytest.raises(
        ValueError,
        match="CSVとして正常に解析できません。",
    ):
        service.import_file(input_path)


@pytest.mark.parametrize(
    ("csv_value", "expected"),
    [
        ("", None),
        ("未読", "unread"),
        ("読書中", "reading"),
        ("読了", "completed"),
    ],
)
def test_convert_reading_status(
    csv_value: str,
    expected: str | None,
) -> None:
    """読書状態を内部値へ変換できることを確認する。"""
    assert (
        CsvImportService._convert_reading_status(csv_value)
        == expected
    )


def test_convert_reading_status_rejects_invalid_value() -> None:
    """不正な読書状態を拒否することを確認する。"""
    with pytest.raises(
        ValueError,
        match="読書状態が不正です。",
    ):
        CsvImportService._convert_reading_status(
            "積読",
        )


@pytest.mark.parametrize(
    ("csv_value", "expected"),
    [
        ("はい", True),
        ("いいえ", False),
    ],
)
def test_convert_is_favorite(
    csv_value: str,
    expected: bool,
) -> None:
    """お気に入り状態をboolへ変換できることを確認する。"""
    assert (
        CsvImportService._convert_is_favorite(csv_value)
        is expected
    )


@pytest.mark.parametrize(
    "csv_value",
    [
        "",
        "YES",
        "true",
    ],
)
def test_convert_is_favorite_rejects_invalid_value(
    csv_value: str,
) -> None:
    """不正なお気に入り状態を拒否することを確認する。"""
    with pytest.raises(
        ValueError,
        match="お気に入りが不正です。",
    ):
        CsvImportService._convert_is_favorite(
            csv_value,
        )


@pytest.mark.parametrize(
    ("csv_value", "expected"),
    [
        ("", None),
        ("1", 1),
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("5", 5),
    ],
)
def test_convert_rating(
    csv_value: str,
    expected: int | None,
) -> None:
    """評価をintまたはNoneへ変換できることを確認する。"""
    assert (
        CsvImportService._convert_rating(csv_value)
        == expected
    )


@pytest.mark.parametrize(
    "csv_value",
    [
        "0",
        "6",
        "-1",
        "abc",
        "1.5",
    ],
)
def test_convert_rating_rejects_invalid_value(
    csv_value: str,
) -> None:
    """不正な評価を拒否することを確認する。"""
    with pytest.raises(
        ValueError,
        match="評価が不正です。",
    ):
        CsvImportService._convert_rating(
            csv_value,
        )


def test_import_file_imports_valid_row(
    tmp_path: Path,
) -> None:
    """正常なCSVデータ行を書籍として登録できることを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "テスト書籍",
                "9784101010014",
                "",
                "テスト著者",
                "テスト出版社",
                "単行本",
                "テスト内容紹介",
                "202608",
                "読書中",
                "はい",
                "4",
                "テスト備考",
                "2026-08-01 10:00:00",
                "2026-08-02 11:00:00",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_called_once_with(
        title="テスト書籍",
        isbn="9784101010014",
        magazine_code="",
        author="テスト著者",
        publisher="テスト出版社",
        publication_format="単行本",
        description="テスト内容紹介",
        completion_month="202608",
        reading_status="reading",
        is_favorite=True,
        rating=4,
        tags=(),
        notes="テスト備考",
    )

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )


def test_import_file_records_error_for_invalid_column_count(
    tmp_path: Path,
) -> None:
    """列数が不正なデータ行をエラーとして記録することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "列不足の書籍",
                "9784101010014",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="列数が不正です。",
            ),
        ),
    )


@pytest.mark.parametrize(
    (
        "reading_status",
        "is_favorite",
        "rating",
        "expected_message",
    ),
    [
        (
            "積読",
            "はい",
            "3",
            "読書状態が不正です。",
        ),
        (
            "未読",
            "",
            "3",
            "お気に入りが不正です。",
        ),
        (
            "未読",
            "はい",
            "6",
            "評価が不正です。",
        ),
    ],
)
def test_import_file_records_error_for_invalid_converted_value(
    tmp_path: Path,
    reading_status: str,
    is_favorite: str,
    rating: str,
    expected_message: str,
) -> None:
    """変換対象の値が不正な行をエラーとして記録することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "エラー書籍",
                "9784101010014",
                "",
                "テスト著者",
                "テスト出版社",
                "単行本",
                "テスト内容紹介",
                "202608",
                reading_status,
                is_favorite,
                rating,
                "テスト備考",
                "2026-08-01 10:00:00",
                "2026-08-02 11:00:00",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message=expected_message,
            ),
        ),
    )


def test_import_file_continues_after_row_error(
    tmp_path: Path,
) -> None:
    """エラー行があっても後続の正常行を登録することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "エラー書籍",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "積読",
                "はい",
                "",
                "",
                "",
                "",
            )
        )
        writer.writerow(
            (
                "正常書籍",
                "9784101010021",
                "",
                "正常著者",
                "正常出版社",
                "単行本",
                "正常な内容紹介",
                "202608",
                "読了",
                "いいえ",
                "5",
                "正常な備考",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_called_once_with(
        title="正常書籍",
        isbn="9784101010021",
        magazine_code="",
        author="正常著者",
        publisher="正常出版社",
        publication_format="単行本",
        description="正常な内容紹介",
        completion_month="202608",
        reading_status="completed",
        is_favorite=False,
        rating=5,
        tags=(),
        notes="正常な備考",
    )

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="読書状態が不正です。",
            ),
        ),
    )


def test_import_file_skips_existing_isbn(
    tmp_path: Path,
) -> None:
    """既存ISBNと重複する行をスキップすることを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = [
        Mock(),
    ]
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "重複書籍",
                "9784101010014",
                "",
                "テスト著者",
                "テスト出版社",
                "単行本",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.find_books_by_isbn.assert_called_once_with(
        "9784101010014",
    )
    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=2,
                message="ISBNが既存データと重複しています。",
            ),
        ),
        errors=(),
    )


def test_import_file_skips_existing_magazine_code(
    tmp_path: Path,
) -> None:
    """既存雑誌コードと重複する行をスキップすることを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_magazine_code.return_value = [
        Mock(),
    ]
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "重複雑誌",
                "",
                "12345-01",
                "",
                "テスト出版社",
                "雑誌",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.find_books_by_magazine_code.assert_called_once_with(
        "12345-01",
    )
    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=2,
                message="雑誌コードが既存データと重複しています。",
            ),
        ),
        errors=(),
    )


def test_import_file_does_not_check_duplicate_when_identifiers_are_empty(
    tmp_path: Path,
) -> None:
    """ISBNと雑誌コードが空の場合は識別子の重複確認を行わない。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "識別子なし書籍",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.find_books_by_isbn.assert_not_called()
    book_service.find_books_by_magazine_code.assert_not_called()
    book_service.add_book.assert_called_once()

    assert result.imported_count == 1
    assert result.skipped_count == 0
    assert result.error_count == 0


def test_import_file_skips_by_isbn_before_magazine_code(
    tmp_path: Path,
) -> None:
    """ISBN重複時は雑誌コードの重複確認を行わないことを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = [
        Mock(),
    ]
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "重複書籍",
                "9784101010014",
                "12345-01",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.find_books_by_isbn.assert_called_once_with(
        "9784101010014",
    )
    book_service.find_books_by_magazine_code.assert_not_called()
    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=2,
                message="ISBNが既存データと重複しています。",
            ),
        ),
        errors=(),
    )


def test_import_file_skips_duplicate_isbn_within_csv(
    tmp_path: Path,
) -> None:
    """CSV内で後続行のISBNが重複した場合にスキップすることを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.side_effect = [
        [],
        [Mock()],
    ]
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "1冊目",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )
        writer.writerow(
            (
                "2冊目",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    assert book_service.find_books_by_isbn.call_count == 2
    book_service.add_book.assert_called_once()

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=3,
                message="ISBNが既存データと重複しています。",
            ),
        ),
        errors=(),
    )


def test_import_file_records_book_service_value_error(
    tmp_path: Path,
) -> None:
    """BookServiceの入力値エラーを行エラーとして記録することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    book_service.add_book.side_effect = ValueError(
        "ISBNの形式が不正です。",
    )
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "不正な書籍",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="ISBNの形式が不正です。",
            ),
        ),
    )


def test_import_file_continues_after_book_service_value_error(
    tmp_path: Path,
) -> None:
    """BookServiceの入力値エラー後も後続行を処理することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    book_service.add_book.side_effect = [
        ValueError("ISBNの形式が不正です。"),
        Mock(),
    ]
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )

        for title, isbn in (
            ("不正な書籍", "9784101010014"),
            ("正常な書籍", "9784101010021"),
        ):
            writer.writerow(
                (
                    title,
                    isbn,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "未読",
                    "いいえ",
                    "",
                    "",
                    "",
                    "",
                )
            )

    result = service.import_file(input_path)

    assert book_service.add_book.call_count == 2

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="ISBNの形式が不正です。",
            ),
        ),
    )


def test_import_file_records_isbn_lookup_value_error(
    tmp_path: Path,
) -> None:
    """ISBN重複確認時の入力値エラーを行エラーとして記録することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.side_effect = ValueError(
        "ISBNの形式が不正です。",
    )
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "不正ISBN書籍",
                "invalid-isbn",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="ISBNの形式が不正です。",
            ),
        ),
    )


def test_import_file_records_magazine_code_lookup_value_error(
    tmp_path: Path,
) -> None:
    """雑誌コード重複確認時の入力値エラーを行エラーとして記録することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_magazine_code.side_effect = ValueError(
        "雑誌コードの形式が不正です。",
    )
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "不正雑誌",
                "",
                "invalid-code",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="雑誌コードの形式が不正です。",
            ),
        ),
    )


def test_import_file_propagates_unexpected_add_book_error(
    tmp_path: Path,
) -> None:
    """登録時の予期しない例外を呼び出し元へ伝播することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    book_service.add_book.side_effect = RuntimeError(
        "予期しないエラー",
    )
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "テスト書籍",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    with pytest.raises(
        RuntimeError,
        match="予期しないエラー",
    ):
        service.import_file(input_path)


def test_import_file_propagates_unexpected_lookup_error(
    tmp_path: Path,
) -> None:
    """重複確認時の予期しない例外を呼び出し元へ伝播することを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.side_effect = RuntimeError(
        "検索処理エラー",
    )
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "テスト書籍",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    with pytest.raises(
        RuntimeError,
        match="検索処理エラー",
    ):
        service.import_file(input_path)


def test_import_file_skips_duplicate_isbn_with_real_database(
    tmp_path: Path,
) -> None:
    """実DB上でCSV内の重複ISBNがスキップされることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"
    initialize_database(database_path)

    repository = BookRepository(database_path)
    book_service = BookService(
        repository,
        now_provider=lambda: datetime(
            2026,
            8,
            31,
            10,
            0,
            0,
        ),
    )
    service = CsvImportService(
        book_service=book_service,
    )

    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "1冊目",
                "9784101010014",
                "",
                "著者A",
                "出版社A",
                "単行本",
                "1冊目の内容",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )
        writer.writerow(
            (
                "2冊目",
                "9784101010014",
                "",
                "著者B",
                "出版社B",
                "文庫",
                "2冊目の内容",
                "",
                "読書中",
                "はい",
                "4",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=3,
                message="ISBNが既存データと重複しています。",
            ),
        ),
        errors=(),
    )

    books = book_service.find_books_by_isbn(
        "9784101010014",
    )

    assert len(books) == 1
    assert books[0].title == "1冊目"
    assert books[0].author == "著者A"


def test_import_file_skips_duplicate_magazine_code_with_real_database(
    tmp_path: Path,
) -> None:
    """実DB上でCSV内の重複雑誌コードがスキップされることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"
    initialize_database(database_path)

    repository = BookRepository(database_path)
    book_service = BookService(
        repository,
        now_provider=lambda: datetime(
            2026,
            8,
            31,
            10,
            0,
            0,
        ),
    )
    service = CsvImportService(
        book_service=book_service,
    )

    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "雑誌1冊目",
                "",
                "12345",
                "著者A",
                "出版社A",
                "雑誌",
                "1冊目の内容",
                "",
                "未読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )
        writer.writerow(
            (
                "雑誌2冊目",
                "",
                "12345",
                "著者B",
                "出版社B",
                "雑誌",
                "2冊目の内容",
                "",
                "読書中",
                "はい",
                "4",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=1,
        error_count=0,
        skipped=(
            CsvImportIssue(
                row_number=3,
                message=(
                    "雑誌コードが既存データと重複しています。"
                ),
            ),
        ),
        errors=(),
    )

    books = book_service.find_books_by_magazine_code(
        "12345",
    )

    assert len(books) == 1
    assert books[0].title == "雑誌1冊目"
    assert books[0].author == "著者A"


def test_import_file_uses_logical_csv_record_number(
    tmp_path: Path,
) -> None:
    """フィールド内改行があっても論理CSVレコード番号を使用することを確認する。"""
    book_service = Mock(spec=BookService)
    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                "改行を含む書籍",
                "",
                "",
                "",
                "",
                "",
                "1行目\n2行目",
                "",
                "積読",
                "いいえ",
                "",
                "",
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    book_service.add_book.assert_not_called()

    assert result == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=1,
        skipped=(),
        errors=(
            CsvImportIssue(
                row_number=2,
                message="読書状態が不正です。",
            ),
        ),
    )


def test_import_file_preserves_special_characters_in_fields(
    tmp_path: Path,
) -> None:
    """カンマ、ダブルクォート、改行を含む値を正しく取り込むことを確認する。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []

    service = CsvImportService(
        book_service=book_service,
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            CsvImportService.LEGACY_HEADERS,
        )
        writer.writerow(
            (
                'カンマ,と"引用符"を含む書籍',
                "9784101010014",
                "",
                '著者A,著者B',
                "出版社",
                "単行本",
                '1行目,カンマあり\n2行目に"引用符"あり',
                "",
                "未読",
                "いいえ",
                "",
                '備考1行目\n備考2行目,"補足"',
                "",
                "",
            )
        )

    result = service.import_file(input_path)

    assert result == CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )

    book_service.add_book.assert_called_once_with(
        title='カンマ,と"引用符"を含む書籍',
        isbn="9784101010014",
        magazine_code="",
        author="著者A,著者B",
        publisher="出版社",
        publication_format="単行本",
        description='1行目,カンマあり\n2行目に"引用符"あり',
        completion_month="",
        reading_status="unread",
        is_favorite=False,
        rating=None,
        tags=(),
        notes='備考1行目\n備考2行目,"補足"',
    )


def test_import_file_accepts_new_header(
    tmp_path: Path,
) -> None:
    """タグ列を含む新しい15列ヘッダーを受け付ける。"""
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        csv.writer(file).writerow(CsvImportService.V26_HEADERS)

    service = CsvImportService(
        book_service=Mock(spec=BookService),
    )

    assert service.import_file(input_path) == CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )


@pytest.mark.parametrize(
    ("csv_value", "expected"),
    [
        ("", ()),
        ("小説", ("小説",)),
        (
            " 小説 | 歴史 |小説 ",
            ("小説", "歴史", "小説"),
        ),
    ],
)
def test_convert_tags(
    csv_value: str,
    expected: tuple[str, ...],
) -> None:
    """タグ欄を分割し、各タグの前後空白を除去する。"""
    assert CsvImportService._convert_tags(csv_value) == expected


def test_import_file_passes_tags_to_book_service(
    tmp_path: Path,
) -> None:
    """新形式CSVのタグをBookServiceへ渡す。"""
    book_service = Mock(spec=BookService)
    book_service.find_books_by_isbn.return_value = []
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(CsvImportService.V26_HEADERS)
        writer.writerow(
            (
                "タグ付き書籍",
                "9784101010014",
                "",
                "著者",
                "出版社",
                "単行本",
                "内容紹介",
                "202608",
                "読書中",
                "はい",
                "4",
                " 小説 | 歴史 |小説 ",
                "備考",
                "",
                "",
            )
        )

    result = CsvImportService(
        book_service=book_service,
    ).import_file(input_path)

    assert result.imported_count == 1
    book_service.add_book.assert_called_once_with(
        title="タグ付き書籍",
        isbn="9784101010014",
        magazine_code="",
        author="著者",
        publisher="出版社",
        publication_format="単行本",
        description="内容紹介",
        completion_month="202608",
        reading_status="reading",
        is_favorite=True,
        rating=4,
        tags=("小説", "歴史", "小説"),
        notes="備考",
    )


def test_import_file_passes_empty_tags_for_legacy_csv(
    tmp_path: Path,
) -> None:
    """旧14列形式では空のタグをBookServiceへ渡す。"""
    book_service = Mock(spec=BookService)
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(CsvImportService.LEGACY_HEADERS)
        writer.writerow(
            (
                "旧形式書籍",
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
                "",
            )
        )

    result = CsvImportService(
        book_service=book_service,
    ).import_file(input_path)

    assert result.imported_count == 1
    assert book_service.add_book.call_args.kwargs["tags"] == ()


def test_import_file_registers_and_reuses_tags(
    tmp_path: Path,
) -> None:
    """未登録タグを登録し、同名タグを複数書籍で再利用する。"""
    database_path = tmp_path / "books.db"
    initialize_database(database_path)
    repository = BookRepository(database_path)
    book_service = BookService(
        repository,
        now_provider=lambda: datetime(2026, 9, 4, 10, 0),
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(CsvImportService.V26_HEADERS)
        for title in ("1冊目", "2冊目"):
            writer.writerow(
                (
                    title,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "未読",
                    "いいえ",
                    "",
                    " 共通タグ | 技術書 ",
                    "",
                    "",
                    "",
                )
            )

    result = CsvImportService(
        book_service=book_service,
    ).import_file(input_path)

    assert result.imported_count == 2
    assert [tag.name for tag in book_service.get_all_tags()] == [
        "共通タグ",
        "技術書",
    ]
    assert all(
        book.tags == ("共通タグ", "技術書")
        for book in book_service.get_all_books()
    )


def test_import_file_does_not_keep_tags_from_error_row(
    tmp_path: Path,
) -> None:
    """不正タグを含む行では書籍とタグを登録しない。"""
    database_path = tmp_path / "books.db"
    initialize_database(database_path)
    book_service = BookService(BookRepository(database_path))
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(CsvImportService.V26_HEADERS)
        writer.writerow(
            (
                "不正タグ書籍",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                f"正常タグ|{'あ' * 31}",
                "",
                "",
                "",
            )
        )

    result = CsvImportService(
        book_service=book_service,
    ).import_file(input_path)

    assert result.imported_count == 0
    assert result.error_count == 1
    assert result.errors[0].message == (
        "タグ名は30文字以内で入力してください。"
    )
    assert book_service.get_all_books() == []
    assert book_service.get_all_tags() == []


def test_import_file_does_not_keep_tags_from_duplicate_row(
    tmp_path: Path,
) -> None:
    """重複によりスキップした行のタグを登録しない。"""
    database_path = tmp_path / "books.db"
    initialize_database(database_path)
    book_service = BookService(BookRepository(database_path))
    book_service.add_book(
        title="登録済み",
        isbn="9784101010014",
    )
    input_path = tmp_path / "books.csv"

    with input_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(CsvImportService.V26_HEADERS)
        writer.writerow(
            (
                "重複書籍",
                "9784101010014",
                "",
                "",
                "",
                "",
                "",
                "",
                "未読",
                "いいえ",
                "",
                "登録されないタグ",
                "",
                "",
                "",
            )
        )

    result = CsvImportService(
        book_service=book_service,
    ).import_file(input_path)

    assert result.skipped_count == 1
    assert book_service.get_all_tags() == []


def test_exported_csv_can_restore_tags_on_import(
    tmp_path: Path,
) -> None:
    """エクスポートした新形式CSVからタグを復元する。"""
    source_path = tmp_path / "source.db"
    destination_path = tmp_path / "destination.db"
    initialize_database(source_path)
    initialize_database(destination_path)
    source_service = BookService(BookRepository(source_path))
    destination_service = BookService(
        BookRepository(destination_path)
    )
    registered = source_service.add_book(
        title="往復確認",
        tags=("技術書", "Python"),
    )
    csv_path = tmp_path / "books.csv"
    CsvExportService().export([registered], csv_path)

    result = CsvImportService(
        book_service=destination_service,
    ).import_file(csv_path)

    assert result.imported_count == 1
    imported = destination_service.get_all_books()
    assert len(imported) == 1
    assert imported[0].tags == ("Python", "技術書")


def test_new_csv_import_preserves_reference_isbn(tmp_path: Path) -> None:
    from book_manager.models.book_item import BookItem
    source = tmp_path / "new.csv"
    database = tmp_path / "new.db"
    initialize_database(database)
    books = BookService(BookRepository(database))
    CsvExportService().export([
        BookItem(title="音声版", reference_isbn="9784101010014"),
        BookItem(title="電子版", reference_isbn="9784101010014"),
    ], source)
    result = CsvImportService(book_service=books).import_file(source)
    assert result.imported_count == 2
    assert result.error_count == result.skipped_count == 0
    assert [book.reference_isbn for book in books.get_all_books()] == ["9784101010014"] * 2
