"""参照ISBNのGUI入力・表示・保存の検証。"""
from unittest.mock import Mock

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
