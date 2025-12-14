"""
Tests for the structured logging system.

Verifies log level handling, prefix formatting, and environment variable configuration.
"""

import unittest
import os
import logging
from io import StringIO
import sys

# Import logging modules
from musiclib.logger import get_logger, log_success, configure_root_logger, AfterglowFormatter
from musiclib.compat import migrate_prefix, detect_log_level


class TestAfterglowFormatter(unittest.TestCase):
    """Test the custom log formatter."""

    def setUp(self):
        """Create formatter instances for testing."""
        self.formatter = AfterglowFormatter(include_module=False)
        self.formatter_with_module = AfterglowFormatter(include_module=True)

    def test_info_prefix(self):
        """Verify INFO messages use [*] prefix."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing file",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertEqual(formatted, "[*] Processing file")

    def test_warning_prefix(self):
        """Verify WARNING messages use [!] prefix."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Low RMS detected",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertEqual(formatted, "[!] Low RMS detected")

    def test_error_prefix(self):
        """Verify ERROR messages use [✗] prefix."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="File not found",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertEqual(formatted, "[✗] File not found")

    def test_success_prefix(self):
        """Verify SUCCESS messages use [✓] prefix."""
        from musiclib.logger import SUCCESS

        record = logging.LogRecord(
            name="test",
            level=SUCCESS,
            pathname="",
            lineno=0,
            msg="Saved 10 textures",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertEqual(formatted, "[✓] Saved 10 textures")

    def test_debug_prefix(self):
        """Verify DEBUG messages use [·] prefix."""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Computing STFT",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertEqual(formatted, "[·] Computing STFT")

    def test_module_name_included(self):
        """Verify module name is included when requested."""
        record = logging.LogRecord(
            name="musiclib.audio_analyzer",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Analyzing audio",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter_with_module.format(record)
        self.assertEqual(formatted, "[*] [audio_analyzer] Analyzing audio")

    def test_module_name_cleanup(self):
        """Verify module name cleanup (removes musiclib. prefix)."""
        record = logging.LogRecord(
            name="musiclib.dsp_utils",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Normalizing audio",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter_with_module.format(record)
        self.assertIn("[dsp_utils]", formatted)
        self.assertNotIn("musiclib.", formatted)


class TestLogger(unittest.TestCase):
    """Test logger creation and configuration."""

    def setUp(self):
        """Clean up environment before each test."""
        # Save original environment
        self.original_log_level = os.environ.get("AFTERGLOW_LOG_LEVEL")

        # Clear all handlers to start fresh
        logging.getLogger().handlers.clear()
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()

    def tearDown(self):
        """Restore environment after each test."""
        if self.original_log_level is not None:
            os.environ["AFTERGLOW_LOG_LEVEL"] = self.original_log_level
        elif "AFTERGLOW_LOG_LEVEL" in os.environ:
            del os.environ["AFTERGLOW_LOG_LEVEL"]

    def test_logger_creation(self):
        """Verify logger can be created."""
        logger = get_logger("test_module")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_module")

    def test_default_log_level(self):
        """Verify default log level is INFO."""
        if "AFTERGLOW_LOG_LEVEL" in os.environ:
            del os.environ["AFTERGLOW_LOG_LEVEL"]

        logger = get_logger("test_default_level")
        self.assertEqual(logger.level, logging.INFO)

    def test_environment_variable_log_level(self):
        """Verify log level can be set via environment variable."""
        os.environ["AFTERGLOW_LOG_LEVEL"] = "DEBUG"

        logger = get_logger("test_env_level")
        self.assertEqual(logger.level, logging.DEBUG)

    def test_log_success_helper(self):
        """Verify log_success() helper function."""
        logger = get_logger("test_success")

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(AfterglowFormatter())
        logger.handlers.clear()
        logger.addHandler(handler)

        log_success(logger, "Operation completed")

        output = stream.getvalue()
        self.assertIn("[✓]", output)
        self.assertIn("Operation completed", output)


class TestCompatibility(unittest.TestCase):
    """Test compatibility helpers for migration."""

    def test_migrate_prefix_info(self):
        """Verify [*] prefix removal."""
        self.assertEqual(migrate_prefix("[*] Processing file"), "Processing file")

    def test_migrate_prefix_warning(self):
        """Verify [!] prefix removal."""
        self.assertEqual(migrate_prefix("[!] Warning message"), "Warning message")

    def test_migrate_prefix_success(self):
        """Verify [✓] prefix removal."""
        self.assertEqual(migrate_prefix("[✓] Success message"), "Success message")

    def test_migrate_prefix_error(self):
        """Verify [✗] prefix removal."""
        self.assertEqual(migrate_prefix("[✗] Error message"), "Error message")

    def test_migrate_prefix_none(self):
        """Verify messages without prefixes pass through unchanged."""
        self.assertEqual(migrate_prefix("No prefix here"), "No prefix here")

    def test_detect_log_level_info(self):
        """Verify log level detection for [*]."""
        self.assertEqual(detect_log_level("[*] Message"), "INFO")

    def test_detect_log_level_warning(self):
        """Verify log level detection for [!]."""
        self.assertEqual(detect_log_level("[!] Message"), "WARNING")

    def test_detect_log_level_success(self):
        """Verify log level detection for [✓]."""
        self.assertEqual(detect_log_level("[✓] Message"), "SUCCESS")

    def test_detect_log_level_error(self):
        """Verify log level detection for [✗]."""
        self.assertEqual(detect_log_level("[✗] Message"), "ERROR")

    def test_detect_log_level_debug(self):
        """Verify log level detection for [·]."""
        self.assertEqual(detect_log_level("[·] Message"), "DEBUG")

    def test_detect_log_level_default(self):
        """Verify default log level for no prefix."""
        self.assertEqual(detect_log_level("Message"), "INFO")


if __name__ == "__main__":
    unittest.main()
