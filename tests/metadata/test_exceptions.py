"""Tests for metadata exceptions."""

from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
    BookMetadataConnectionError,
    BookMetadataError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)


def test_connection_error_is_book_metadata_error() -> None:
    """ConnectionErrorが基底例外を継承することを確認する。"""
    assert issubclass(
        BookMetadataConnectionError,
        BookMetadataError,
    )


def test_response_error_is_book_metadata_error() -> None:
    """ResponseErrorが基底例外を継承することを確認する。"""
    assert issubclass(
        BookMetadataResponseError,
        BookMetadataError,
    )


def test_rate_limit_error_is_book_metadata_error() -> None:
    """RateLimitErrorが基底例外を継承することを確認する。"""
    assert issubclass(
        BookMetadataRateLimitError,
        BookMetadataError,
    )


def test_not_found_error_is_book_metadata_error() -> None:
    """NotFoundErrorが基底例外を継承することを確認する。"""
    assert issubclass(
        BookMetadataNotFoundError,
        BookMetadataError,
    )


def test_configuration_error_is_book_metadata_error() -> None:
    """ConfigurationErrorが基底例外を継承することを確認する。"""
    assert issubclass(
        BookMetadataConfigurationError,
        BookMetadataError,
    )


def test_exception_message_is_preserved() -> None:
    """例外メッセージが保持されることを確認する。"""
    message = "connection failed"

    exception = BookMetadataConnectionError(message)

    assert str(exception) == message