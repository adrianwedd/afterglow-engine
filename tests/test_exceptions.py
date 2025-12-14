"""
Tests for the custom exception hierarchy.

Verifies exception creation, context preservation, and inheritance.
"""

import unittest

from musiclib.exceptions import (
    AfterglowError,
    AudioError,
    SilentArtifact,
    ClippedArtifact,
    ArchaeologyFailed,
    ConfigurationError,
    InvalidParameter,
    FilesystemError,
    DiskFullError,
    PermissionError,
    ProcessingError,
    STFTError,
    GrainExtractionError,
)


class TestAfterglowError(unittest.TestCase):
    """Test the base AfterglowError exception."""

    def test_creation_without_context(self):
        """Verify exception can be created without context."""
        error = AfterglowError("Something went wrong")
        self.assertEqual(error.message, "Something went wrong")
        self.assertEqual(error.context, {})

    def test_creation_with_context(self):
        """Verify exception can be created with context."""
        context = {"file_path": "/path/to/file.wav", "rms_db": -60.0}
        error = AfterglowError("Audio too quiet", context=context)

        self.assertEqual(error.message, "Audio too quiet")
        self.assertEqual(error.context, context)

    def test_string_representation_without_context(self):
        """Verify string representation without context."""
        error = AfterglowError("Error message")
        self.assertEqual(str(error), "Error message")

    def test_string_representation_with_context(self):
        """Verify string representation includes context."""
        error = AfterglowError(
            "Processing failed", context={"file": "test.wav", "duration": 3.5}
        )

        error_str = str(error)
        self.assertIn("Processing failed", error_str)
        self.assertIn("context:", error_str)
        self.assertIn("file=test.wav", error_str)
        self.assertIn("duration=3.5", error_str)


class TestExceptionHierarchy(unittest.TestCase):
    """Test the exception inheritance hierarchy."""

    def test_audio_error_inheritance(self):
        """Verify AudioError inherits from AfterglowError."""
        self.assertTrue(issubclass(AudioError, AfterglowError))

    def test_silent_artifact_inheritance(self):
        """Verify SilentArtifact inherits from AudioError."""
        self.assertTrue(issubclass(SilentArtifact, AudioError))
        self.assertTrue(issubclass(SilentArtifact, AfterglowError))

    def test_clipped_artifact_inheritance(self):
        """Verify ClippedArtifact inherits from AudioError."""
        self.assertTrue(issubclass(ClippedArtifact, AudioError))
        self.assertTrue(issubclass(ClippedArtifact, AfterglowError))

    def test_archaeology_failed_inheritance(self):
        """Verify ArchaeologyFailed inherits from AudioError."""
        self.assertTrue(issubclass(ArchaeologyFailed, AudioError))
        self.assertTrue(issubclass(ArchaeologyFailed, AfterglowError))

    def test_configuration_error_inheritance(self):
        """Verify ConfigurationError inherits from AfterglowError."""
        self.assertTrue(issubclass(ConfigurationError, AfterglowError))

    def test_invalid_parameter_inheritance(self):
        """Verify InvalidParameter inherits from ConfigurationError."""
        self.assertTrue(issubclass(InvalidParameter, ConfigurationError))
        self.assertTrue(issubclass(InvalidParameter, AfterglowError))

    def test_filesystem_error_inheritance(self):
        """Verify FilesystemError inherits from AfterglowError."""
        self.assertTrue(issubclass(FilesystemError, AfterglowError))

    def test_disk_full_error_inheritance(self):
        """Verify DiskFullError inherits from FilesystemError."""
        self.assertTrue(issubclass(DiskFullError, FilesystemError))
        self.assertTrue(issubclass(DiskFullError, AfterglowError))

    def test_permission_error_inheritance(self):
        """Verify PermissionError inherits from FilesystemError."""
        self.assertTrue(issubclass(PermissionError, FilesystemError))
        self.assertTrue(issubclass(PermissionError, AfterglowError))

    def test_processing_error_inheritance(self):
        """Verify ProcessingError inherits from AfterglowError."""
        self.assertTrue(issubclass(ProcessingError, AfterglowError))

    def test_stft_error_inheritance(self):
        """Verify STFTError inherits from ProcessingError."""
        self.assertTrue(issubclass(STFTError, ProcessingError))
        self.assertTrue(issubclass(STFTError, AfterglowError))

    def test_grain_extraction_error_inheritance(self):
        """Verify GrainExtractionError inherits from ProcessingError."""
        self.assertTrue(issubclass(GrainExtractionError, ProcessingError))
        self.assertTrue(issubclass(GrainExtractionError, AfterglowError))


class TestAudioErrors(unittest.TestCase):
    """Test audio-specific exceptions."""

    def test_silent_artifact_with_context(self):
        """Verify SilentArtifact preserves context."""
        context = {"peak": 1e-9, "rms_db": -80.0}
        error = SilentArtifact("Audio below noise floor", context=context)

        self.assertEqual(error.message, "Audio below noise floor")
        self.assertEqual(error.context["peak"], 1e-9)
        self.assertEqual(error.context["rms_db"], -80.0)

    def test_clipped_artifact_with_context(self):
        """Verify ClippedArtifact preserves context."""
        context = {"clipped_samples": 150, "total_samples": 44100}
        error = ClippedArtifact("Audio contains clipping", context=context)

        self.assertEqual(error.context["clipped_samples"], 150)

    def test_archaeology_failed_catchable(self):
        """Verify ArchaeologyFailed can be caught as AudioError."""
        with self.assertRaises(AudioError):
            raise ArchaeologyFailed("No stable regions found")


class TestConfigurationErrors(unittest.TestCase):
    """Test configuration-specific exceptions."""

    def test_invalid_parameter_with_context(self):
        """Verify InvalidParameter preserves context."""
        context = {"parameter": "grain_length_min_ms", "value": -5.0}
        error = InvalidParameter("Parameter must be positive", context=context)

        self.assertEqual(error.context["parameter"], "grain_length_min_ms")
        self.assertEqual(error.context["value"], -5.0)


class TestFilesystemErrors(unittest.TestCase):
    """Test filesystem-specific exceptions."""

    def test_disk_full_error_with_context(self):
        """Verify DiskFullError preserves context."""
        context = {"path": "/export/textures", "bytes_needed": 1024000}
        error = DiskFullError("Cannot write file", context=context)

        self.assertEqual(error.context["path"], "/export/textures")

    def test_permission_error_with_context(self):
        """Verify PermissionError preserves context."""
        context = {"path": "/restricted/file.wav", "operation": "write"}
        error = PermissionError("Access denied", context=context)

        self.assertEqual(error.context["operation"], "write")


class TestProcessingErrors(unittest.TestCase):
    """Test processing-specific exceptions."""

    def test_stft_error_with_context(self):
        """Verify STFTError preserves context."""
        context = {"audio_length": 0, "hop_length": 512}
        error = STFTError("Cannot compute STFT on empty array", context=context)

        self.assertEqual(error.context["audio_length"], 0)

    def test_grain_extraction_error_with_context(self):
        """Verify GrainExtractionError preserves context."""
        context = {"grains_found": 0, "min_required": 10}
        error = GrainExtractionError("Insufficient grains", context=context)

        self.assertEqual(error.context["grains_found"], 0)

    def test_processing_error_catchable(self):
        """Verify specific processing errors can be caught as ProcessingError."""
        with self.assertRaises(ProcessingError):
            raise STFTError("STFT computation failed")


class TestExceptionCatching(unittest.TestCase):
    """Test exception catching with hierarchy."""

    def test_catch_base_exception(self):
        """Verify all custom exceptions can be caught as AfterglowError."""
        exceptions_to_test = [
            SilentArtifact("test"),
            ClippedArtifact("test"),
            InvalidParameter("test"),
            DiskFullError("test"),
            STFTError("test"),
        ]

        for exc in exceptions_to_test:
            with self.assertRaises(AfterglowError):
                raise exc

    def test_catch_category_exception(self):
        """Verify exceptions can be caught by category."""
        # AudioError category
        with self.assertRaises(AudioError):
            raise SilentArtifact("test")

        # FilesystemError category
        with self.assertRaises(FilesystemError):
            raise DiskFullError("test")

        # ProcessingError category
        with self.assertRaises(ProcessingError):
            raise STFTError("test")


if __name__ == "__main__":
    unittest.main()
