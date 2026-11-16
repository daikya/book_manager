"""667件の一覧でも初期表示は可視行だけを読み、更新時に画像を再利用する。"""
from collections import OrderedDict
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.book_item import BookItem


def app():
    obj=BookManagerApplication.__new__(BookManagerApplication)
    obj._root=Mock();obj._book_tree=Mock();obj._book_tree.get_children.return_value=()
    obj._book_tree.winfo_height.return_value=240
    obj._book_tree.identify_row.side_effect=lambda y:str(1+y//56)
    obj._thumbnail_photos={};obj._thumbnail_books={};obj._thumbnail_cache=OrderedDict()
    obj._thumbnail_job=None;obj._count_status_var=Mock();obj._service=Mock()
    return obj


def test_667_rows_do_not_decode_all_images_and_scroll_loads_new_rows():
    obj=app();obj._create_thumbnail_photo=Mock(side_effect=lambda path:Mock())
    books=[BookItem(id=i,title=f'本{i}',cover_image_path=f'{i}.png') for i in range(1,668)]
    obj._display_books(books,status_prefix='全')
    assert obj._book_tree.insert.call_count==667
    obj._create_thumbnail_photo.assert_not_called()
    obj._load_visible_thumbnails()
    assert obj._create_thumbnail_photo.call_count==5
    obj._load_visible_thumbnails()
    assert obj._create_thumbnail_photo.call_count==5
    obj._book_tree.identify_row.side_effect=lambda y:str(100+y//56)
    obj._load_visible_thumbnails()
    assert obj._create_thumbnail_photo.call_count==10


def test_thumbnail_is_reused_until_file_changes(tmp_path):
    obj=app();path=tmp_path/'a.png';Image.new('RGB',(400,600),'red').save(path)
    obj._service.resolve_cover_image_path.return_value=path
    with patch('book_manager.gui.book_manager_application.Image.open',wraps=Image.open) as opened,patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage',side_effect=lambda image:Mock()):
        first=obj._create_thumbnail_photo('stored')
        second=obj._create_thumbnail_photo('stored')
        assert first is second and opened.call_count==1
        Image.new('RGB',(600,400),'blue').save(path)
        third=obj._create_thumbnail_photo('stored')
        assert third is not first and opened.call_count==2


def test_refresh_cannot_apply_a_previous_book_list_job():
    obj=app();obj._create_thumbnail_photo=Mock(return_value=Mock())
    obj._display_books([BookItem(id=1,title='旧',cover_image_path='old')],status_prefix='全')
    obj._display_books([BookItem(id=2,title='新',cover_image_path='new')],status_prefix='全')
    obj._book_tree.identify_row.return_value='2';obj._book_tree.identify_row.side_effect=None
    obj._load_visible_thumbnails()
    obj._create_thumbnail_photo.assert_called_once_with('new')


def test_geometry_events_schedule_only_one_pending_job():
    obj=app();obj._schedule_visible_thumbnails();obj._schedule_visible_thumbnails()
    obj._root.after_idle.assert_called_once()


def test_thumbnail_cache_is_bounded_when_many_books_are_browsed(tmp_path):
    obj=app()
    obj._service.resolve_cover_image_path.side_effect=lambda stored:Path(stored)
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage',side_effect=lambda image:Mock()):
        for index in range(260):
            path=tmp_path/f'{index}.png';Image.new('RGB',(1,1)).save(path)
            obj._create_thumbnail_photo(str(path))
    assert len(obj._thumbnail_cache)==256
    assert not any(key[0]==str(tmp_path/'0.png') for key in obj._thumbnail_cache)
