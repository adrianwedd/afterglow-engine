"""
Lightweight musical analysis helpers: key and tempo detection.
"""
from typing import Optional, Tuple
import numpy as np

try:
    import librosa
except ImportError:
    librosa = None


MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key(audio: np.ndarray, sr: int) -> Optional[str]:
    """
    Detect key using chroma and Krumhansl-Schmuckler profiles.

    Returns "C maj", "A min", or None on failure.
    """
    if librosa is None or len(audio) == 0:
        return None
    try:
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        # Normalize
        chroma_norm = chroma_mean / np.linalg.norm(chroma_mean) if np.linalg.norm(chroma_mean) > 0 else chroma_mean
        # Correlate with all rotations of profiles
        best = None
        for i in range(12):
            maj_score = np.dot(chroma_norm, np.roll(MAJOR_PROFILE, i))
            min_score = np.dot(chroma_norm, np.roll(MINOR_PROFILE, i))
            if best is None or maj_score > best[1]:
                best = (f"{NOTE_NAMES[i]} maj", maj_score)
            if min_score > best[1]:
                best = (f"{NOTE_NAMES[i]} min", min_score)
        return best[0] if best else None
    except Exception:
        return None


def detect_bpm(audio: np.ndarray, sr: int) -> Tuple[Optional[float], float]:
    """
    Detect BPM using librosa beat tracking. Returns (bpm, confidence 0-1).
    """
    if librosa is None or len(audio) == 0:
        return (None, 0.0)
    try:
        tempo, beats = librosa.beat.beat_track(y=audio, sr=sr, units="time")
        # Confidence heuristic: beat count vs duration
        duration = len(audio) / sr
        beat_rate = len(beats) / duration if duration > 0 else 0
        # Normalize confidence: 0 beats/sec -> 0, 4 beats/sec -> ~1 (capped)
        confidence = min(1.0, beat_rate / 4.0)
        return (float(tempo), confidence)
    except Exception:
        return (None, 0.0)


def get_transposition_interval(source_key: str, target_key: str) -> int:
    """
    Calculate shortest transposition in semitones from source to target.
    e.g., C maj -> G maj = -5 or +7 (returns -5)
    """
    # Simple mapping map
    semitones = {
        "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, 
        "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, 
        "A": 9, "A#": 10, "BB": 10, "B": 11
    }
    
    def parse_root(k):
        # extract root part "C#" from "C# maj"
        parts = k.split()
        root = parts[0].upper()
        return semitones.get(root, 0)

    try:
        src_val = parse_root(source_key)
        tgt_val = parse_root(target_key)
        
        diff = tgt_val - src_val
        # Wrap to -6 to +6 range for shortest path
        while diff > 6:
            diff -= 12
        while diff < -6:
            diff += 12
        return diff
    except Exception:
        return 0
