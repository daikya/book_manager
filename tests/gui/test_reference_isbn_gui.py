"""参照ISBNのGUI入力・表示・保存の検証。"""
from unittest.mock import Mock, patch
from types import SimpleNamespace

from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.book_item import BookItem


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def create_application():
    application = BookManagerApplication.__new__(BookManagerApplication)
    for name in (
        "title", "isbn", "reference_isbn", "magazine_code", "author",
        "publisher", "publication_format", "completion_month", "reading_status",
        "rating", "tags", "edit_status",
    ):
        setattr(application, f"_{name}_var", Value())
    application._is_favorite_var = Value(False)
    application._reading_status_var.set("未設定")
    application._rating_var.set("未評価")
    application._description_text = Mock()
    application._description_text.get.return_value = "内容紹介\n"
    application._notes_text = Mock()
    application._notes_text.get.return_value = "メモ\n"
    application._book_tree = Mock()
    application._book_tree.selection.return_value = ()
    application._current_cover_image_url = None
    application._current_cover_image_path = None
    application._set_edit_buttons_enabled = Mock()
    application._clear_cover_state = Mock()
    application._display_selected_cover_image = Mock()
    application._selected_book_id = None
    return application


def test_form_creates_book_with_separate_reference_isbn():
    application = create_application()
    application._title_var.set("音声版")
    application._reference_isbn_var.set("9784101010014")
    application._tags_var.set("音声|既読")
    book = application._create_book_item_from_form(book_id=10)
    assert book.id == 10
    assert book.title == "音声版"
    assert book.isbn == ""
    assert book.reference_isbn == "9784101010014"
    assert book.description == "内容紹介"
    assert book.notes == "メモ"
    assert book.tags == ("音声", "既読")


def test_display_and_edit_preserve_reference_isbn():
    application = create_application()
    book = BookItem(id=10, title="音声版", reference_isbn="9784101010014")
    application._display_book_in_form(book)
    assert application._reference_isbn_var.get() == book.reference_isbn
    application._notes_text.get.return_value = "変更したメモ\n"
    updated = application._create_book_item_from_form(book_id=10)
    assert updated.reference_isbn == book.reference_isbn
    assert updated.notes == "変更したメモ"
    assert updated.isbn == ""


def test_selecting_book_without_reference_clears_previous_value():
    application = create_application()
    application._reference_isbn_var.set("9784101010014")
    application._display_book_in_form(BookItem(id=11, title="通常の本"))
    assert application._reference_isbn_var.get() == ""


def test_clear_form_clears_reference_isbn():
    application = create_application()
    application._reference_isbn_var.set("9784101010014")
    application._clear_form()
    assert application._reference_isbn_var.get() == ""
    assert application._selected_book_id is None


def test_reference_isbn_can_be_removed_from_edited_book():
    application = create_application()
    application._display_book_in_form(
        BookItem(id=10, title="音声版", reference_isbn="9784101010014"),
    )
    application._reference_isbn_var.set("")
    assert application._create_book_item_from_form(book_id=10).reference_isbn == ""


def create_metadata_application():
    application = create_application()
    application._root = Mock()
    application._isbn_entry = Mock()
    application._fetch_metadata_button = Mock()
    application._service = Mock()
    application._confirm_metadata_overwrite = Mock(return_value=True)
    application._display_cover_image = Mock()
    application._replace_text = Mock()
    application._service.fetch_book_metadata.return_value = SimpleNamespace(
        isbn="9784101010014", title="取得書籍名", author="取得著者",
        publisher="取得出版社", publication_format="文庫",
        description="取得した内容紹介", cover_image_url="https://example.com/cover.jpg",
    )
    application._service.fetch_cover_image.return_value = "cover.jpg"
    application._service.create_stored_cover_image_path.return_value = "covers/cover.jpg"
    return application


def test_reference_fetch_applies_same_metadata_without_setting_regular_isbn():
    application = create_metadata_application()
    application._reference_isbn_var.set("4-10-101001-3")
    application._title_var.set("元の書籍名")
    application._publication_format_var.set("音声版")
    application._completion_month_var.set("2026-09")
    application._tags_var.set("音声")
    with patch("book_manager.gui.book_manager_application.messagebox.showinfo"):
        application._on_fetch_book_metadata()
    application._service.fetch_book_metadata.assert_called_once_with("4-10-101001-3")
    application._confirm_metadata_overwrite.assert_called_once_with()
    assert application._isbn_var.get() == ""
    assert application._reference_isbn_var.get() == "9784101010014"
    assert application._title_var.get() == "取得書籍名"
    assert application._author_var.get() == "取得著者"
    assert application._publisher_var.get() == "取得出版社"
    assert application._publication_format_var.get() == "文庫"
    application._replace_text.assert_called_once_with(application._description_text, "取得した内容紹介")
    assert application._current_cover_image_url == "https://example.com/cover.jpg"
    assert application._current_cover_image_path == "covers/cover.jpg"
    assert application._completion_month_var.get() == "2026-09"
    assert application._tags_var.get() == "音声"
    application._service.add_book.assert_not_called()
    application._service.update_book.assert_not_called()
    application._fetch_metadata_button.configure.assert_called_with(state="normal")


def test_reference_fetch_cancel_preserves_original_form_and_cover():
    application = create_metadata_application()
    application._reference_isbn_var.set("9784101010014")
    application._title_var.set("元の書籍名")
    application._current_cover_image_url = "https://example.com/original.jpg"
    application._current_cover_image_path = "original.jpg"
    application._confirm_metadata_overwrite.return_value = False
    application._on_fetch_book_metadata()
    assert application._title_var.get() == "元の書籍名"
    assert application._isbn_var.get() == ""
    assert application._current_cover_image_url == "https://example.com/original.jpg"
    assert application._current_cover_image_path == "original.jpg"
    application._replace_text.assert_not_called()
    application._service.fetch_cover_image.assert_not_called()
    application._fetch_metadata_button.configure.assert_called_with(state="normal")


def test_regular_isbn_takes_priority_over_reference():
    application = create_metadata_application()
    application._isbn_var.set("9784101010014")
    application._reference_isbn_var.set("9784065363706")
    with patch("book_manager.gui.book_manager_application.messagebox.showinfo"):
        application._on_fetch_book_metadata()
    application._service.fetch_book_metadata.assert_called_once_with("9784101010014")
    assert application._reference_isbn_var.get() == "9784065363706"


def test_reference_fetch_without_cover_clears_cover_as_regular_fetch_does():
    application = create_metadata_application()
    application._reference_isbn_var.set("9784101010014")
    application._service.fetch_book_metadata.return_value.cover_image_url = None
    with patch("book_manager.gui.book_manager_application.messagebox.showinfo"):
        application._on_fetch_book_metadata()
    application._clear_cover_state.assert_called_once_with()
    application._service.fetch_cover_image.assert_not_called()


def test_fetch_without_both_isbns_does_not_call_service():
    application = create_metadata_application()
    with patch("book_manager.gui.book_manager_application.messagebox.showwarning") as warning:
        application._on_fetch_book_metadata()
    warning.assert_called_once()
    application._service.fetch_book_metadata.assert_not_called()
