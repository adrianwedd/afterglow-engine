"""
DSP utilities: filters, envelopes, windowing, normalization.
"""

import numpy as np
from scipy import signal
import math
import sys

from musiclib.logger import get_logger
from musiclib.exceptions import SilentArtifact, AudioError

logger = get_logger(__name__)

try:
    import librosa
except ImportError:
    logger.warning("librosa not installed")
    logger.warning("  → Pitch shifting, BPM detection, key detection will be disabled")
    logger.warning("  → Install with: pip install librosa")
    librosa = None


# Global verbose flag for pre-analysis logging
_verbose = False


def set_verbose(verbose: bool):
    """Enable/disable verbose logging for pre-analysis."""
    global _verbose
    _verbose = verbose


def vprint(*args, **kwargs):
    """Print only if verbose mode is enabled."""
    global _verbose
    if _verbose:
        print(*args, **kwargs)


def set_random_seed(seed: int = None):
    """
    Set random seed for reproducible results.

    Call this before running the pipeline if you want deterministic output.

    Args:
        seed: Random seed (None for non-deterministic behavior)
    """
    if seed is not None:
        np.random.seed(seed)
        try:
            import random
            random.seed(seed)
        except ImportError:
            # If stdlib random is unavailable for some reason, skip without failing
            logger.debug("stdlib random module not available, skipping random.seed()")
            pass


def normalize_audio(audio: np.ndarray, target_peak_dbfs: float = -1.0) -> np.ndarray:
    """
    Normalize audio to a target peak level.

    Args:
        audio: Input audio array
        target_peak_dbfs: Target peak in dBFS (e.g., -1.0)

    Returns:
        Normalized audio array

    Raises:
        ValueError: If audio is empty or contains NaN/Inf values
        SilentArtifact: If audio is silent (peak < 1e-8)
    """
    # Validate input
    if audio.size == 0:
        raise ValueError("Cannot normalize empty audio array")

    if np.any(np.isnan(audio)):
        raise ValueError("Audio contains NaN values")

    if np.any(np.isinf(audio)):
        raise ValueError("Audio contains Inf values")

    peak = np.max(np.abs(audio))
    if peak < 1e-8:
        rms_db = rms_energy_db(audio)
        raise SilentArtifact(
            f"Cannot normalize silent audio (peak={peak:.2e}). "
            f"Audio is likely below noise floor or all zeros.",
            context={"peak": peak, "rms_db": rms_db}
        )

    target_linear = 10 ** (target_peak_dbfs / 20.0)
    normalized = audio * (target_linear / peak)

    # Clip to [-1, 1] range to prevent overflow
    return np.clip(normalized, -1.0, 1.0)


def linear_to_db(linear: float, min_db: float = -80.0) -> float:
    """Convert linear amplitude to dB."""
    if linear <= 0:
        return min_db
    return 20 * np.log10(linear)


def db_to_linear(db: float) -> float:
    """Convert dB to linear amplitude."""
    return 10 ** (db / 20.0)


def rms_energy(audio: np.ndarray) -> float:
    """Calculate RMS (root mean square) energy."""
    return np.sqrt(np.mean(audio ** 2))


def rms_energy_db(audio: np.ndarray, min_db: float = -80.0) -> float:
    """Calculate RMS energy in dB."""
    rms = rms_energy(audio)
    return linear_to_db(rms, min_db)


def hann_window(length: int) -> np.ndarray:
    """Create a Hann window."""
    return signal.windows.hann(length, sym=False)


def _spectral_centroid(audio: np.ndarray, sr: int) -> float:
    """Compute spectral centroid using librosa if available, else FFT."""
    if len(audio) == 0:
        return 0.0
    try:
        if librosa is not None:
            return float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))
    except Exception as e:
        # Fall back to FFT if librosa fails (e.g., due to invalid audio)
        logger.debug(f"librosa spectral_centroid failed, using FFT fallback: {e}")

    # FFT-based fallback
    fft = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    mag = np.abs(fft)
    if np.sum(mag) == 0:
        return 0.0
    return float(np.sum(freqs * mag) / np.sum(mag))


def estimate_pitch_hz(audio: np.ndarray, sr: int, fmin: float = 30.0, fmax: float = 6000.0) -> float or None:
    """Rough pitch estimate via dominant FFT bin."""
    if len(audio) == 0:
        return None
    # If stereo/stacked, collapse to mono for robust FFT sizing
    if audio.ndim > 1:
        audio = np.mean(audio, axis=0)
    audio = audio - np.mean(audio)
    if np.max(np.abs(audio)) < 1e-4:
        return None
    fft = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    mag = np.abs(fft)
    peak_idx = np.argmax(mag)
    peak_freq = freqs[peak_idx]
    if peak_freq < fmin or peak_freq > fmax:
        return None
    return float(peak_freq)


def compute_audio_metadata(
    audio: np.ndarray,
    sr: int,
    *,
    brightness_bounds=None,
    kind: str = None,
    source: str = None,
    filename: str = None,
    detected_key: str = None,
    detected_bpm: float = None,
) -> dict:
    """
    Compute lightweight metadata for an audio buffer.

    Returns: filename, source, type, duration_sec, rms_db, peak, crest_factor,
    centroid_hz, est_freq_hz, loop_error_db, brightness, detected_key, detected_bpm
    """
    duration_sec = len(audio) / sr if sr else 0.0
    rms = rms_energy(audio)
    rms_db = rms_energy_db(audio)
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    crest = float(peak / rms) if rms > 1e-9 else math.inf
    centroid = _spectral_centroid(audio, sr)
    est_freq = estimate_pitch_hz(audio, sr) if kind in ("pad", "drone", "swell") else None
    seam_len = min(len(audio) // 8, 2048)
    loop_error_db = None
    if seam_len > 0:
        head = audio[:seam_len]
        tail = audio[-seam_len:]
        diff_rms = rms_energy(head - tail)
        loop_error_db = 20 * np.log10(diff_rms + 1e-12)

    brightness_tag = None
    if brightness_bounds is not None:
        low, high = brightness_bounds
        brightness_tag = classify_brightness(audio, sr, low, high)

    return {
        "filename": filename,
        "source": source,
        "type": kind,
        "duration_sec": duration_sec,
        "rms_db": rms_db,
        "peak": peak,
        "crest_factor": crest,
        "centroid_hz": centroid,
        "est_freq_hz": est_freq,
        "loop_error_db": loop_error_db,
        "brightness": brightness_tag,
        "detected_key": detected_key,
        "detected_bpm": detected_bpm,
    }


def grade_audio(metadata: dict, thresholds: dict) -> str:
    """
    Simple grading: F if below minima or clipping; A if well within bounds; else B.
    thresholds keys: min_rms_db, clipping_tolerance, max_crest_factor.
    """
    min_rms = thresholds.get("min_rms_db", -60.0)
    clip_tol = thresholds.get("clipping_tolerance", 0.0)
    max_crest = thresholds.get("max_crest_factor", 30.0)

    rms_db = metadata.get("rms_db", -120.0)
    peak = metadata.get("peak", 0.0)
    crest = metadata.get("crest_factor", math.inf)
    loop_err = metadata.get("loop_error_db")

    if rms_db < min_rms or peak >= (1.0 - clip_tol) or crest > max_crest:
        return "F"

    if rms_db > min_rms + 15 and crest < max_crest * 0.6:
        if loop_err is None or loop_err < -30:
            return "A"

    return "B"


def crossfade(audio1: np.ndarray, audio2: np.ndarray, fade_length: int, equal_power: bool = True) -> np.ndarray:
    """
    Crossfade between two audio signals.

    Args:
        audio1: First audio signal
        audio2: Second audio signal
        fade_length: Length of fade in samples
        equal_power: If True, use equal-power (sqrt) curves to maintain perceived loudness.
                     If False, use linear fades.

    Returns:
        Crossfaded audio
    """
    t = np.linspace(0, 1, fade_length)

    if equal_power:
        # Equal-power crossfade maintains constant perceived loudness
        fade_out = np.sqrt(1 - t)  # Convex curve
        fade_in = np.sqrt(t)        # Convex curve
    else:
        # Linear crossfade
        fade_out = 1 - t
        fade_in = t

    # Overlap-add the crossfade
    overlap_region = (audio1[-fade_length:] * fade_out + audio2[:fade_length] * fade_in)
    result = np.concatenate([audio1[:-fade_length], overlap_region, audio2[fade_length:]])
    return result


def apply_fade_in(audio: np.ndarray, fade_length: int) -> np.ndarray:
    """Apply fade-in envelope."""
    if fade_length > len(audio):
        fade_length = len(audio)
    fade = np.linspace(0, 1, fade_length)
    audio_out = audio.copy()
    audio_out[:fade_length] *= fade
    return audio_out


def apply_fade_out(audio: np.ndarray, fade_length: int) -> np.ndarray:
    """Apply fade-out envelope."""
    if fade_length > len(audio):
        fade_length = len(audio)
    fade = np.linspace(1, 0, fade_length)
    audio_out = audio.copy()
    audio_out[-fade_length:] *= fade
    return audio_out


def apply_hann_window_edge(audio: np.ndarray, window_length: int) -> np.ndarray:
    """Apply Hann window at start and end of audio."""
    if window_length > len(audio) // 2:
        window_length = len(audio) // 2

    window = hann_window(window_length * 2)
    audio_out = audio.copy()
    audio_out[:window_length] *= window[:window_length]
    audio_out[-window_length:] *= window[window_length:]
    return audio_out


def design_butterworth_lowpass(cutoff_hz: float, sr: int, order: int = 5) -> tuple:
    """
    Design a Butterworth low-pass filter.

    Args:
        cutoff_hz: Cutoff frequency in Hz
        sr: Sample rate in Hz
        order: Filter order

    Returns:
        (b, a) coefficients for scipy.signal.filtfilt
    """
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist
    if normalized_cutoff >= 1.0:
        normalized_cutoff = 0.99
    b, a = signal.butter(order, normalized_cutoff, btype='low')
    return b, a


def design_butterworth_highpass(cutoff_hz: float, sr: int, order: int = 5) -> tuple:
    """
    Design a Butterworth high-pass filter.

    Args:
        cutoff_hz: Cutoff frequency in Hz
        sr: Sample rate in Hz
        order: Filter order

    Returns:
        (b, a) coefficients for scipy.signal.filtfilt
    """
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist
    if normalized_cutoff >= 0.99:
        normalized_cutoff = 0.99
    if normalized_cutoff <= 0.01:
        normalized_cutoff = 0.01
    b, a = signal.butter(order, normalized_cutoff, btype='high')
    return b, a


def design_butterworth_bandpass(
    low_hz: float, high_hz: float, sr: int, order: int = 5
) -> tuple:
    """
    Design a Butterworth band-pass filter.

    Args:
        low_hz: Low cutoff frequency in Hz
        high_hz: High cutoff frequency in Hz
        sr: Sample rate in Hz
        order: Filter order

    Returns:
        (b, a) coefficients for scipy.signal.filtfilt

    Raises:
        ValueError: If frequencies or sample rate are invalid
    """
    # Validate parameters
    if sr <= 0:
        raise ValueError(f"Sample rate must be positive, got {sr}")

    if low_hz < 0:
        raise ValueError(f"Low frequency must be non-negative, got {low_hz}")

    if high_hz < 0:
        raise ValueError(f"High frequency must be non-negative, got {high_hz}")

    if low_hz >= high_hz:
        raise ValueError(f"Low frequency ({low_hz}) must be less than high frequency ({high_hz})")

    nyquist = sr / 2
    if high_hz >= nyquist:
        raise ValueError(f"High frequency ({high_hz}) must be less than Nyquist frequency ({nyquist})")

    low_norm = low_hz / nyquist
    high_norm = high_hz / nyquist
    low_norm = np.clip(low_norm, 0.01, 0.99)
    high_norm = np.clip(high_norm, 0.01, 0.99)
    b, a = signal.butter(order, [low_norm, high_norm], btype='band')
    return b, a


def apply_filter(audio: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """
    Apply IIR filter using filtfilt (zero-phase).

    Args:
        audio: Input audio
        b, a: Filter coefficients

    Returns:
        Filtered audio
    """
    min_len = 3 * max(len(a), len(b))
    if len(audio) < min_len:
        # Too short for filtfilt stability; return unfiltered audio
        # to avoid crashes on tiny hiss/flicker segments.
        return audio
    return signal.filtfilt(b, a, audio)


def apply_tremolo(audio: np.ndarray, rate_hz: float, depth: float, sr: int) -> np.ndarray:
    """
    Apply tremolo (amplitude modulation).

    Args:
        audio: Input audio
        rate_hz: Modulation rate in Hz
        depth: Modulation depth (0-1)
        sr: Sample rate in Hz

    Returns:
        Audio with tremolo applied
    """
    n_samples = len(audio)
    t = np.arange(n_samples) / sr
    # Sine wave modulation: depth controls how much it oscillates
    modulation = 1.0 - depth * 0.5 + depth * 0.5 * np.sin(2 * np.pi * rate_hz * t)
    return audio * modulation


def apply_simple_reverb(audio: np.ndarray, decay: float = 0.5, delay_ms: float = 50.0, sr: int = 44100) -> np.ndarray:
    """
    Apply a simple delay-based reverb.

    Args:
        audio: Input audio
        decay: Decay factor (0-1)
        delay_ms: Delay time in milliseconds
        sr: Sample rate

    Returns:
        Reverb-processed audio
    """
    delay_samples = int(delay_ms * sr / 1000)
    if delay_samples > len(audio):
        return audio

    output = audio.copy()
    delayed = np.zeros_like(audio)
    delayed[delay_samples:] = audio[:-delay_samples] * decay
    output += delayed
    return output


def find_best_loop_trim(audio: np.ndarray, fade_length: int, search_window: int = None) -> int:
    """
    Find the optimal number of samples to trim from the end to align phase.

    Uses cross-correlation to match the end of the audio with the start.

    Args:
        audio: Input audio array
        fade_length: Length of the crossfade (reference size)
        search_window: How many samples at the end to search (default: 4 * fade_length)

    Returns:
        Number of samples to trim from the end.
    """
    # Ensure mono to avoid accidental multi-channel correlation oddities
    if audio.ndim > 1:
        audio = ensure_mono(audio)

    if search_window is None:
        search_window = 4 * fade_length

    # Ensure search window is valid
    if search_window > len(audio):
        search_window = len(audio)
    if search_window < fade_length:
        return 0

    # Reference: the start of the loop (we want the end to flow into this)
    ref = audio[:fade_length]
    ref = ref - np.mean(ref)
    
    # Search region: the end of the file
    # We want to find where 'ref' occurs best in the 'search_region'
    # The search region effectively represents the 'predecessor' to the loop start.
    search_region = audio[-search_window:]
    search_region = search_region - np.mean(search_region)

    # Correlate
    # Mode 'valid' returns correlations where the signals fully overlap
    corr = signal.correlate(search_region, ref, mode='valid')
    
    if len(corr) == 0:
        return 0

    # Find best match index
    # We prefer the match closest to the end of the file (smallest trim).
    # np.argmax returns the *first* occurrence. 
    # By reversing, finding argmax, and adjusting, we get the *last* occurrence.
    best_offset = len(corr) - 1 - np.argmax(corr[::-1])
    
    # Calculate trim
    # best_offset is the index in search_region where the match starts.
    # We want the file to end exactly where this match starts + fade_length.
    # So we keep (best_offset + fade_length) samples from the search region.
    samples_to_keep_in_search = best_offset + fade_length
    trim_amount = len(search_region) - samples_to_keep_in_search
    
    # Safety cap: never trim more than a quarter of the file
    trim_amount = max(0, trim_amount)
    trim_amount = min(trim_amount, len(audio) // 4)
    return trim_amount


def time_domain_crossfade_loop(
    audio: np.ndarray, crossfade_ms: float, sr: int, optimize_loop: bool = True, equal_power: bool = True
) -> np.ndarray:
    """
    Make audio loopable by crossfading end to beginning.

    Args:
        audio: Input audio
        crossfade_ms: Crossfade duration in milliseconds
        sr: Sample rate
        optimize_loop: If True, search for optimal phase alignment before crossfading.
        equal_power: If True, use equal-power (sqrt) fades for constant perceived loudness.
                     If False, use linear fades.

    Returns:
        Audio with smoothed loop point
    """
    crossfade_samples = int(crossfade_ms * sr / 1000)

    # Guard against zero or very small crossfades
    if crossfade_samples < 1:
        return audio.copy()

    # Clamp crossfade to half the audio length
    if crossfade_samples > len(audio) // 2:
        crossfade_samples = len(audio) // 2

    # Optimization: align phase
    if optimize_loop:
        # Search a reasonable window (e.g., up to 200ms or 2x fade)
        # If we search too far, we might change the musical timing significantly.
        # Let's default to searching ~4x the fade length or max 500ms.
        search_limit = min(len(audio) // 2, max(crossfade_samples * 4, int(0.5 * sr)))
        trim = find_best_loop_trim(audio, crossfade_samples, search_window=search_limit)
        if trim > 0:
            audio = audio[:-trim]

    t = np.linspace(0, 1, crossfade_samples)

    if equal_power:
        # Equal-power crossfade maintains constant perceived loudness
        fade_out = np.sqrt(1 - t)  # Convex curve
        fade_in = np.sqrt(t)        # Convex curve
    else:
        # Linear crossfade
        fade_out = 1 - t
        fade_in = t

    # Crossfade: end of audio fades out, beginning fades in
    audio_out = audio.copy()
    audio_out[-crossfade_samples:] *= fade_out
    audio_out[:crossfade_samples] *= fade_in

    # Add the faded-out end to the faded-in beginning (overlap-add)
    audio_out[:crossfade_samples] += audio[-crossfade_samples:] * fade_out

    return audio_out


def classify_brightness(audio: np.ndarray, sr: int, centroid_low_hz: float = 1500, centroid_high_hz: float = 3500) -> str:
    """
    Classify audio brightness (dark/mid/bright) based on spectral centroid.

    Args:
        audio: Input audio array
        sr: Sample rate
        centroid_low_hz: Threshold between dark and mid
        centroid_high_hz: Threshold between mid and bright

    Returns:
        One of: "dark", "mid", "bright"
    """
    # Ensure mono for consistent centroid measurement
    if audio.ndim > 1:
        audio = ensure_mono(audio)

    if librosa is None:
        # Fallback if librosa not available: compute simple spectral centroid
        # using FFT-based approach
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1 / sr)
        magnitudes = np.abs(fft)
        if np.sum(magnitudes) == 0:
            return "mid"
        centroid = np.sum(freqs * magnitudes) / np.sum(magnitudes)
    else:
        # Use librosa's spectral centroid
        centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))

    if centroid < centroid_low_hz:
        return "dark"
    elif centroid > centroid_high_hz:
        return "bright"
    else:
        return "mid"


def ensure_mono(audio: np.ndarray, method: str = "average") -> np.ndarray:
    """
    Normalize audio to mono (samples,) regardless of input convention.

    Handles both librosa convention (2, samples) and soundfile convention (samples, 2).

    Args:
        audio: Input audio in any format:
               - (samples,) -> mono, returned as-is
               - (2, samples) -> stereo (librosa), converted to mono
               - (samples, 2) -> stereo (soundfile), converted to mono
        method: Conversion method for stereo to mono:
                - "average": Mean of channels (default, safest for normalization)
                - "sum": Sum channels then divide by √2 (approx constant power)
                - "left": Use left channel only
                - "right": Use right channel only

    Returns:
        Mono audio (samples,)

    Raises:
        ValueError: If audio has unexpected shape or invalid method
    """
    if audio.ndim == 1:
        return audio
    elif audio.ndim == 2:
        if audio.shape[0] == 2:  # librosa convention: (2, samples)
            if method == "average":
                return np.mean(audio, axis=0)
            elif method == "sum":
                return np.sum(audio, axis=0) / np.sqrt(2.0)  # Normalize power
            elif method == "left":
                return audio[0]
            elif method == "right":
                return audio[1]
            else:
                raise ValueError(f"Unknown stereo conversion method: {method}")
        elif audio.shape[1] == 2:  # soundfile convention: (samples, 2)
            if method == "average":
                return np.mean(audio, axis=1)
            elif method == "sum":
                return np.sum(audio, axis=1) / np.sqrt(2.0)  # Normalize power
            elif method == "left":
                return audio[:, 0]
            elif method == "right":
                return audio[:, 1]
            else:
                raise ValueError(f"Unknown stereo conversion method: {method}")
        else:
            raise ValueError(
                f"Unexpected stereo shape: {audio.shape}. "
                f"Expected (2, N) or (N, 2) for stereo."
            )
    else:
        raise ValueError(
            f"Cannot convert {audio.ndim}D array to mono. "
            f"Expected 1D or 2D audio."
        )


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert stereo to mono (mean of channels).

    DEPRECATED: Use ensure_mono() for better shape handling.

    Args:
        audio: Input audio (channels, samples) or (samples,)

    Returns:
        Mono audio (samples,)
    """
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=0)


def mono_to_stereo(audio: np.ndarray) -> np.ndarray:
    """
    Convert mono to stereo (duplicate to both channels).

    Args:
        audio: Mono audio (samples,)

    Returns:
        Stereo audio (2, samples)
    """
    if audio.ndim == 2:
        return audio
    # SoundFile expects (samples, channels)
    return np.column_stack((audio, audio))
