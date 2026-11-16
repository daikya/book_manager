"""別画面の長文反映・取消・書籍切替時の保持。"""
from unittest.mock import Mock, patch
import pytest
from book_manager.gui.long_text_dialog import FormTextValue,LongTextDialog,text_dialog_store
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.config.window_state_store import WindowStateStore


def test_value_retains_unicode_multiline_and_text_end_semantics():
    text=FormTextValue('内容\n\n末尾\n')
    assert text.get('1.0','end-1c')=='内容\n\n末尾\n'
    assert text.get('1.0','end')=='内容\n\n末尾\n\n'
    text.delete('1.0','end');text.insert('1.0','新しい文')
    assert text.get()=='新しい文'


def test_description_and_notes_have_separate_geometry_files(tmp_path):
    base=WindowStateStore(tmp_path/'window_state.json')
    assert text_dialog_store(base,'description').path != text_dialog_store(base,'notes').path
    assert text_dialog_store(None,'notes') is None


@pytest.mark.parametrize('field',['description','notes'])
@pytest.mark.parametrize('result',[None,'変更\nした文',''])
def test_edit_only_changes_pending_form(field,result):
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._root=Mock();app._service=Mock();app._selected_book_id=7
    app._description_text=FormTextValue('元の紹介');app._notes_text=FormTextValue('元の備考')
    value=app._description_text if field=='description' else app._notes_text
    before=value.value
    with patch('book_manager.gui.book_manager_application.LongTextDialog') as dialog:
        dialog.return_value.show.return_value=result
        app._on_edit_long_text(field)
        assert dialog.call_args.kwargs['value']==before
    assert value.value==(before if result is None else result)
    app._service.update_book.assert_not_called()


def test_changed_book_does_not_receive_old_edit():
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._root=Mock();app._selected_book_id=7
    app._description_text=FormTextValue('元');app._notes_text=FormTextValue()
    def finish():app._selected_book_id=8;return '変更'
    with patch('book_manager.gui.book_manager_application.LongTextDialog') as dialog,patch('book_manager.gui.book_manager_application.messagebox.showwarning') as warning:
        dialog.return_value.show.side_effect=finish;app._on_edit_long_text('description')
        warning.assert_called_once()
    assert app._description_text.value=='元'


def test_apply_keeps_all_text_and_closes():
    dialog=LongTextDialog.__new__(LongTextDialog)
    dialog._text=Mock();dialog._text.get.return_value='長文\n\n';dialog.window=Mock()
    dialog._apply()
    assert dialog.result=='長文\n\n'
    dialog.window.destroy.assert_called_once_with()
