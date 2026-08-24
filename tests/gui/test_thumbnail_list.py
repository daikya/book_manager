"""表紙サムネイル付き一覧に関するGUIロジックのテスト。"""

from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from PIL import Image

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem


def create_application() -> BookManagerApplication:
    """テスト用のBookManagerApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._thumbnail_photos = {}
    application._book_tree = Mock()
    application._count_status_var = Mock()

    return application


def test_create_thumbnail_photo_returns_none_for_none_path() -> None:
    """表紙パスがNoneの場合はNoneを返す。"""
    application = create_application()

    result = application._create_thumbnail_photo(
        None,
    )

    assert result is None


def test_create_thumbnail_photo_returns_none_for_missing_file(
    tmp_path: Path,
) -> None:
    """表紙ファイルが存在しない場合はNoneを返す。"""
    application = create_application()

    result = application._create_thumbnail_photo(
        str(tmp_path / "missing.jpg"),
    )

    assert result is None


def test_create_thumbnail_photo_creates_thumbnail(
    tmp_path: Path,
) -> None:
    """正常な画像からサムネイルを生成する。"""
    application = create_application()

    image_path = tmp_path / "cover.jpg"

    Image.new(
        "RGB",
        (400, 600),
    ).save(
        image_path,
    )

    fake_photo = Mock()

    with patch(
        "book_manager.gui.book_manager_application.ImageTk.PhotoImage",
        return_value=fake_photo,
    ):
        result = application._create_thumbnail_photo(
            str(image_path),
        )

    assert result is fake_photo


def test_create_thumbnail_photo_resizes_within_maximum_size(
    tmp_path: Path,
) -> None:
    """サムネイルが最大40×55px以内になる。"""
    application = create_application()

    image_path = tmp_path / "cover.jpg"

    Image.new(
        "RGB",
        (400, 600),
    ).save(
        image_path,
    )

    captured_size: tuple[int, int] | None = None

    def fake_photo_image(
        image: Image.Image,
    ) -> Mock:
        nonlocal captured_size
        captured_size = image.size
        return Mock()

    with patch(
        "book_manager.gui.book_manager_application.ImageTk.PhotoImage",
        side_effect=fake_photo_image,
    ):
        application._create_thumbnail_photo(
            str(image_path),
        )

    assert captured_size is not None
    assert captured_size[0] <= 40
    assert captured_size[1] <= 55


def test_create_thumbnail_photo_returns_none_for_broken_image(
    tmp_path: Path,
) -> None:
    """破損画像の場合はNoneを返す。"""
    application = create_application()

    image_path = tmp_path / "broken.jpg"
    image_path.write_text(
        "画像ではないデータ",
        encoding="utf-8",
    )

    with patch(
        "book_manager.gui.book_manager_application.traceback.print_exc",
    ):
        result = application._create_thumbnail_photo(
            str(image_path),
        )

    assert result is None


def test_display_books_clears_old_thumbnail_photos() -> None:
    """一覧再表示時に古いサムネイル参照をクリアする。"""
    application = create_application()

    application._thumbnail_photos[1] = Mock()

    application._book_tree.get_children.return_value = []

    application._display_books(
        [],
        status_prefix="全",
    )

    assert application._thumbnail_photos == {}


def test_display_books_keeps_created_thumbnail_photo() -> None:
    """生成したサムネイルをBookID単位で保持する。"""
    application = create_application()

    application._book_tree.get_children.return_value = []

    thumbnail_photo = Mock()

    application._create_thumbnail_photo = Mock(
        return_value=thumbnail_photo,
    )

    book = BookItem(
        id=1,
        title="テスト書籍",
        cover_image_path="cache/covers/test.jpg",
    )

    application._display_books(
        [book],
        status_prefix="全",
    )

    assert application._thumbnail_photos == {
        1: thumbnail_photo,
    }
    call_kwargs = (
        application._book_tree.insert.call_args.kwargs
    )

    assert call_kwargs["image"] is thumbnail_photo

def test_display_books_inserts_book_without_cover() -> None:
    """表紙なし書籍もTreeviewへ追加できる。"""
    application = create_application()

    application._book_tree.get_children.return_value = []

    application._create_thumbnail_photo = Mock(
        return_value=None,
    )

    book = BookItem(
        id=1,
        title="表紙なし書籍",
        cover_image_path=None,
    )

    application._display_books(
        [book],
        status_prefix="全",
    )

    application._book_tree.insert.assert_called_once()

    call_kwargs = (
        application._book_tree.insert.call_args.kwargs
    )

    assert call_kwargs["iid"] == "1"
    assert call_kwargs["image"] == ""

def test_create_thumbnail_photo_preserves_aspect_ratio(
    tmp_path: Path,
) -> None:
    """サムネイル生成時に元画像の縦横比を維持する。"""
    application = create_application()

    image_path = tmp_path / "cover.jpg"

    Image.new(
        "RGB",
        (400, 600),
    ).save(
        image_path,
    )

    captured_size: tuple[int, int] | None = None

    def fake_photo_image(
        image: Image.Image,
    ) -> Mock:
        nonlocal captured_size
        captured_size = image.size
        return Mock()

    with patch(
        "book_manager.gui.book_manager_application.ImageTk.PhotoImage",
        side_effect=fake_photo_image,
    ):
        application._create_thumbnail_photo(
            str(image_path),
        )

    assert captured_size is not None

    original_ratio = 400 / 600
    thumbnail_ratio = (
        captured_size[0]
        / captured_size[1]
    )

    assert thumbnail_ratio == pytest.approx(
        original_ratio,
        abs=0.02,
    )