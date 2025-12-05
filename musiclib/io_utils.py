"""
File I/O utilities: discovery, loading, saving, logging.
"""

import os
from pathlib import Path
from typing import List, Tuple
import librosa
import soundfile as sf
import numpy as np


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


def load_audio(filepath: str, sr: int = 44100, mono: bool = True) -> Tuple[np.ndarray, int]:
    """
    Load an audio file using librosa.

    Args:
        filepath: Path to audio file
        sr: Target sample rate (Hz)
        mono: Convert to mono if True

    Returns:
        (audio_data, sample_rate) tuple
    """
    try:
        y, sr_orig = librosa.load(filepath, sr=sr, mono=mono)
        return y, sr
    except Exception as e:
        print(f"  [!] Failed to load {filepath}: {e}")
        return None, None


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
    """
    # Validate bit depth before attempting save
    if bit_depth not in {16, 24}:
        print(f"  [!] Invalid bit_depth={bit_depth} for {filepath}. Use 16 or 24.")
        return False

    try:
        # Create parent directories if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Determine subtype based on bit depth
        if bit_depth == 16:
            subtype = 'PCM_16'
        else:  # bit_depth == 24
            subtype = 'PCM_24'

        sf.write(filepath, audio, sr, subtype=subtype)
        return True
    except Exception as e:
        print(f"  [!] Failed to save {filepath}: {e}")
        return False


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
    """Print a message (can be extended for logging)."""
    if verbose:
        print(message)
