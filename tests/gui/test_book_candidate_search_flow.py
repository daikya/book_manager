"""画面を生成せず、検索開始・応答・ISBN反映の連携を検証する。"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from book_manager.gui.book_candidate_search_dialog import BookCandidateSearchDialog
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.book_search_candidate import BookSearchCandidate
from book_manager.services.book_service import BookService


def variable(value=""):
    return Mock(get=Mock(return_value=value))


def dialog():
    result = BookCandidateSearchDialog.__new__(BookCandidateSearchDialog)
    result.window = Mock()
    result._next_button = Mock()
    result._broaden_button = Mock()
    result._only_matches = Mock(get=Mock(return_value=False))
    result._pending = False
    result._closed = False
    result._title = variable("")
    result._author = variable("")
    result._publisher = variable("集英社")
    result._search = Mock()
    result._task = Mock(start=Mock(return_value=True))
    result._entries = [Mock(), Mock(), Mock()]
    result._tree = Mock(get_children=Mock(return_value=()))
    result._destination = variable("normal")
    result._isbn = variable()
    result._isbn_box = Mock()
    result._details = Mock()
    result._apply_button = Mock()
    result._search_button = Mock()
    result._status = Mock()
    return result


def test_publisher_only_start_captures_conditions_and_disables_inputs():
    form = dialog()
    form._start()
    form._task.start.assert_called_once_with(form._search, title="", author="", publisher="集英社")
    assert form._conditions == dict(title="", author="", publisher="集英社")
    for entry in form._entries:
        entry.configure.assert_called_once_with(state="disabled")


def test_result_shows_match_hint_and_restores_inputs_without_selecting():
    form = dialog()
    form._start()
    form._task.poll.return_value = ([BookSearchCandidate(source="Google Books", title="本", publisher="株式会社集英社")], None)
    form._poll()
    assert form._tree.insert.call_args.kwargs["values"][-1] == "出版社: 一致"
    form._tree.selection_set.assert_not_called()
    for entry in form._entries:
        assert entry.configure.call_args.kwargs == {"state": "normal"}


def test_book_service_forwards_publisher_without_repository():
    service = BookService.__new__(BookService)
    service._book_metadata_service = Mock()
    service.search_book_candidates(publisher="集英社")
    service._book_metadata_service.search_candidates.assert_called_once_with(
        title="", author="", publisher="集英社", max_results=20,
    )


def application():
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._root = Mock(winfo_exists=Mock(return_value=True))
    app._metadata_form_snapshot = Mock(return_value=(1, "unchanged"))
    app._selected_book_id = 1
    app._title_var = variable("本")
    app._author_var = variable("著者")
    app._publisher_var = variable("出版社")
    app._isbn_var = variable("")
    app._reference_isbn_var = variable("")
    app._candidate_search_task = SimpleNamespace(busy=False)
    app._candidate_search_button = Mock()
    app._service = Mock()
    app._edit_status_var = Mock()
    return app


def test_main_dialog_prefills_publisher_and_cancel_keeps_isbn():
    app = application()
    with patch("book_manager.gui.book_manager_application.BookCandidateSearchDialog") as factory, patch("book_manager.gui.book_manager_application.center_window_on_parent"):
        factory.return_value.show.return_value = None
        app._on_search_book_candidates()
    assert factory.call_args.kwargs["publisher"] == "出版社"
    app._isbn_var.set.assert_not_called()
    app._reference_isbn_var.set.assert_not_called()


def test_publisher_change_discards_selected_isbn():
    app = application()
    def show():
        app._publisher_var.get.return_value = "別の出版社"
        return "9784087754537", "reference"
    with patch("book_manager.gui.book_manager_application.BookCandidateSearchDialog") as factory, patch("book_manager.gui.book_manager_application.center_window_on_parent"), patch("book_manager.gui.book_manager_application.messagebox.showwarning") as warning:
        factory.return_value.show.side_effect = show
        app._on_search_book_candidates()
    warning.assert_called_once()
    app._reference_isbn_var.set.assert_not_called()


def test_unregistered_form_can_search_and_apply_selected_metadata():
    from book_manager.models.fetched_book_data import FetchedBookData
    app = application()
    app._selected_book_id = None
    app._choose_metadata_fields = Mock(return_value=frozenset({"title", "description", "cover_image_url"}))
    app._apply_fetched_book_data = Mock()
    app._apply_fetched_cover = Mock()
    fetched = FetchedBookData(isbn="9784087754537", title="候補", description="紹介", cover_image_url="https://example.com/cover")
    with patch("book_manager.gui.book_manager_application.BookCandidateSearchDialog") as factory, patch("book_manager.gui.book_manager_application.center_window_on_parent"):
        factory.return_value.show.return_value = (fetched, "normal")
        app._on_search_book_candidates()
    app._choose_metadata_fields.assert_called_once_with(fetched, use_reference_isbn=False)
    app._apply_fetched_book_data.assert_called_once()
    app._apply_fetched_cover.assert_called_once_with(fetched.cover_image_url)
    app._service.fetch_book_metadata.assert_not_called()


def test_candidate_comparison_cancel_keeps_form():
    from book_manager.models.fetched_book_data import FetchedBookData
    app = application()
    app._choose_metadata_fields = Mock(return_value=None)
    app._apply_fetched_book_data = Mock()
    with patch("book_manager.gui.book_manager_application.BookCandidateSearchDialog") as factory, patch("book_manager.gui.book_manager_application.center_window_on_parent"):
        factory.return_value.show.return_value = (FetchedBookData(isbn=""), "normal")
        app._on_search_book_candidates()
    app._apply_fetched_book_data.assert_not_called()


def test_additional_search_merges_without_dropping_existing_or_same_isbn_editions():
    form = dialog()
    form._start()
    first = BookSearchCandidate(source="Google Books", source_id="a", title="本", publisher="集英社")
    second = BookSearchCandidate(source="Google Books", source_id="b", title="別版", publisher="集英社")
    form._task.poll.return_value = ([first], None)
    form._poll()
    form._operation = "page"
    form._pending = True
    form._task.poll.return_value = ([first, second], None)
    form._poll()
    assert form._all_candidates == [first, second]


def test_explicit_broadening_queries_fields_separately():
    form = dialog()
    form._conditions = dict(title="本", author="著者", publisher="集英社")
    form._title.get.return_value = "本"
    form._author.get.return_value = "著者"
    form._task.start_operation = Mock(return_value=True)
    form._search.return_value = []
    form._broaden()
    operation = form._task.start_operation.call_args.args[0]
    assert operation() == []
    assert form._search.call_count == 3
    assert form._search.call_args_list[0].kwargs == {"title": "本", "max_results": 20}


def test_isbnless_candidate_can_request_detail():
    form = dialog()
    form._start()
    form._pending = False
    candidate = BookSearchCandidate(source="Google Books", source_id="id", title="ISBNなし")
    form._candidates = [candidate]
    form._tree.selection.return_value = ("0",)
    form._fetch = Mock()
    form._task.start_operation = Mock(return_value=True)
    form._apply()
    operation = form._task.start_operation.call_args.args[0]
    operation()
    form._fetch.assert_called_once_with(candidate, isbn="")


def test_failed_additional_request_keeps_prior_candidates_and_restores_page():
    from book_manager.metadata.exceptions import BookMetadataResponseError
    form = dialog()
    form._start()
    form._all_candidates = [BookSearchCandidate(source="Google Books", title="以前の候補")]
    form._candidates = []
    form._tree.selection.return_value = ()
    form._operation = "page"
    form._start_index = 20
    form._task.poll.return_value = (None, BookMetadataResponseError("failed"))
    form._poll()
    assert form._all_candidates[0].title == "以前の候補"
    assert form._start_index == 0


def test_changed_form_during_comparison_does_not_apply():
    from book_manager.models.fetched_book_data import FetchedBookData
    app = application()
    app._metadata_form_snapshot.side_effect = [(1, "before"), (1, "after")]
    app._choose_metadata_fields = Mock(return_value=frozenset({"description"}))
    app._apply_fetched_book_data = Mock()
    with patch("book_manager.gui.book_manager_application.BookCandidateSearchDialog") as factory, patch("book_manager.gui.book_manager_application.center_window_on_parent"), patch("book_manager.gui.book_manager_application.messagebox.showwarning"):
        factory.return_value.show.return_value = (FetchedBookData(isbn="", description="new"), "normal")
        app._on_search_book_candidates()
    app._apply_fetched_book_data.assert_not_called()
