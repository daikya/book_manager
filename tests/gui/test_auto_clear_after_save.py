"""登録・更新成功後の入力フォーム自動クリアに関するGUIロジックのテスト。"""

from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem


def create_application() -> BookManagerApplication:
    """テスト用のBookManagerApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._root = Mock()
    application._service = Mock()
    application._selected_book_id = None
    application._title_entry = Mock()
    application._is_favorite_var = Mock()
    application._load_all_books = Mock()
    application._refresh_tag_options = Mock()
    application._clear_form = Mock()
    application._confirm_duplicate_candidates = Mock(
        return_value=True,
    )
    application._get_form_values = Mock(
        return_value={
            "title": "テスト書籍",
            "isbn": None,
            "reference_isbn": None,
            "magazine_code": None,
            "author": None,
            "publisher": None,
            "publication_format": None,
            "description": None,
            "cover_image_url": None,
            "cover_image_path": None,
            "completion_month": None,
            "reading_status": None,
            "is_favorite": False,
            "rating": None,
            "tags": (),
            "notes": None,
        },
    )

    return application


def test_on_add_clears_form_after_success() -> None:
    """新規登録成功後にフォームを初期化する。"""
    application = create_application()

    application._service.add_book.return_value = BookItem(
        id=1,
        title="テスト書籍",
    )

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo",
    ):
        application._on_add()

    application._load_all_books.assert_called_once_with()
    application._clear_form.assert_called_once_with()
    application._title_entry.focus_set.assert_called_once_with()


def test_on_add_does_not_clear_form_when_add_fails() -> None:
    """新規登録失敗時はフォームを初期化しない。"""
    application = create_application()

    application._service.add_book.side_effect = ValueError(
        "登録エラー",
    )

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror",
    ):
        application._on_add()

    application._clear_form.assert_not_called()


def test_on_add_does_not_clear_form_when_duplicate_confirmation_is_cancelled() -> None:
    """重複候補確認で中止した場合はフォームを初期化しない。"""
    application = create_application()

    application._confirm_duplicate_candidates.return_value = False

    application._on_add()

    application._service.add_book.assert_not_called()
    application._clear_form.assert_not_called()


def test_on_update_clears_form_after_success() -> None:
    """更新成功後にフォームを初期化する。"""
    application = create_application()

    application._selected_book_id = 1

    application._create_book_item_from_form = Mock(
        return_value=BookItem(
            id=1,
            title="テスト書籍",
        ),
    )

    application._service.update_book.return_value = True

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ),
    ):
        application._on_update()

    application._load_all_books.assert_called_once_with()
    application._clear_form.assert_called_once_with()
    application._title_entry.focus_set.assert_called_once_with()


def test_on_update_does_not_clear_form_when_update_fails() -> None:
    """更新失敗時はフォームを初期化しない。"""
    application = create_application()

    application._selected_book_id = 1

    application._create_book_item_from_form = Mock(
        return_value=BookItem(
            id=1,
            title="テスト書籍",
        ),
    )

    application._service.update_book.side_effect = ValueError(
        "更新エラー",
    )

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror",
        ),
    ):
        application._on_update()

    application._clear_form.assert_not_called()


def test_on_update_does_not_clear_form_when_confirmation_is_cancelled() -> None:
    """更新確認でキャンセルした場合はフォームを初期化しない。"""
    application = create_application()

    application._selected_book_id = 1

    with patch(
        "book_manager.gui.book_manager_application.messagebox.askyesno",
        return_value=False,
    ):
        application._on_update()

    application._service.update_book.assert_not_called()
    application._clear_form.assert_not_called()
