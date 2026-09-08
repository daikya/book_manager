"""アプリケーションのファイルログを設定する。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


APPLICATION_LOGGER_NAME = "book_manager"
DEFAULT_MAX_LOG_BYTES = 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3
LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def configure_file_logging(
    log_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """ローテーション付きファイルログを設定する。

    同じプロセスで再設定された場合は既存Handlerを閉じて交換し、
    ログの重複出力とファイルハンドルのリークを防ぐ。

    Args:
        log_path:
            ログファイルの絶対パス。
        max_bytes:
            ローテーションする最大ファイルサイズ。
        backup_count:
            保持する旧ログの世代数。

    Returns:
        設定済みのアプリケーションLogger。

    Raises:
        ValueError:
            相対パス、不正な最大サイズまたは世代数の場合。
        OSError:
            ログディレクトリまたはファイルを作成できない場合。
    """
    normalized_log_path = Path(log_path).expanduser()

    if not normalized_log_path.is_absolute():
        raise ValueError(
            "ログファイルには絶対パスを指定してください。"
        )

    if max_bytes <= 0:
        raise ValueError(
            "ログファイルの最大サイズは1以上にしてください。"
        )

    if backup_count < 0:
        raise ValueError(
            "ログファイルの世代数は0以上にしてください。"
        )

    normalized_log_path = normalized_log_path.resolve(
        strict=False,
    )
    normalized_log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    handler = RotatingFileHandler(
        normalized_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger = logging.getLogger(APPLICATION_LOGGER_NAME)

    for existing_handler in tuple(logger.handlers):
        logger.removeHandler(existing_handler)
        existing_handler.close()

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)

    return logger


def get_application_logger() -> logging.Logger:
    """アプリケーション共通Loggerを返す。"""
    return logging.getLogger(APPLICATION_LOGGER_NAME)
