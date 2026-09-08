"""Tests for ReadingHistoryService."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)
from book_manager.repositories.book_repository import BookRepository
from book_manager.repositories.reading_history_repository import (
    ReadingHistoryRepository,
)
from book_manager.services.reading_history_service import (
    ReadingHistoryService,
)


FIXED_NOW = datetime(2026, 9, 7, 10, 30, 0)
UPDATED_NOW = datetime(2026, 9, 8, 11, 45, 30)


@pytest.fixture
def components(
    tmp_path: Path,
) -> tuple[BookRepository, ReadingHistoryService]:
    """同じ一時DBを使用するBookRepositoryとServiceを返す。"""
    database_path = tmp_path / "test_book_manager.db"
    initialize_database(database_path)
    book_repository = BookRepository(database_path)
    history_repository = ReadingHistoryRepository(database_path)
    service = ReadingHistoryService(
        history_repository,
        book_repository,
        now_provider=lambda: FIXED_NOW,
    )

    return book_repository, service


def add_book(
    book_repository: BookRepository,
    *,
    title: str = "吾輩は猫である",
    reading_status: str | None = "completed",
    completion_month: str | None = "2026-08",
) -> BookItem:
    """テスト用書籍を登録する。"""
    return book_repository.add(
        BookItem(
            title=title,
            reading_status=reading_status,
            completion_month=completion_month,
            created_at="2026-09-01 10:00:00",
            updated_at="2026-09-01 10:00:00",
        )
    )


def test_add_history_registers_normalized_values_and_timestamps(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """入力値を正規化し、登録日時と更新日時を設定する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    registered = service.add_history(
        book_item_id=book.id,
        started_on=" 2026-08-01 ",
        completed_on=" 2026-08-31 ",
        notes="  読了した。  ",
    )

    assert registered.id is not None
    assert registered.started_on == "2026-08-01"
    assert registered.completed_on == "2026-08-31"
    assert registered.notes == "読了した。"
    assert registered.created_at == "2026-09-07 10:30:00"
    assert registered.updated_at == "2026-09-07 10:30:00"


@pytest.mark.parametrize(
    ("started_on", "completed_on", "notes"),
    [
        ("2026-09-01", None, None),
        (None, "2026-09-07", None),
        (None, None, "読書メモだけを記録する。"),
    ],
)
def test_add_history_accepts_each_single_value(
    components: tuple[BookRepository, ReadingHistoryService],
    started_on: str | None,
    completed_on: str | None,
    notes: str | None,
) -> None:
    """開始日、読了日またはメモだけでも登録できる。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    registered = service.add_history(
        book_item_id=book.id,
        started_on=started_on,
        completed_on=completed_on,
        notes=notes,
    )

    assert registered.id is not None


def test_add_history_converts_blank_values_to_none(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """空白だけの任意入力をNoneへ変換する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    registered = service.add_history(
        book_item_id=book.id,
        started_on="   ",
        completed_on="\t",
        notes=" メモ ",
    )

    assert registered.started_on is None
    assert registered.completed_on is None
    assert registered.notes == "メモ"


def test_add_history_rejects_all_empty_values(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """すべて未設定の履歴を拒否する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    with pytest.raises(
        ValueError,
        match="読書開始日、読了日、読書メモのいずれか",
    ):
        service.add_history(
            book_item_id=book.id,
            started_on=" ",
            completed_on=None,
            notes=" ",
        )


@pytest.mark.parametrize(
    ("started_on", "completed_on", "message"),
    [
        (
            "2026/09/01",
            None,
            "読書開始日はYYYY-MM-DD形式で入力してください。",
        ),
        (
            None,
            "2026-02-30",
            "読了日に実在する日付を入力してください。",
        ),
        (
            "2026-09-08",
            "2026-09-07",
            "読書開始日は読了日以前の日付を入力してください。",
        ),
    ],
)
def test_add_history_rejects_invalid_dates(
    components: tuple[BookRepository, ReadingHistoryService],
    started_on: str | None,
    completed_on: str | None,
    message: str,
) -> None:
    """不正な日付と前後関係を拒否する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    with pytest.raises(ValueError, match=message):
        service.add_history(
            book_item_id=book.id,
            started_on=started_on,
            completed_on=completed_on,
        )


def test_add_history_rejects_missing_book(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """存在しない書籍への登録を拒否する。"""
    _, service = components

    with pytest.raises(
        ValueError,
        match="対象の書籍が見つかりません。",
    ):
        service.add_history(
            book_item_id=999,
            notes="メモ",
        )


def test_get_history_returns_registered_history(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """IDを指定して履歴を取得する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None
    registered = service.add_history(
        book_item_id=book.id,
        notes="メモ",
    )
    assert registered.id is not None

    assert service.get_history(registered.id) == registered
    assert service.get_history(999) is None


def test_get_histories_for_book_distinguishes_empty_and_missing(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """履歴0件と存在しない書籍を区別する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None

    assert service.get_histories_for_book(book.id) == []

    with pytest.raises(
        ValueError,
        match="対象の書籍が見つかりません。",
    ):
        service.get_histories_for_book(999)


def test_get_histories_for_book_returns_registered_histories(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """指定書籍の履歴一覧を取得する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None
    first = service.add_history(
        book_item_id=book.id,
        completed_on="2026-08-01",
    )
    second = service.add_history(
        book_item_id=book.id,
        completed_on="2026-09-01",
    )

    assert service.get_histories_for_book(book.id) == [second, first]


def test_update_history_normalizes_values_and_sets_timestamp(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """更新値を正規化して更新日時を設定する。"""
    book_repository, create_service = components
    book = add_book(book_repository)
    assert book.id is not None
    registered = create_service.add_history(
        book_item_id=book.id,
        notes="登録時",
    )
    update_service = ReadingHistoryService(
        create_service._repository,
        book_repository,
        now_provider=lambda: UPDATED_NOW,
    )
    update_target = replace(
        registered,
        started_on=" 2026-08-01 ",
        completed_on=" 2026-08-31 ",
        notes="  更新後  ",
    )

    assert update_service.update_history(update_target) is True
    assert registered.id is not None
    updated = update_service.get_history(registered.id)
    assert updated is not None
    assert updated.started_on == "2026-08-01"
    assert updated.completed_on == "2026-08-31"
    assert updated.notes == "更新後"
    assert updated.updated_at == "2026-09-08 11:45:30"


def test_update_history_preserves_identity_and_created_at(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """更新時にID、書籍IDおよび登録日時を維持する。"""
    book_repository, service = components
    first_book = add_book(book_repository, title="一冊目")
    second_book = add_book(book_repository, title="二冊目")
    assert first_book.id is not None
    assert second_book.id is not None
    registered = service.add_history(
        book_item_id=first_book.id,
        notes="登録時",
    )
    target = replace(
        registered,
        id=registered.id,
        book_item_id=second_book.id,
        created_at="2099-01-01 00:00:00",
        notes="更新後",
    )

    assert service.update_history(target) is True
    assert registered.id is not None
    updated = service.get_history(registered.id)
    assert updated is not None
    assert updated.id == registered.id
    assert updated.book_item_id == first_book.id
    assert updated.created_at == registered.created_at


def test_update_history_returns_false_before_validation_when_missing(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """存在しない履歴では入力値を検証せずFalseを返す。"""
    _, service = components
    target = ReadingHistory(
        id=999,
        book_item_id=999,
        started_on="invalid",
    )

    assert service.update_history(target) is False


def test_update_history_requires_id(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """IDがない履歴を更新できない。"""
    _, service = components

    with pytest.raises(
        ValueError,
        match="更新対象のReadingHistoryにはidが必要です。",
    ):
        service.update_history(
            ReadingHistory(book_item_id=1, notes="メモ")
        )


def test_update_history_rejects_empty_and_invalid_values(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """登録済み履歴の不正な更新値を拒否する。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None
    registered = service.add_history(
        book_item_id=book.id,
        notes="登録時",
    )

    with pytest.raises(ValueError):
        service.update_history(
            replace(registered, notes=" ")
        )
    with pytest.raises(ValueError):
        service.update_history(
            replace(
                registered,
                started_on="2026-09-08",
                completed_on="2026-09-07",
            )
        )

    assert registered.id is not None
    assert service.get_history(registered.id) == registered


def test_delete_history_returns_repository_result(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """履歴を削除し、存在しないIDではFalseを返す。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None
    registered = service.add_history(
        book_item_id=book.id,
        notes="削除対象",
    )
    assert registered.id is not None

    assert service.delete_history(registered.id) is True
    assert service.delete_history(registered.id) is False


def test_history_operations_do_not_change_book_reading_fields(
    components: tuple[BookRepository, ReadingHistoryService],
) -> None:
    """履歴操作で既存の読書状態と読了年月を変更しない。"""
    book_repository, service = components
    book = add_book(book_repository)
    assert book.id is not None
    registered = service.add_history(
        book_item_id=book.id,
        completed_on="2026-09-07",
    )
    assert service.update_history(
        replace(registered, notes="更新")
    ) is True
    assert registered.id is not None
    assert service.delete_history(registered.id) is True

    restored_book = book_repository.get_by_id(book.id)
    assert restored_book is not None
    assert restored_book.reading_status == "completed"
    assert restored_book.completion_month == "2026-08"


def create_statistics_service(
    repository: Mock,
) -> ReadingHistoryService:
    """集計テスト用のServiceを生成する。"""
    return ReadingHistoryService(
        repository,
        Mock(spec=BookRepository),
    )


def test_get_statistics_summary_returns_repository_result() -> None:
    """Repositoryの全体集計を返す。"""
    repository = Mock(spec=ReadingHistoryRepository)
    summary = ReadingStatisticsSummary(12, 8, 10, 3)
    repository.get_statistics_summary.return_value = summary
    service = create_statistics_service(repository)

    assert service.get_statistics_summary() == summary
    repository.get_statistics_summary.assert_called_once_with()


@pytest.mark.parametrize(
    "summary",
    [
        ReadingStatisticsSummary(-1, 0, 0, 0),
        ReadingStatisticsSummary(0, -1, 0, 0),
        ReadingStatisticsSummary(0, 0, -1, 0),
        ReadingStatisticsSummary(0, 0, 0, -1),
        ReadingStatisticsSummary(True, 0, 0, 0),
    ],
)
def test_get_statistics_summary_rejects_invalid_counts(
    summary: ReadingStatisticsSummary,
) -> None:
    """負数またはboolを含む全体集計を拒否する。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_statistics_summary.return_value = summary
    service = create_statistics_service(repository)

    with pytest.raises(
        ValueError,
        match="読書履歴の集計結果が不正です。",
    ):
        service.get_statistics_summary()


def test_get_completed_years_returns_repository_result() -> None:
    """Repositoryの対象年一覧を返す。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_completed_years.return_value = [2026, 2025, 2024]
    service = create_statistics_service(repository)

    assert service.get_completed_years() == [2026, 2025, 2024]
    repository.get_completed_years.assert_called_once_with()


def test_get_completed_years_accepts_empty_list() -> None:
    """読了記録がない場合は空の対象年一覧を返す。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_completed_years.return_value = []
    service = create_statistics_service(repository)

    assert service.get_completed_years() == []


@pytest.mark.parametrize("year", [0, 10000, "2026", True, None])
def test_get_completed_years_rejects_invalid_repository_years(
    year: object,
) -> None:
    """Repositoryが返した不正な対象年を拒否する。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_completed_years.return_value = [year]
    service = create_statistics_service(repository)

    with pytest.raises(
        ValueError,
        match="集計対象年は1から9999までの整数",
    ):
        service.get_completed_years()


def test_get_monthly_reading_counts_fills_all_months() -> None:
    """記録がない月を0件で補完して12か月分を返す。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_monthly_completed_counts.return_value = {
        1: 2,
        3: 1,
        12: 4,
    }
    service = create_statistics_service(repository)

    result = service.get_monthly_reading_counts(2026)

    assert result == [
        MonthlyReadingCount(
            year=2026,
            month=month,
            completed_count={1: 2, 3: 1, 12: 4}.get(
                month,
                0,
            ),
        )
        for month in range(1, 13)
    ]
    repository.get_monthly_completed_counts.assert_called_once_with(
        2026
    )


def test_get_monthly_reading_counts_returns_zero_for_missing_year(
) -> None:
    """記録がない年は12か月すべて0件で返す。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_monthly_completed_counts.return_value = {}
    service = create_statistics_service(repository)

    result = service.get_monthly_reading_counts(2026)

    assert len(result) == 12
    assert [item.month for item in result] == list(range(1, 13))
    assert all(item.completed_count == 0 for item in result)


@pytest.mark.parametrize("year", [1, 9999])
def test_get_monthly_reading_counts_accepts_year_limits(
    year: int,
) -> None:
    """1年と9999年を集計対象として許可する。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_monthly_completed_counts.return_value = {}
    service = create_statistics_service(repository)

    result = service.get_monthly_reading_counts(year)

    assert len(result) == 12
    assert all(item.year == year for item in result)


@pytest.mark.parametrize("year", [0, 10000, "2026", True, None])
def test_get_monthly_reading_counts_rejects_invalid_year(
    year: object,
) -> None:
    """範囲外の値と整数以外を集計対象年として拒否する。"""
    repository = Mock(spec=ReadingHistoryRepository)
    service = create_statistics_service(repository)

    with pytest.raises(
        ValueError,
        match="集計対象年は1から9999までの整数",
    ):
        service.get_monthly_reading_counts(year)  # type: ignore[arg-type]

    repository.get_monthly_completed_counts.assert_not_called()


@pytest.mark.parametrize(
    "monthly_counts",
    [
        {0: 1},
        {13: 1},
        {True: 1},
        {1: -1},
        {1: True},
    ],
)
def test_get_monthly_reading_counts_rejects_invalid_results(
    monthly_counts: dict[int, int],
) -> None:
    """不正な月または件数を含むRepository結果を拒否する。"""
    repository = Mock(spec=ReadingHistoryRepository)
    repository.get_monthly_completed_counts.return_value = monthly_counts
    service = create_statistics_service(repository)

    with pytest.raises(
        ValueError,
        match="月別読了数の集計結果が不正です。",
    ):
        service.get_monthly_reading_counts(2026)
