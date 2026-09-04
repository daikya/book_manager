"""タグ管理ダイアログのGUIロジックを検証する。"""

from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem
from book_manager.models.tag import Tag


def create_application() -> BookManagerApplication:
    """タグ管理テスト用Applicationを生成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._service = Mock()
    application._selected_book_id = None
    application._refresh_tag_options = Mock()
    application._on_reload = Mock()
    application._display_book_in_form = Mock()

    return application


def create_tag_tree(
    *,
    tag_id: int = 1,
    tag_name: str = "小説",
) -> Mock:
    """選択済みタグを持つTreeviewのMockを生成する。"""
    tag_tree = Mock()
    tag_tree.selection.return_value = (str(tag_id),)
    tag_tree.item.return_value = (tag_name, 2)

    return tag_tree


def test_populate_tag_management_tree_displays_counts() -> None:
    """タグ名と使用冊数をタグ管理一覧へ表示する。"""
    application = create_application()
    tag_tree = Mock()
    tag_tree.get_children.return_value = ("old",)
    application._service.get_all_tags.return_value = [
        Tag(id=1, name="小説"),
        Tag(id=2, name="技術書"),
    ]
    application._service.count_books_by_tag.side_effect = [2, 1]

    application._populate_tag_management_tree(tag_tree)

    tag_tree.delete.assert_called_once_with("old")
    assert tag_tree.insert.call_count == 2
    tag_tree.insert.assert_any_call(
        "",
        "end",
        iid="1",
        values=("小説", 2),
    )
    tag_tree.insert.assert_any_call(
        "",
        "end",
        iid="2",
        values=("技術書", 1),
    )


def test_get_selected_tag_warns_when_not_selected() -> None:
    """タグ未選択時は警告してNoneを返す。"""
    application = create_application()
    tag_tree = Mock()
    tag_tree.selection.return_value = ()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showwarning"
    ) as showwarning:
        result = application._get_selected_tag(tag_tree)

    assert result is None
    showwarning.assert_called_once()


def test_get_selected_tag_returns_id_and_name() -> None:
    """選択中のタグIDと名称を返す。"""
    application = create_application()
    tag_tree = create_tag_tree(tag_id=3, tag_name="歴史")

    assert application._get_selected_tag(tag_tree) == (3, "歴史")


def test_rename_selected_tag_cancels_without_service_call() -> None:
    """名称入力をキャンセルした場合は変更しない。"""
    application = create_application()
    tag_tree = create_tag_tree()

    with patch(
        "book_manager.gui.book_manager_application.simpledialog.askstring",
        return_value=None,
    ):
        application._rename_selected_tag(tag_tree)

    application._service.rename_tag.assert_not_called()


def test_rename_selected_tag_refreshes_after_success() -> None:
    """タグ名変更成功後に各表示を更新する。"""
    application = create_application()
    application._service.rename_tag.return_value = True
    application._refresh_after_tag_change = Mock()
    tag_tree = create_tag_tree()

    with (
        patch(
            "book_manager.gui.book_manager_application.simpledialog.askstring",
            return_value="文学",
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo"
        ),
    ):
        application._rename_selected_tag(tag_tree)

    application._service.rename_tag.assert_called_once_with(
        tag_id=1,
        name="文学",
    )
    application._refresh_after_tag_change.assert_called_once_with(
        tag_tree
    )


def test_rename_selected_tag_displays_validation_error() -> None:
    """タグ名の入力エラーを利用者へ表示する。"""
    application = create_application()
    application._service.rename_tag.side_effect = ValueError(
        "同じ名前のタグがすでに登録されています。"
    )
    application._refresh_after_tag_change = Mock()
    tag_tree = create_tag_tree()

    with (
        patch(
            "book_manager.gui.book_manager_application.simpledialog.askstring",
            return_value="既存タグ",
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror"
        ) as showerror,
    ):
        application._rename_selected_tag(tag_tree)

    showerror.assert_called_once()
    application._refresh_after_tag_change.assert_not_called()


def test_delete_selected_tag_cancels_without_deleting() -> None:
    """削除確認でキャンセルした場合は削除しない。"""
    application = create_application()
    application._service.count_books_by_tag.return_value = 2
    tag_tree = create_tag_tree()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.askyesno",
        return_value=False,
    ):
        application._delete_selected_tag(tag_tree)

    application._service.delete_tag.assert_not_called()


def test_delete_selected_tag_shows_count_and_refreshes() -> None:
    """使用冊数を確認表示し、削除成功後に各表示を更新する。"""
    application = create_application()
    application._service.count_books_by_tag.return_value = 2
    application._service.delete_tag.return_value = True
    application._refresh_after_tag_change = Mock()
    tag_tree = create_tag_tree(tag_name="小説")

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ) as askyesno,
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo"
        ),
    ):
        application._delete_selected_tag(tag_tree)

    assert "2件" in askyesno.call_args.args[1]
    assert "すべての書籍から解除" in askyesno.call_args.args[1]
    application._service.delete_tag.assert_called_once_with(1)
    application._refresh_after_tag_change.assert_called_once_with(
        tag_tree
    )


def test_delete_selected_unused_tag_still_confirms() -> None:
    """未使用タグの場合も削除確認を表示する。"""
    application = create_application()
    application._service.count_books_by_tag.return_value = 0
    tag_tree = create_tag_tree()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.askyesno",
        return_value=False,
    ) as askyesno:
        application._delete_selected_tag(tag_tree)

    assert "0件" in askyesno.call_args.args[1]


def test_refresh_after_tag_change_updates_form_and_lists() -> None:
    """タグ変更後にタグ候補、書籍一覧、編集中フォームを更新する。"""
    application = create_application()
    application._selected_book_id = 10
    application._populate_tag_management_tree = Mock()
    book = BookItem(id=10, title="更新対象", tags=("新名称",))
    application._service.get_book.return_value = book
    tag_tree = Mock()

    application._refresh_after_tag_change(tag_tree)

    application._populate_tag_management_tree.assert_called_once_with(
        tag_tree
    )
    application._refresh_tag_options.assert_called_once_with()
    application._on_reload.assert_called_once_with()
    application._service.get_book.assert_called_once_with(10)
    application._display_book_in_form.assert_called_once_with(book)
