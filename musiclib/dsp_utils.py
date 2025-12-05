"""
DSP utilities: filters, envelopes, windowing, normalization.
"""

import numpy as np
from scipy import signal
try:
    import librosa
except ImportError:
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
        except Exception:
            # If stdlib random is unavailable for some reason, skip without failing
            pass


def normalize_audio(audio: np.ndarray, target_peak_dbfs: float = -1.0) -> np.ndarray:
    """
    Normalize audio to a target peak level.

    Args:
        audio: Input audio array
        target_peak_dbfs: Target peak in dBFS (e.g., -1.0)

    Returns:
        Normalized audio array
    """
    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio

    target_linear = 10 ** (target_peak_dbfs / 20.0)
    return audio * (target_linear / peak)


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


def crossfade(audio1: np.ndarray, audio2: np.ndarray, fade_length: int) -> np.ndarray:
    """
    Crossfade between two audio signals.

    Args:
        audio1: First audio signal
        audio2: Second audio signal
        fade_length: Length of fade in samples

    Returns:
        Crossfaded audio
    """
    fade_out = np.linspace(1, 0, fade_length)
    fade_in = np.linspace(0, 1, fade_length)

    # Overlap-add the crossfade
    result = np.concatenate([audio1[:-fade_length], audio2[fade_length:]])
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
    """
    nyquist = sr / 2
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


def time_domain_crossfade_loop(audio: np.ndarray, crossfade_ms: float, sr: int) -> np.ndarray:
    """
    Make audio loopable by crossfading end to beginning.

    Args:
        audio: Input audio
        crossfade_ms: Crossfade duration in milliseconds
        sr: Sample rate

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

    fade_out = np.linspace(1, 0, crossfade_samples)
    fade_in = np.linspace(0, 1, crossfade_samples)

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
        audio = stereo_to_mono(audio)

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


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert stereo to mono (mean of channels).

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
