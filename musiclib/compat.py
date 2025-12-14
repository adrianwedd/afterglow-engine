"""
Compatibility helpers for migrating from print() to logging.

Provides drop-in replacement functions that preserve existing behavior
while enabling structured logging. Use these during gradual migration.
"""

import sys
from typing import Optional
from musiclib.logger import get_logger, log_success


# Global logger for compatibility functions
_compat_logger = get_logger("afterglow.compat")


def print_info(message: str, file=sys.stdout) -> None:
    """
    Drop-in replacement for print() that uses structured logging.

    Maps to INFO level with [*] prefix.

    Args:
        message: Message to log
        file: Output file (for compatibility; ignored in favor of logger)

    Example:
        # Before:
        print(f"Processing {filename}")

        # After (gradual migration):
        from musiclib.compat import print_info
        print_info(f"Processing {filename}")
    """
    _compat_logger.info(message)


def print_warning(message: str, file=sys.stderr) -> None:
    """
    Drop-in replacement for warning print() that uses structured logging.

    Maps to WARNING level with [!] prefix.

    Args:
        message: Warning message to log
        file: Output file (for compatibility; ignored in favor of logger)

    Example:
        # Before:
        print(f"[!] Warning: {issue}", file=sys.stderr)

        # After:
        from musiclib.compat import print_warning
        print_warning(f"Warning: {issue}")
    """
    _compat_logger.warning(message)


def print_success(message: str, file=sys.stdout) -> None:
    """
    Drop-in replacement for success print() that uses structured logging.

    Maps to SUCCESS level with [✓] prefix.

    Args:
        message: Success message to log
        file: Output file (for compatibility; ignored in favor of logger)

    Example:
        # Before:
        print(f"[✓] Saved {count} textures")

        # After:
        from musiclib.compat import print_success
        print_success(f"Saved {count} textures")
    """
    log_success(_compat_logger, message)


def print_error(message: str, file=sys.stderr) -> None:
    """
    Drop-in replacement for error print() that uses structured logging.

    Maps to ERROR level with [✗] prefix.

    Args:
        message: Error message to log
        file: Output file (for compatibility; ignored in favor of logger)

    Example:
        # Before:
        print(f"Error: {error}", file=sys.stderr)

        # After:
        from musiclib.compat import print_error
        print_error(f"Error: {error}")
    """
    _compat_logger.error(message)


def migrate_prefix(message: str) -> str:
    """
    Remove explicit prefixes from messages during migration.

    Removes common prefixes like [*], [!], [✓], [✗] since the logger
    adds them automatically.

    Args:
        message: Message possibly containing prefix

    Returns:
        Message with prefix removed (if present)

    Example:
        >>> migrate_prefix("[*] Processing file")
        "Processing file"
        >>> migrate_prefix("[!] Warning: low RMS")
        "Warning: low RMS"
        >>> migrate_prefix("No prefix here")
        "No prefix here"
    """
    prefixes = ["[*]", "[!]", "[✓]", "[✗]", "[✗✗]", "[·]", "[config]"]
    for prefix in prefixes:
        if message.startswith(prefix):
            # Remove prefix and any following whitespace
            return message[len(prefix):].lstrip()
    return message


def detect_log_level(message: str) -> str:
    """
    Detect intended log level from message prefix.

    Useful for automated migration scripts.

    Args:
        message: Message with potential prefix

    Returns:
        Log level name (DEBUG, INFO, WARNING, ERROR, SUCCESS)

    Example:
        >>> detect_log_level("[*] Processing")
        "INFO"
        >>> detect_log_level("[!] Warning")
        "WARNING"
        >>> detect_log_level("[✓] Success")
        "SUCCESS"
    """
    if message.startswith("[!]"):
        return "WARNING"
    elif message.startswith("[✓]"):
        return "SUCCESS"
    elif message.startswith("[✗✗]"):
        return "CRITICAL"
    elif message.startswith("[✗]"):
        return "ERROR"
    elif message.startswith("[·]"):
        return "DEBUG"
    else:
        # Default to INFO for [*] or no prefix
        return "INFO"
