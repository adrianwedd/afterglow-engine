"""
Structured logging for afterglow-engine.

Preserves the visual CLI style ([*], [!], [✓], [✗]) while providing
proper log levels, module tagging, and configurable verbosity.

Environment Variables:
    AFTERGLOW_LOG_LEVEL: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                         Defaults to INFO if not set
"""

import logging
import os
import sys
from typing import Optional


# Custom log level for SUCCESS messages
SUCCESS = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS, "SUCCESS")


class AfterglowFormatter(logging.Formatter):
    """
    Custom formatter that preserves the existing CLI visual style.

    Maps log levels to visual prefixes:
        DEBUG    -> [·]
        INFO     -> [*]
        SUCCESS  -> [✓]
        WARNING  -> [!]
        ERROR    -> [✗]
        CRITICAL -> [✗✗]
    """

    PREFIX_MAP = {
        "DEBUG": "[·]",
        "INFO": "[*]",
        "SUCCESS": "[✓]",
        "WARNING": "[!]",
        "ERROR": "[✗]",
        "CRITICAL": "[✗✗]",
    }

    def __init__(self, include_module: bool = False):
        """
        Initialize formatter.

        Args:
            include_module: If True, include module name in output (for debugging)
        """
        self.include_module = include_module
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with visual prefix."""
        prefix = self.PREFIX_MAP.get(record.levelname, "[?]")

        if self.include_module:
            # Include module name for debugging
            module = record.name.replace("musiclib.", "").replace("__main__", "main")
            return f"{prefix} [{module}] {record.getMessage()}"
        else:
            # Clean output for production
            return f"{prefix} {record.getMessage()}"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance

    Environment Variables:
        AFTERGLOW_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

    Example:
        >>> from musiclib.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
        [*] Processing started
        >>> logger.warning("Low RMS detected")
        [!] Low RMS detected
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        # Get log level from environment
        level_name = os.environ.get("AFTERGLOW_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

        logger.setLevel(level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Determine if we should include module names (useful for DEBUG level)
        include_module = level == logging.DEBUG

        # Set formatter
        formatter = AfterglowFormatter(include_module=include_module)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        # Don't propagate to root logger (avoid duplicate messages)
        logger.propagate = False

    return logger


def log_success(logger: logging.Logger, message: str) -> None:
    """
    Log a success message with [✓] prefix.

    This is a convenience function for the custom SUCCESS level.

    Args:
        logger: Logger instance
        message: Success message

    Example:
        >>> logger = get_logger(__name__)
        >>> log_success(logger, "Saved 10 textures")
        [✓] Saved 10 textures
    """
    logger.log(SUCCESS, message)


def configure_root_logger(level: Optional[str] = None) -> None:
    """
    Configure the root logger for the entire application.

    This should be called once at application startup (in make_textures.py).

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses AFTERGLOW_LOG_LEVEL environment variable

    Example:
        >>> configure_root_logger("DEBUG")  # Enable verbose output
        >>> configure_root_logger()  # Use default (INFO)
    """
    if level:
        os.environ["AFTERGLOW_LOG_LEVEL"] = level.upper()

    # Force reconfiguration by clearing handlers
    root = logging.getLogger()
    root.handlers.clear()

    # Get a configured logger to establish the pattern
    get_logger("afterglow")


# Convenience module-level logger for quick imports
default_logger = get_logger("afterglow")
