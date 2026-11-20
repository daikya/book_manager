"""ローカル書影の検証・正規化。プレビュー準備はファイルを書き込まない。"""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
SUPPORTED_FORMATS = frozenset({'JPEG', 'PNG', 'WEBP', 'GIF', 'BMP'})


@dataclass(frozen=True, slots=True)
class PreparedCoverImage:
    png_data: bytes
    width: int
    height: int


def prepare_local_cover(path: Path) -> PreparedCoverImage:
    """先頭フレームを向き補正し、最大1600×2400のPNGへ整える。"""
    source = Path(path)
    if not source.is_file():
        raise ValueError('画像ファイルが見つかりません。')
    with source.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('画像ファイルは20MB以内にしてください。')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in SUPPORTED_FORMATS:
                    raise ValueError('JPEG・PNG・WebP・GIF・BMPの画像を選択してください。')
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError('画像は2000万画素以内にしてください。')
                image.seek(0)
                image.load()
                oriented = ImageOps.exif_transpose(image)
                mode = 'RGBA' if 'A' in oriented.getbands() or 'transparency' in oriented.info else 'RGB'
                normalized = oriented.convert(mode)
                normalized.thumbnail((1600, 2400), Image.Resampling.LANCZOS)
                normalized.info.clear()
                output = BytesIO()
                normalized.save(output, format='PNG')
                return PreparedCoverImage(output.getvalue(), normalized.width, normalized.height)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ValueError('画像を読み込めませんでした。破損していない対応形式の画像を選択してください。') from error
