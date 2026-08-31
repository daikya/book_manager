"""Tests for the CSV import result models."""

from dataclasses import FrozenInstanceError

import pytest

from book_manager.models.csv_import_result import (
    CsvImportIssue,
    CsvImportResult,
)


def test_csv_import_issue_can_store_values() -> None:
    """行番号とメッセージを保持できることを確認する。"""
    issue = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )

    assert issue.row_number == 3
    assert issue.message == "ISBNが既に登録されています。"


def test_csv_import_issue_is_immutable() -> None:
    """生成後に属性を変更できないことを確認する。"""
    issue = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )

    with pytest.raises(FrozenInstanceError):
        issue.row_number = 4  # type: ignore[misc]


def test_csv_import_issue_rejects_undefined_attribute() -> None:
    """未定義属性を追加できないことを確認する。"""
    issue = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )

    with pytest.raises((AttributeError, TypeError)):
        issue.unexpected = "value"  # type: ignore[attr-defined]


def test_csv_import_issues_with_same_values_are_equal() -> None:
    """同じ値を持つIssue同士が等しいことを確認する。"""
    first = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )
    second = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )

    assert first == second


def test_csv_import_result_can_store_values() -> None:
    """インポート結果を保持できることを確認する。"""
    skipped_issue = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )
    error_issue = CsvImportIssue(
        row_number=5,
        message="評価が不正です。",
    )

    result = CsvImportResult(
        imported_count=10,
        skipped_count=1,
        error_count=1,
        skipped=(skipped_issue,),
        errors=(error_issue,),
    )

    assert result.imported_count == 10
    assert result.skipped_count == 1
    assert result.error_count == 1
    assert result.skipped == (skipped_issue,)
    assert result.errors == (error_issue,)


def test_csv_import_result_can_store_empty_result() -> None:
    """スキップとエラーがない結果を保持できることを確認する。"""
    result = CsvImportResult(
        imported_count=0,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )

    assert result.imported_count == 0
    assert result.skipped_count == 0
    assert result.error_count == 0
    assert result.skipped == ()
    assert result.errors == ()


def test_csv_import_result_can_store_multiple_issues() -> None:
    """複数のスキップ・エラー情報を保持できることを確認する。"""
    skipped = (
        CsvImportIssue(
            row_number=2,
            message="ISBNが既に登録されています。",
        ),
        CsvImportIssue(
            row_number=4,
            message="雑誌コードが既に登録されています。",
        ),
    )
    errors = (
        CsvImportIssue(
            row_number=6,
            message="評価が不正です。",
        ),
        CsvImportIssue(
            row_number=8,
            message="読書状態が不正です。",
        ),
    )

    result = CsvImportResult(
        imported_count=5,
        skipped_count=2,
        error_count=2,
        skipped=skipped,
        errors=errors,
    )

    assert result.skipped == skipped
    assert result.errors == errors


def test_csv_import_result_is_immutable() -> None:
    """生成後に属性を変更できないことを確認する。"""
    result = CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.imported_count = 2  # type: ignore[misc]


def test_csv_import_result_rejects_undefined_attribute() -> None:
    """未定義属性を追加できないことを確認する。"""
    result = CsvImportResult(
        imported_count=1,
        skipped_count=0,
        error_count=0,
        skipped=(),
        errors=(),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.unexpected = "value"  # type: ignore[attr-defined]


def test_csv_import_results_with_same_values_are_equal() -> None:
    """同じ値を持つResult同士が等しいことを確認する。"""
    issue = CsvImportIssue(
        row_number=3,
        message="ISBNが既に登録されています。",
    )

    first = CsvImportResult(
        imported_count=2,
        skipped_count=1,
        error_count=0,
        skipped=(issue,),
        errors=(),
    )
    second = CsvImportResult(
        imported_count=2,
        skipped_count=1,
        error_count=0,
        skipped=(issue,),
        errors=(),
    )

    assert first == second
