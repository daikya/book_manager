"""外部書誌情報取得機能の例外クラス。"""


class BookMetadataError(Exception):
    """外部書誌情報取得機能の基底例外。"""


class BookMetadataConnectionError(BookMetadataError):
    """通信エラー。"""


class BookMetadataResponseError(BookMetadataError):
    """レスポンス解析エラー。"""


class BookMetadataRateLimitError(BookMetadataError):
    """API利用制限エラー。"""


class BookMetadataNotFoundError(BookMetadataError):
    """対象書籍が存在しない。"""


class BookMetadataConfigurationError(BookMetadataError):
    """設定エラー。"""