"""Tests for the ReadingHistoryRepository."""

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    ReadingStatisticsSummary,
)
from book_manager.repositories.book_repository import BookRepository
from book_manager.repositories.reading_history_repository import (
    ReadingHistoryRepository,
)


@pytest.fixture
def repositories(
    tmp_path: Path,
) -> tuple[BookRepository, ReadingHistoryRepository]:
    """初期化済みDBを共有するRepositoryを返す。"""
    database_path = tmp_path / "test_book_manager.db"
    initialize_database(database_path)

    return (
        BookRepository(database_path),
        ReadingHistoryRepository(database_path),
    )


def add_book(
    book_repository: BookRepository,
    *,
    title: str = "吾輩は猫である",
) -> BookItem:
    """テスト用書籍を登録する。"""
    return book_repository.add(
        BookItem(
            title=title,
            created_at="2026-09-07 10:00:00",
            updated_at="2026-09-07 10:00:00",
        )
    )


def create_reading_history(
    *,
    book_item_id: int,
    started_on: str | None = "2026-09-01",
    completed_on: str | None = "2026-09-07",
    notes: str | None = "読了した。",
    created_at: str = "2026-09-07 10:00:00",
    updated_at: str = "2026-09-07 10:00:00",
) -> ReadingHistory:
    """Repositoryテスト用の読書履歴を生成する。"""
    return ReadingHistory(
        book_item_id=book_item_id,
        started_on=started_on,
        completed_on=completed_on,
        notes=notes,
        created_at=created_at,
        updated_at=updated_at,
    )


def test_repository_accepts_path(
    tmp_path: Path,
) -> None:
    """Pathを使用してRepositoryを生成できる。"""
    database_path = tmp_path / "test.db"

    repository = ReadingHistoryRepository(database_path)

    assert repository._database_path == database_path


def test_repository_accepts_string_path(
    tmp_path: Path,
) -> None:
    """文字列パスを使用してRepositoryを生成できる。"""
    database_path = tmp_path / "test.db"

    repository = ReadingHistoryRepository(str(database_path))

    assert repository._database_path == database_path


def test_add_registers_reading_history(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読書履歴を登録して自動採番IDを返す。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None

    registered = repository.add(
        create_reading_history(book_item_id=book.id)
    )

    assert registered.id is not None
    assert registered.book_item_id == book.id
    assert repository.get_by_id(registered.id) == registered


def test_add_does_not_modify_input_model(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """登録時に入力モデルを変更しない。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    history = create_reading_history(book_item_id=book.id)

    registered = repository.add(history)

    assert history.id is None
    assert registered is not history


def test_add_stores_none_optional_fields(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """未設定の日付をNULLとして登録できる。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None

    registered = repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on=None,
            completed_on=None,
            notes="日付を記録していない読書。",
        )
    )

    assert registered.id is not None
    restored = repository.get_by_id(registered.id)
    assert restored is not None
    assert restored.started_on is None
    assert restored.completed_on is None


def test_add_rejects_missing_book(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """存在しない書籍の履歴を登録できない。"""
    _, repository = repositories

    with pytest.raises(sqlite3.IntegrityError):
        repository.add(
            create_reading_history(book_item_id=999)
        )


def test_get_by_id_returns_none_for_missing_id(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """存在しないIDではNoneを返す。"""
    _, repository = repositories

    assert repository.get_by_id(999) is None


def test_get_by_book_id_returns_only_target_book_histories(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """指定書籍の複数履歴だけを取得する。"""
    book_repository, repository = repositories
    first_book = add_book(book_repository, title="一冊目")
    second_book = add_book(book_repository, title="二冊目")
    assert first_book.id is not None
    assert second_book.id is not None
    first = repository.add(
        create_reading_history(
            book_item_id=first_book.id,
            started_on="2026-07-01",
            completed_on="2026-08-01",
        )
    )
    second = repository.add(
        create_reading_history(
            book_item_id=first_book.id,
            completed_on="2026-09-01",
        )
    )
    repository.add(
        create_reading_history(book_item_id=second_book.id)
    )

    histories = repository.get_by_book_id(first_book.id)

    assert histories == [second, first]


def test_get_by_book_id_uses_started_on_when_not_completed(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読了日がない場合は開始日で降順にする。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    older = repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on="2026-07-01",
            completed_on=None,
        )
    )
    newer = repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on="2026-08-01",
            completed_on=None,
        )
    )

    assert repository.get_by_book_id(book.id) == [newer, older]


def test_get_by_book_id_uses_created_at_when_dates_are_none(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """日付がない場合は登録日で降順にする。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    older = repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on=None,
            completed_on=None,
            notes="古いメモ",
            created_at="2026-07-01 10:00:00",
        )
    )
    newer = repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on=None,
            completed_on=None,
            notes="新しいメモ",
            created_at="2026-08-01 10:00:00",
        )
    )

    assert repository.get_by_book_id(book.id) == [newer, older]


def test_get_by_book_id_uses_descending_id_for_same_date(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """基準日が同じ場合はIDの降順にする。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    first = repository.add(
        create_reading_history(book_item_id=book.id)
    )
    second = repository.add(
        create_reading_history(book_item_id=book.id)
    )

    assert repository.get_by_book_id(book.id) == [second, first]


def test_get_by_book_id_returns_empty_list_for_missing_book(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """履歴がない書籍IDでは空リストを返す。"""
    _, repository = repositories

    assert repository.get_by_book_id(999) == []


def test_update_changes_editable_fields(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読書履歴の編集可能項目を更新する。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    registered = repository.add(
        create_reading_history(book_item_id=book.id)
    )
    updated = replace(
        registered,
        started_on="2026-08-01",
        completed_on="2026-08-31",
        notes="更新後のメモ",
        updated_at="2026-09-08 11:00:00",
    )

    result = repository.update(updated)

    assert result is True
    assert registered.id is not None
    assert repository.get_by_id(registered.id) == updated


def test_update_preserves_book_id_and_created_at(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """更新時に書籍IDと登録日時を変更しない。"""
    book_repository, repository = repositories
    first_book = add_book(book_repository, title="一冊目")
    second_book = add_book(book_repository, title="二冊目")
    assert first_book.id is not None
    assert second_book.id is not None
    registered = repository.add(
        create_reading_history(book_item_id=first_book.id)
    )
    changed = replace(
        registered,
        book_item_id=second_book.id,
        created_at="2099-01-01 00:00:00",
        notes="更新後",
    )

    assert repository.update(changed) is True
    assert registered.id is not None
    restored = repository.get_by_id(registered.id)
    assert restored is not None
    assert restored.book_item_id == first_book.id
    assert restored.created_at == registered.created_at
    assert restored.notes == "更新後"


def test_update_returns_false_for_missing_id(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """存在しない履歴IDの更新ではFalseを返す。"""
    _, repository = repositories
    history = replace(
        create_reading_history(book_item_id=1),
        id=999,
    )

    assert repository.update(history) is False


def test_update_raises_value_error_without_id(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """IDがない履歴を更新できない。"""
    _, repository = repositories

    with pytest.raises(ValueError):
        repository.update(
            create_reading_history(book_item_id=1)
        )


def test_delete_removes_existing_history(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """登録済みの読書履歴を削除する。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    registered = repository.add(
        create_reading_history(book_item_id=book.id)
    )
    assert registered.id is not None

    assert repository.delete(registered.id) is True
    assert repository.get_by_id(registered.id) is None


def test_delete_returns_false_for_missing_id(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """存在しない履歴IDの削除ではFalseを返す。"""
    _, repository = repositories

    assert repository.delete(999) is False


def test_deleting_book_cascades_reading_histories(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """書籍削除時に関連する読書履歴も削除する。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    registered = repository.add(
        create_reading_history(book_item_id=book.id)
    )
    assert registered.id is not None

    assert book_repository.delete(book.id) is True
    assert repository.get_by_id(registered.id) is None


def test_notes_are_bound_as_sql_parameter(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """SQL特殊文字を含むメモを安全に保存する。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    notes = "'); DROP TABLE reading_histories; -- %_"

    registered = repository.add(
        create_reading_history(
            book_item_id=book.id,
            notes=notes,
        )
    )

    assert registered.id is not None
    restored = repository.get_by_id(registered.id)
    assert restored is not None
    assert restored.notes == notes


def test_get_statistics_summary_returns_zero_without_histories(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読書履歴がない場合はすべて0件を返す。"""
    _, repository = repositories

    assert repository.get_statistics_summary() == (
        ReadingStatisticsSummary(
            total_history_count=0,
            books_with_history_count=0,
            completed_history_count=0,
            reread_book_count=0,
        )
    )


def test_get_statistics_summary_counts_each_definition(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """履歴・書籍・読了・再読を定義どおり集計する。"""
    book_repository, repository = repositories
    first_book = add_book(book_repository, title="再読した書籍")
    second_book = add_book(book_repository, title="一回読んだ書籍")
    third_book = add_book(book_repository, title="履歴のない書籍")
    assert first_book.id is not None
    assert second_book.id is not None
    assert third_book.id is not None

    repository.add(
        create_reading_history(
            book_item_id=first_book.id,
            started_on="2025-01-01",
            completed_on="2025-01-10",
        )
    )
    repository.add(
        create_reading_history(
            book_item_id=first_book.id,
            started_on="2026-02-01",
            completed_on=None,
            notes="再読中",
        )
    )
    repository.add(
        create_reading_history(
            book_item_id=second_book.id,
            started_on=None,
            completed_on=None,
            notes="メモだけの履歴",
        )
    )

    assert repository.get_statistics_summary() == (
        ReadingStatisticsSummary(
            total_history_count=3,
            books_with_history_count=2,
            completed_history_count=1,
            reread_book_count=1,
        )
    )


def test_get_statistics_summary_counts_multiple_reread_books(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """履歴が二件以上ある複数の書籍を再読書籍として数える。"""
    book_repository, repository = repositories

    for title in ("一冊目", "二冊目"):
        book = add_book(book_repository, title=title)
        assert book.id is not None
        repository.add(
            create_reading_history(book_item_id=book.id)
        )
        repository.add(
            create_reading_history(
                book_item_id=book.id,
                started_on="2026-10-01",
                completed_on="2026-10-10",
            )
        )

    summary = repository.get_statistics_summary()

    assert summary.total_history_count == 4
    assert summary.books_with_history_count == 2
    assert summary.completed_history_count == 4
    assert summary.reread_book_count == 2


def test_get_completed_years_returns_distinct_descending_years(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読了記録の年を重複なく新しい順で返す。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None

    for completed_on in (
        "2024-12-31",
        "2026-01-01",
        "2025-06-15",
        "2026-09-08",
    ):
        repository.add(
            create_reading_history(
                book_item_id=book.id,
                started_on=None,
                completed_on=completed_on,
            )
        )

    assert repository.get_completed_years() == [2026, 2025, 2024]


def test_get_completed_years_ignores_histories_without_completed_on(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """読了日がない履歴を対象年へ含めない。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    repository.add(
        create_reading_history(
            book_item_id=book.id,
            completed_on=None,
        )
    )

    assert repository.get_completed_years() == []


def test_get_monthly_completed_counts_groups_target_year(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """指定年の読了記録を月ごとに集計する。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None

    for completed_on in (
        "2026-01-01",
        "2026-01-31",
        "2026-03-15",
        "2025-01-10",
        "2027-12-20",
    ):
        repository.add(
            create_reading_history(
                book_item_id=book.id,
                started_on=None,
                completed_on=completed_on,
            )
        )

    assert repository.get_monthly_completed_counts(2026) == {
        1: 2,
        3: 1,
    }


def test_get_monthly_completed_counts_handles_year_boundaries(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """年初と年末の読了記録を対象年へ含める。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None

    for completed_on in ("2026-01-01", "2026-12-31"):
        repository.add(
            create_reading_history(
                book_item_id=book.id,
                started_on=None,
                completed_on=completed_on,
            )
        )

    assert repository.get_monthly_completed_counts(2026) == {
        1: 1,
        12: 1,
    }


def test_get_monthly_completed_counts_returns_empty_for_missing_year(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
) -> None:
    """指定年に読了記録がない場合は空の辞書を返す。"""
    _, repository = repositories

    assert repository.get_monthly_completed_counts(2026) == {}


@pytest.mark.parametrize("year", [1, 9999])
def test_get_monthly_completed_counts_supports_year_limits(
    repositories: tuple[BookRepository, ReadingHistoryRepository],
    year: int,
) -> None:
    """1年と9999年の読了記録を集計できる。"""
    book_repository, repository = repositories
    book = add_book(book_repository)
    assert book.id is not None
    repository.add(
        create_reading_history(
            book_item_id=book.id,
            started_on=None,
            completed_on=f"{year:04d}-01-01",
        )
    )

    assert repository.get_monthly_completed_counts(year) == {1: 1}
