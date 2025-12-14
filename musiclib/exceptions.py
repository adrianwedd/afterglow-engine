"""
Custom exception hierarchy for afterglow-engine.

Maintains the philosophical tone of "sonic archaeology" while providing
structured error handling with context preservation.
"""

from typing import Dict, Any, Optional


class AfterglowError(Exception):
    """
    Base exception for all afterglow-engine errors.

    The machine speaks when the archaeology falters.
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize exception with message and optional context.

        Args:
            message: Human-readable error description
            context: Additional diagnostic information (file paths, values, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Format exception with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


# Audio Processing Errors

class AudioError(AfterglowError):
    """Base class for audio-related errors."""
    pass


class SilentArtifact(AudioError):
    """
    Raised when audio is below the noise floor.

    The machine cannot mine what does not resonate.
    """
    pass


class ClippedArtifact(AudioError):
    """
    Raised when audio contains clipping distortion.

    The pigment has been burned; the texture is scorched.
    """
    pass


class ArchaeologyFailed(AudioError):
    """
    Raised when the excavation yields no usable material.

    The dig found no stable ground, no sustained surface.
    """
    pass


# Configuration Errors

class ConfigurationError(AfterglowError):
    """Base class for configuration-related errors."""
    pass


class InvalidParameter(ConfigurationError):
    """
    Raised when configuration contains invalid parameters.

    The machine cannot calibrate to contradictory instructions.
    """
    pass


# Filesystem Errors

class FilesystemError(AfterglowError):
    """Base class for filesystem-related errors."""
    pass


class DiskFullError(FilesystemError):
    """
    Raised when the disk is full.

    The archive has no more room; the excavation cannot continue.
    """
    pass


class PermissionError(FilesystemError):
    """
    Raised when filesystem permissions prevent operation.

    The machine is denied access to the excavation site.
    """
    pass


# Processing Errors

class ProcessingError(AfterglowError):
    """Base class for signal processing errors."""
    pass


class STFTError(ProcessingError):
    """
    Raised when Short-Time Fourier Transform computation fails.

    The spectral lens could not be focused on the signal.
    """
    pass


class GrainExtractionError(ProcessingError):
    """
    Raised when grain extraction or synthesis fails.

    The grains could not be sifted from the source material.
    """
    pass
