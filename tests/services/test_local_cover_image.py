"""ローカル書影は確認まで保存せず、元画像から独立して保持する。"""
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from PIL import Image

from book_manager.services.cover_image_service import CoverImageService
from book_manager.services.local_cover_image import prepare_local_cover
from book_manager.services.book_service import BookService
from book_manager.repositories.book_repository import BookRepository
from book_manager.database.initializer import initialize_database


def service(tmp_path):
    return CoverImageService(session=Mock(), root_directory=tmp_path/'home', cache_directory=tmp_path/'home'/'cache'/'covers')


@pytest.mark.parametrize('format_', ['PNG', 'JPEG', 'WEBP', 'GIF', 'BMP'])
def test_supported_images_prepare_without_writing_and_without_network(tmp_path, format_):
    source = tmp_path/'source.image'
    Image.new('RGB', (30, 50), 'red').save(source, format=format_)
    before = source.read_bytes();s = service(tmp_path)
    prepared = s.prepare_local_image(source)
    assert not (tmp_path/'home').exists() and source.read_bytes() == before
    with Image.open(BytesIO(prepared.png_data)) as image:
        assert image.format == 'PNG' and image.size == (30, 50)
    s._session.get.assert_not_called()


def test_alpha_is_preserved(tmp_path):
    source = tmp_path/'alpha.png';Image.new('RGBA',(20,30),(255,0,0,80)).save(source)
    prepared = prepare_local_cover(source)
    with Image.open(BytesIO(prepared.png_data)) as image:
        assert image.mode == 'RGBA' and image.getpixel((0,0))[3] == 80


def test_orientation_is_applied_and_metadata_is_removed(tmp_path):
    source = tmp_path/'rotated.jpg';image = Image.new('RGB',(30,50),'blue')
    exif = Image.Exif();exif[274] = 6;exif[270] = '元のメタデータ'
    image.save(source, exif=exif)
    prepared = prepare_local_cover(source)
    with Image.open(BytesIO(prepared.png_data)) as image:
        assert image.size == (50,30) and not image.getexif()


def test_large_image_fits_without_enlarging_small_images(tmp_path):
    source = tmp_path/'wide.png';Image.new('RGB',(2800,1000),'blue').save(source)
    prepared = prepare_local_cover(source)
    assert prepared.width == 1600 and prepared.height <= 2400


def test_animated_gif_uses_first_frame(tmp_path):
    source = tmp_path/'animated.gif';first = Image.new('RGB',(10,20),'red');second = Image.new('RGB',(10,20),'blue')
    first.save(source, save_all=True, append_images=[second], duration=100, loop=0)
    prepared = prepare_local_cover(source)
    with Image.open(BytesIO(prepared.png_data)) as image:
        assert image.convert('RGB').getpixel((0,0)) == (255,0,0)
        assert getattr(image, 'n_frames', 1) == 1


@pytest.mark.parametrize('kind', ['missing', 'text', 'truncated', 'unsupported'])
def test_invalid_input_does_not_write_to_application(tmp_path, kind):
    source = tmp_path/'source.png'
    if kind == 'text':source.write_text('not an image')
    if kind == 'truncated':
        image = BytesIO();Image.new('RGB',(100,100)).save(image, format='PNG');source.write_bytes(image.getvalue()[:40])
    if kind == 'unsupported':Image.new('RGB',(10,20)).save(source, format='TIFF')
    with pytest.raises(ValueError):service(tmp_path).prepare_local_image(source)
    assert not (tmp_path/'home').exists()


def test_size_and_pixel_limits_are_checked_without_huge_test_data(tmp_path, monkeypatch):
    source = tmp_path/'source.png';Image.new('RGB',(10,20)).save(source)
    with monkeypatch.context() as m:
        m.setattr('book_manager.services.local_cover_image.MAX_FILE_BYTES', 8)
        with pytest.raises(ValueError, match='20MB'):prepare_local_cover(source)
    with monkeypatch.context() as m:
        m.setattr('book_manager.services.local_cover_image.MAX_IMAGE_PIXELS', 10)
        with pytest.raises(ValueError, match='2000万画素'):prepare_local_cover(source)


def test_import_is_independent_of_source_and_survives_cache_clear_and_db_reopen(tmp_path):
    source = tmp_path/'source.png';Image.new('RGB',(30,50),'green').save(source)
    s = service(tmp_path);prepared = s.prepare_local_image(source)
    path = s.store_local_image(prepared);stored = s.create_stored_path(path)
    assert stored.startswith('cache/covers/local/')
    source.unlink()
    db = tmp_path/'home'/'data'/'books.db';initialize_database(db)
    books = BookService(BookRepository(db), cover_image_service=s)
    book = books.add_book(title='ISBNのない本', cover_image_path=stored)
    assert book.isbn is None and book.cover_image_url is None
    (path.parent.parent/'downloaded.jpg').write_bytes(b'downloaded cache')
    assert s.get_cache_status().file_count == 1
    assert s.clear_cache().deleted_count == 1
    assert path.is_file()
    reopened = BookService(BookRepository(db), cover_image_service=service(tmp_path))
    saved = reopened.get_book(book.id)
    assert reopened.resolve_cover_image_path(saved.cover_image_path) == path
    with Image.open(path) as image:assert image.size == (30,50)
    s._session.get.assert_not_called()


def test_same_prepared_image_reuses_hash_path_and_refreshes_broken_copy(tmp_path):
    source = tmp_path/'source.png';Image.new('RGB',(30,50)).save(source)
    s = service(tmp_path);prepared = s.prepare_local_image(source)
    first = s.store_local_image(prepared);first.write_bytes(b'corrupt')
    assert s.store_local_image(prepared) == first and first.read_bytes() == prepared.png_data
    assert len(list(first.parent.iterdir())) == 1


def test_failed_atomic_write_keeps_previous_image_and_removes_temporary_file(tmp_path):
    source = tmp_path/'source.png';Image.new('RGB',(30,50)).save(source)
    s = service(tmp_path);prepared = s.prepare_local_image(source);first = s.store_local_image(prepared)
    with patch('book_manager.services.cover_image_service.os.replace', side_effect=OSError('disk')):
        with pytest.raises(OSError):s.store_local_image(prepared)
    assert first.read_bytes() == prepared.png_data and len(list(first.parent.iterdir())) == 1


def test_book_service_only_prepares_until_explicit_store(tmp_path):
    covers = service(tmp_path);source = tmp_path/'source.png';Image.new('RGB',(10,20)).save(source)
    repo = Mock();books = BookService(repo, cover_image_service=covers)
    prepared = books.prepare_local_cover_image(source)
    assert not (tmp_path/'home').exists()
    assert books.store_local_cover_image(prepared).is_file()
    assert not repo.method_calls
