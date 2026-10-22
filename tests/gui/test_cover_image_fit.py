"""書影を実表示領域に収め、元画像と保存ファイルを保持する。"""
from unittest.mock import Mock,patch
from PIL import Image
import pytest
from book_manager.gui.book_manager_application import BookManagerApplication


@pytest.mark.parametrize('size',[(1200,1800),(1800,1200),(1200,1200),(100,2400),(2400,100)])
def test_cover_fits_actual_viewport_preserving_aspect(size,tmp_path):
    path=tmp_path/'cover.png';Image.new('RGB',size,'blue').save(path)
    original=path.read_bytes()
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._cover_viewport=Mock()
    app._cover_viewport.winfo_width.return_value=125
    app._cover_viewport.winfo_height.return_value=175
    app._cover_image_label=Mock()
    rendered=[]
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage',side_effect=lambda image:rendered.append(image.copy()) or Mock()):
        app._display_cover_image(str(path))
    width,height=rendered[0].size
    assert width<=121 and height<=171
    assert abs(width-size[0]*height/size[1])<=max(1,size[0]/size[1])
    assert app._cover_source_image.size==size
    assert path.read_bytes()==original


def test_resize_uses_original_and_can_grow_again_without_rereading(tmp_path):
    path=tmp_path/'cover.png';Image.new('RGB',(1000,1500)).save(path)
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._cover_viewport=Mock();app._cover_image_label=Mock()
    app._cover_viewport.winfo_width.return_value=170
    app._cover_viewport.winfo_height.return_value=240
    rendered=[]
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage',side_effect=lambda image:rendered.append(image.size) or Mock()):
        app._display_cover_image(str(path))
        path.unlink()
        app._cover_viewport.winfo_width.return_value=70
        app._cover_viewport.winfo_height.return_value=100
        app._on_cover_viewport_resize()
        app._cover_viewport.winfo_width.return_value=170
        app._cover_viewport.winfo_height.return_value=240
        app._on_cover_viewport_resize()
    assert rendered[0]==rendered[2]
    assert rendered[1][0]<rendered[0][0]
    assert rendered[1][1]<rendered[0][1]


def test_small_image_is_not_enlarged():
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._cover_image_label=Mock()
    rendered=[]
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage',side_effect=lambda image:rendered.append(image.size) or Mock()):
        app._render_cover_image(Image.new('RGB',(20,30)))
    assert rendered==[(20,30)]


def test_clear_prevents_old_image_reappearing_after_resize():
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._cover_image_label=Mock();app._cover_source_image=Image.new('RGB',(100,150))
    app._clear_cover_image()
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage') as photo:
        app._on_cover_viewport_resize()
    photo.assert_not_called()
    assert app._cover_photo is None
    app._cover_image_label.configure.assert_called_once_with(image='',text='画像なし')


def test_layout_not_ready_has_safe_initial_size():
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._cover_viewport=Mock();app._cover_image_label=Mock()
    app._cover_viewport.winfo_width.return_value=1
    app._cover_viewport.winfo_height.return_value=1
    with patch('book_manager.gui.book_manager_application.ImageTk.PhotoImage') as photo:
        app._render_cover_image(Image.new('RGB',(1000,1500)))
    image=photo.call_args.args[0]
    assert image.width<=166 and image.height<=236
