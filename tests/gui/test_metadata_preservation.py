"""GUI依存を起動せず、実ソースの反映メソッドの状態変化を検証する。"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from book_manager.models.fetched_book_data import FetchedBookData


class Variable:
    def __init__(self, value):
        self.value = value

    def set(self, value):
        self.value = value


class Text:
    def __init__(self, value):
        self.value = value

    def get(self, *args):
        return self.value


def method(name):
    # Tkの画面生成や無関係なアプリ依存を使わず、実メソッドを実行する。
    import book_manager.gui.book_candidate_search_dialog as module
    source = Path(module.__file__).with_name("book_manager_application.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    application = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                       and n.name == "BookManagerApplication")
    function = next(n for n in application.body if isinstance(n, ast.FunctionDef)
                    and n.name == name)
    namespace = {
        "traceback": SimpleNamespace(print_exc=lambda: None),
        "messagebox": SimpleNamespace(showwarning=lambda *a, **k: None),
    }
    exec("from __future__ import annotations\n" + ast.unparse(function), namespace)
    return namespace[name]


def form():
    app = SimpleNamespace(
        _isbn_var=Variable("old-isbn"), _reference_isbn_var=Variable("old-ref"),
        _title_var=Variable("元書籍"), _author_var=Variable("元著者"),
        _publisher_var=Variable("元出版社"), _publication_format_var=Variable("Audible"),
        _description_text=Text("元の内容紹介\n改行"),
        _current_cover_image_url="old-url", _current_cover_image_path="old-path",
        _root=None,
    )
    app._replace_text = lambda text, value: setattr(text, "value", value)
    return app


@pytest.mark.parametrize("value", [None, "", "  "])
def test_missing_description_preserves_existing(value):
    app = form()
    method("_apply_fetched_book_data")(app, FetchedBookData(isbn="new", description=value))
    assert app._description_text.value == "元の内容紹介\n改行"


def test_reference_preserves_original_fields_and_description():
    app = form()
    data = FetchedBookData(
        isbn="ref", title="紙の版", author="別表記", publisher="別出版社",
        publication_format="文庫", description="新しい紹介",
    )
    method("_apply_fetched_book_data")(app, data, use_reference_isbn=True)
    assert app._reference_isbn_var.value == "ref"
    assert app._isbn_var.value == "old-isbn"
    assert app._title_var.value == "元書籍"
    assert app._author_var.value == "元著者"
    assert app._publisher_var.value == "元出版社"
    assert app._publication_format_var.value == "Audible"
    assert app._description_text.value == "元の内容紹介\n改行"


def test_reference_fills_empty_description():
    app = form()
    app._description_text.value = ""
    method("_apply_fetched_book_data")(
        app, FetchedBookData(isbn="ref", description="紹介\n改行"),
        use_reference_isbn=True,
    )
    assert app._description_text.value == "紹介\n改行"


@pytest.mark.parametrize("url", [None, "", " "])
def test_missing_cover_preserves_state_without_fetch(url):
    app = form()
    method("_apply_fetched_cover")(app, url)
    assert app._current_cover_image_url == "old-url"
    assert app._current_cover_image_path == "old-path"


@pytest.mark.parametrize("stage", ["fetch", "store", "display"])
def test_cover_failure_preserves_state(stage):
    app = form()
    def fail():
        raise RuntimeError("失敗")
    app._service = SimpleNamespace(
        fetch_cover_image=lambda url: fail() if stage == "fetch" else Path("new"),
        create_stored_cover_image_path=lambda path: fail() if stage == "store" else "new-path",
    )
    app._display_cover_image = lambda path: fail() if stage == "display" else None
    method("_apply_fetched_cover")(app, "new-url")
    assert app._current_cover_image_url == "old-url"
    assert app._current_cover_image_path == "old-path"


def test_successful_cover_updates_url_and_path_together():
    app = form()
    displayed = []
    app._service = SimpleNamespace(
        fetch_cover_image=lambda url: Path("new"),
        create_stored_cover_image_path=lambda path: "new-path",
    )
    app._display_cover_image = displayed.append
    method("_apply_fetched_cover")(app, "new-url")
    assert displayed == ["new"]
    assert app._current_cover_image_url == "new-url"
    assert app._current_cover_image_path == "new-path"



def test_explicit_selection_only_updates_selected_field():
    app = form()
    data = FetchedBookData(isbn="new", title="新書籍", author="新著者", description="新紹介")
    method("_apply_fetched_book_data")(app, data, selected_fields=frozenset({"author"}))
    assert app._author_var.value == "新著者"
    assert app._title_var.value == "元書籍"
    assert app._description_text.value == "元の内容紹介\n改行"


def test_explicit_reference_selection_can_replace_description():
    app = form()
    data = FetchedBookData(isbn="ref", title="紙の版", description="選択した紹介")
    method("_apply_fetched_book_data")(
        app, data, use_reference_isbn=True,
        selected_fields=frozenset({"description", "title"}),
    )
    assert app._description_text.value == "選択した紹介"
    assert app._title_var.value == "元書籍"
    assert app._isbn_var.value == "old-isbn"


def test_isbnless_candidate_preserves_existing_identifiers():
    app = form()
    method("_apply_fetched_book_data")(
        app, FetchedBookData(isbn="", title="新しい本"), selected_fields=frozenset({"title"}),
    )
    assert app._isbn_var.value == "old-isbn"
    assert app._reference_isbn_var.value == "old-ref"
    assert app._title_var.value == "新しい本"
