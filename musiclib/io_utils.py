"""
File I/O utilities: discovery, loading, saving, logging.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
import librosa
import soundfile as sf
import numpy as np

from musiclib.logger import get_logger
from musiclib.exceptions import AudioError, FilesystemError, DiskFullError, PermissionError as AfterglowPermissionError

logger = get_logger(__name__)

SUPPORTED_AUDIO_FORMATS = {'.wav', '.aiff', '.aif', '.flac'}


def discover_audio_files(directory: str) -> List[str]:
    """
    Recursively discover audio files in a directory.

    Args:
        directory: Path to search

    Returns:
        List of absolute file paths for supported audio formats
    """
    if not os.path.isdir(directory):
        return []

    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in SUPPORTED_AUDIO_FORMATS:
                files.append(os.path.join(root, filename))

    return sorted(files)


def load_audio(filepath: str, sr: int = 44100, mono: bool = True) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """
    Load an audio file using librosa.

    Args:
        filepath: Path to audio file
        sr: Target sample rate (Hz)
        mono: Convert to mono if True

    Returns:
        (audio_data, sample_rate) tuple, or (None, None) on error

    Raises:
        AudioError: If file is corrupt or contains invalid data
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    try:
        y, sr_orig = librosa.load(filepath, sr=sr, mono=mono)

        # Validate loaded audio
        if y is None or len(y) == 0:
            raise AudioError(
                "Loaded audio is empty",
                context={"filepath": filepath, "sr": sr}
            )

        if np.any(np.isnan(y)):
            raise AudioError(
                "Audio contains NaN values",
                context={"filepath": filepath}
            )

        if np.any(np.isinf(y)):
            raise AudioError(
                "Audio contains infinite values",
                context={"filepath": filepath}
            )

        return y, sr

    except (FileNotFoundError, AudioError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.warning(f"Failed to load {filepath}: {e}")
        raise AudioError(
            "Could not load audio file",
            context={"filepath": filepath, "error": str(e)}
        )


def save_audio(
    filepath: str,
    audio: np.ndarray,
    sr: int = 44100,
    bit_depth: int = 24,
    subtype: str = 'PCM_24'
) -> bool:
    """
    Save audio to WAV file with specified bit depth.

    Args:
        filepath: Output path
        audio: Audio data (numpy array)
        sr: Sample rate (Hz)
        bit_depth: 16 or 24 for bit depth
        subtype: Soundfile subtype string

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If audio contains invalid data or bit_depth is invalid
        AfterglowPermissionError: If path is outside export root
        DiskFullError: If insufficient disk space
    """
    # Validate audio data
    if audio is None or audio.size == 0:
        logger.error("Cannot save empty audio array")
        raise ValueError("Cannot save empty audio array")

    if np.any(np.isnan(audio)):
        logger.error("Audio contains NaN values")
        raise ValueError("Audio contains NaN values")

    if np.any(np.isinf(audio)):
        logger.error("Audio contains infinite values")
        raise ValueError("Audio contains infinite values")

    # Validate bit depth
    if bit_depth not in {16, 24}:
        logger.error(f"Invalid bit_depth={bit_depth}. Use 16 or 24.")
        raise ValueError(f"Invalid bit_depth={bit_depth}. Use 16 or 24.")

    # Prevent accidental writes outside the export root
    export_root = Path(os.environ.get("AFTERGLOW_EXPORT_ROOT", "export")).resolve()
    abs_path = Path(filepath).resolve()

    try:
        if not abs_path.is_relative_to(export_root):
            logger.warning(f"Refusing to write outside export root ({export_root}): {abs_path}")
            raise AfterglowPermissionError(
                "Path is outside export root",
                context={"export_root": str(export_root), "requested_path": str(abs_path)}
            )
    except AttributeError:
        # Fallback for Python versions without is_relative_to
        abs_path_resolved = abs_path.resolve()
        export_root_resolved = export_root.resolve()
        if export_root_resolved not in abs_path_resolved.parents and abs_path_resolved != export_root_resolved:
            logger.warning(f"Refusing to write outside export root ({export_root_resolved}): {abs_path_resolved}")
            raise AfterglowPermissionError(
                "Path is outside export root",
                context={"export_root": str(export_root_resolved), "requested_path": str(abs_path_resolved)}
            )

    # Check disk space before writing
    # Estimate file size (conservative: 4 bytes per sample for 24-bit stereo)
    estimated_bytes = audio.size * 4
    try:
        stat = shutil.disk_usage(abs_path.parent if abs_path.parent.exists() else export_root)
        if stat.free < estimated_bytes * 1.1:  # 10% buffer
            logger.error(f"Insufficient disk space: {stat.free / 1024 / 1024:.1f} MB available, {estimated_bytes / 1024 / 1024:.1f} MB needed")
            raise DiskFullError(
                "Insufficient disk space",
                context={
                    "available_bytes": stat.free,
                    "needed_bytes": estimated_bytes,
                    "path": str(abs_path.parent)
                }
            )
    except OSError as e:
        logger.warning(f"Could not check disk space: {e}")

    try:
        # Create parent directories if needed
        os.makedirs(abs_path.parent, exist_ok=True)

        # Determine subtype based on bit depth
        if bit_depth == 16:
            subtype = 'PCM_16'
        else:  # bit_depth == 24
            subtype = 'PCM_24'

        # Write to the resolved path
        sf.write(str(abs_path), audio, sr, subtype=subtype)

        # Verify what was actually written
        info = sf.info(str(abs_path))
        actual_subtype = info.subtype
        if actual_subtype != subtype:
            logger.warning(f"Requested {subtype}, but file has {actual_subtype}: {str(abs_path)}")

        return True

    except OSError as e:
        if e.errno == 28:  # ENOSPC - No space left on device
            logger.error(f"Disk full while writing {str(abs_path)}")
            raise DiskFullError(
                "No space left on device",
                context={"filepath": str(abs_path), "error": str(e)}
            )
        elif e.errno == 13:  # EACCES - Permission denied
            logger.error(f"Permission denied: {str(abs_path)}")
            raise AfterglowPermissionError(
                "Permission denied",
                context={"filepath": str(abs_path), "error": str(e)}
            )
        else:
            logger.error(f"Failed to save {str(abs_path)}: {e}")
            raise FilesystemError(
                "Could not save audio file",
                context={"filepath": str(abs_path), "error": str(e)}
            )
    except Exception as e:
        logger.error(f"Unexpected error saving {str(abs_path)}: {e}")
        raise FilesystemError(
            "Unexpected error while saving",
            context={"filepath": str(abs_path), "error": str(e)}
        )


def get_filename_stem(filepath: str) -> str:
    """Extract filename without extension."""
    return Path(filepath).stem


def ensure_directory(directory: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)


def get_duration_seconds(audio: np.ndarray, sr: int) -> float:
    """Get duration of audio in seconds."""
    return len(audio) / sr


def log_message(message: str, verbose: bool = True) -> None:
    """
    Log a message (deprecated - use logger directly).

    This function is provided for backward compatibility.
    New code should use the logger from musiclib.logger directly.
    """
    if verbose:
        logger.info(message)
