"""ファイルログ設定のテスト。"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from book_manager.config.logging_config import (
    APPLICATION_LOGGER_NAME,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_MAX_LOG_BYTES,
    configure_file_logging,
    get_application_logger,
)


@pytest.fixture(autouse=True)
def reset_application_logger() -> None:
    """テストごとにアプリケーションLoggerを初期化する。"""
    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    original_level = logger.level
    original_propagate = logger.propagate
    original_handlers = tuple(logger.handlers)

    for handler in original_handlers:
        logger.removeHandler(handler)

    yield

    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    for handler in original_handlers:
        logger.addHandler(handler)

    logger.setLevel(original_level)
    logger.propagate = original_propagate


def test_configure_file_logging_creates_log_directory(
    tmp_path: Path,
) -> None:
    """存在しないログディレクトリを作成する。"""
    log_path = tmp_path / "application" / "logs" / "app.log"

    configure_file_logging(log_path)

    assert log_path.parent.is_dir()
    assert log_path.is_file()


def test_configure_file_logging_writes_utf8_message(
    tmp_path: Path,
) -> None:
    """日本語をUTF-8でログへ記録する。"""
    log_path = tmp_path / "logs" / "app.log"
    logger = configure_file_logging(log_path)

    logger.info("書籍管理を起動しました。")

    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "INFO book_manager" in content
    assert "書籍管理を起動しました。" in content


def test_configure_file_logging_uses_expected_defaults(
    tmp_path: Path,
) -> None:
    """既定の最大サイズと世代数を使用する。"""
    logger = configure_file_logging(
        tmp_path / "logs" / "app.log"
    )

    handler = logger.handlers[0]

    assert handler.maxBytes == DEFAULT_MAX_LOG_BYTES
    assert handler.backupCount == DEFAULT_LOG_BACKUP_COUNT


def test_configure_file_logging_replaces_existing_handler(
    tmp_path: Path,
) -> None:
    """再設定してもHandlerを重複させない。"""
    first_path = tmp_path / "first" / "app.log"
    second_path = tmp_path / "second" / "app.log"
    logger = configure_file_logging(first_path)
    first_handler = logger.handlers[0]

    configured_logger = configure_file_logging(second_path)

    assert configured_logger is logger
    assert len(logger.handlers) == 1
    assert logger.handlers[0] is not first_handler


def test_configure_file_logging_does_not_propagate(
    tmp_path: Path,
) -> None:
    """ルートLoggerへ重複して伝播しない。"""
    logger = configure_file_logging(
        tmp_path / "logs" / "app.log"
    )

    assert logger.propagate is False
    assert logger.level == logging.INFO


def test_configure_file_logging_rotates_file(
    tmp_path: Path,
) -> None:
    """最大サイズを超えたログをローテーションする。"""
    log_path = tmp_path / "logs" / "app.log"
    logger = configure_file_logging(
        log_path,
        max_bytes=80,
        backup_count=2,
    )

    for index in range(20):
        logger.info("ログメッセージ %s", index)

    for handler in logger.handlers:
        handler.flush()

    assert log_path.is_file()
    assert (log_path.parent / "app.log.1").is_file()
    assert len(list(log_path.parent.glob("app.log*"))) <= 3


def test_configure_file_logging_rejects_relative_path() -> None:
    """相対ログパスを拒否する。"""
    with pytest.raises(
        ValueError,
        match="絶対パスを指定してください。",
    ):
        configure_file_logging(Path("logs/app.log"))


@pytest.mark.parametrize("max_bytes", [0, -1])
def test_configure_file_logging_rejects_invalid_max_bytes(
    tmp_path: Path,
    max_bytes: int,
) -> None:
    """不正な最大ファイルサイズを拒否する。"""
    with pytest.raises(
        ValueError,
        match="最大サイズは1以上",
    ):
        configure_file_logging(
            tmp_path / "app.log",
            max_bytes=max_bytes,
        )


def test_configure_file_logging_rejects_negative_backup_count(
    tmp_path: Path,
) -> None:
    """負のログ世代数を拒否する。"""
    with pytest.raises(
        ValueError,
        match="世代数は0以上",
    ):
        configure_file_logging(
            tmp_path / "app.log",
            backup_count=-1,
        )


def test_configure_file_logging_raises_for_conflicting_file(
    tmp_path: Path,
) -> None:
    """ログディレクトリと同名のファイルがあれば通知する。"""
    conflicting_path = tmp_path / "logs"
    conflicting_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(FileExistsError):
        configure_file_logging(conflicting_path / "app.log")


def test_get_application_logger_returns_shared_logger() -> None:
    """共通名のLoggerを返す。"""
    logger = get_application_logger()

    assert logger is logging.getLogger(APPLICATION_LOGGER_NAME)
