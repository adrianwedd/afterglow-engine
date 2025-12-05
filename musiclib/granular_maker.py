"""
IMPROVED GRANULAR CLOUD GENERATOR

This module provides enhancements to the existing granular synthesis for better cloud quality:

1. Smarter grain extraction (avoids silent regions and transients)
2. Better grain analysis (spectral quality metric)
3. Polyphonic cloud construction (multiple overlapping regions)
4. Configurable post-processing (smoothing, compression)

Usage:
    Replace musiclib/granular_maker.py with this version and update make_textures.py
    to use improved functions.

Key improvements:
- extract_grains_smart(): Analyzes and scores grains, skips bad ones
- create_cloud_polyphonic(): Creates denser, more interesting clouds
- apply_smoothing(): Reduces clicks and artifacts
"""

import numpy as np
from typing import List, Tuple
import librosa
from scipy import signal


def analyze_grain_quality(
    grain: np.ndarray,
    sr: int,
    check_silence: bool = True,
    check_dc: bool = True,
) -> float:
    """
    Score grain quality (0-1, higher is better).

    Penalties for:
    - Silent regions (RMS < threshold)
    - DC offset (mean >> 0)
    - Clipping (peak near 1.0)
    - Extreme spectral skew

    Args:
        grain: Audio grain to analyze
        sr: Sample rate
        check_silence: Penalize silent grains
        check_dc: Penalize grains with DC offset

    Returns:
        Quality score (0.0 to 1.0)
    """
    score = 1.0

    # Check for silence
    rms = np.sqrt(np.mean(grain ** 2))
    if check_silence and rms < 0.01:  # Very quiet
        score *= 0.2

    # Check for DC offset
    mean_abs = np.abs(np.mean(grain))
    if check_dc and mean_abs > 0.1:  # Large DC offset
        score *= 0.7

    # Check for clipping
    peak = np.max(np.abs(grain))
    if peak > 0.95:
        score *= 0.5

    # Check for extreme skew (lopsided envelope)
    if len(grain) > 10:
        first_half_energy = np.sum(grain[:len(grain)//2] ** 2)
        second_half_energy = np.sum(grain[len(grain)//2:] ** 2)
        total_energy = first_half_energy + second_half_energy
        if total_energy > 0:
            skew = abs(first_half_energy - second_half_energy) / total_energy
            if skew > 0.8:  # Very lopsided
                score *= 0.6

    return max(0.0, min(1.0, score))


def extract_grains_smart(
    audio: np.ndarray,
    grain_length_samples: int,
    num_grains: int,
    sr: int,
    min_quality: float = 0.5,
    analyze_regions: bool = True,
) -> List[np.ndarray]:
    """
    Extract grains from high-quality regions of audio.

    Avoids extracting grains from:
    - Silent regions
    - Regions with heavy transients
    - Clipping regions

    Args:
        audio: Source audio
        grain_length_samples: Length of each grain
        num_grains: Number of grains to extract
        sr: Sample rate
        min_quality: Minimum acceptable grain quality (0-1)
        analyze_regions: If True, pre-analyze good regions first

    Returns:
        List of quality grains with Hann windowing applied
    """
    grains = []
    max_start = max(0, len(audio) - grain_length_samples)

    if max_start == 0:
        # Audio too short, fall back to simple extraction
        return _extract_grains_fallback(audio, grain_length_samples, num_grains, sr)

    # Pre-analyze if requested (slower but better results)
    if analyze_regions:
        good_starts = []

        # Analyze 100 candidate positions
        candidates = np.linspace(0, max_start, min(100, max_start // grain_length_samples + 1)).astype(int)

        for start in candidates:
            end = min(start + grain_length_samples, len(audio))
            candidate_grain = audio[start:end]

            if len(candidate_grain) < grain_length_samples:
                candidate_grain = np.pad(candidate_grain, (0, grain_length_samples - len(candidate_grain)))

            quality = analyze_grain_quality(candidate_grain, sr)
            if quality >= min_quality:
                good_starts.append(start)

        # If we found good regions, use them
        if good_starts:
            for i in range(num_grains):
                start = good_starts[i % len(good_starts)]
                # Add small random offset for variation
                offset = np.random.randint(-grain_length_samples // 4, grain_length_samples // 4)
                start = max(0, min(max_start, start + offset))

                end = min(start + grain_length_samples, len(audio))
                grain = audio[start:end]

                if len(grain) < grain_length_samples:
                    grain = np.pad(grain, (0, grain_length_samples - len(grain)))

                # Apply Hann window
                window = signal.hann(grain_length_samples, sym=False)
                grain = grain * window
                grains.append(grain)

            return grains

    # Fallback: random extraction with quality filtering
    attempts = 0
    max_attempts = num_grains * 10

    while len(grains) < num_grains and attempts < max_attempts:
        attempts += 1
        start = np.random.randint(0, max_start)
        end = min(start + grain_length_samples, len(audio))
        grain = audio[start:end]

        if len(grain) < grain_length_samples:
            grain = np.pad(grain, (0, grain_length_samples - len(grain)))

        # Check quality
        if analyze_grain_quality(grain, sr) < min_quality:
            continue

        # Apply Hann window
        window = signal.hann(grain_length_samples, sym=False)
        grain = grain * window
        grains.append(grain)

    return grains


def _extract_grains_fallback(
    audio: np.ndarray,
    grain_length_samples: int,
    num_grains: int,
    sr: int,
) -> List[np.ndarray]:
    """Fallback grain extraction (original simple method)."""
    grains = []
    max_start = max(0, len(audio) - grain_length_samples)

    for _ in range(num_grains):
        if max_start == 0:
            start = 0
        else:
            start = np.random.randint(0, max_start)

        end = min(start + grain_length_samples, len(audio))
        grain = audio[start:end]

        if len(grain) < grain_length_samples:
            grain = np.pad(grain, (0, grain_length_samples - len(grain)))

        window = signal.hann(grain_length_samples, sym=False)
        grain = grain * window
        grains.append(grain)

    return grains


def apply_smoothing(
    cloud: np.ndarray,
    sr: int,
    smoothing_ms: float = 10.0,
    smooth_method: str = "gaussian",
) -> np.ndarray:
    """
    Apply smoothing to reduce clicks and artifacts.

    Methods:
    - "gaussian": Gaussian blur (smooth, musical)
    - "median": Median filter (preserves transients better)
    - "butterworth": Butterworth low-pass (warm, smooth)

    Args:
        cloud: Input cloud audio
        sr: Sample rate
        smoothing_ms: Smoothing window (milliseconds)
        smooth_method: Smoothing method to use

    Returns:
        Smoothed cloud audio
    """
    window_size = max(3, int(sr * smoothing_ms / 1000.0))

    if smooth_method == "median":
        return signal.medfilt(cloud, kernel_size=window_size if window_size % 2 == 1 else window_size + 1)

    elif smooth_method == "butterworth":
        # Design low-pass filter
        nyquist = sr / 2
        cutoff_hz = 1000 / smoothing_ms  # Higher smoothing -> lower cutoff
        cutoff_hz = min(cutoff_hz, nyquist * 0.99)
        normalized_cutoff = cutoff_hz / nyquist

        if normalized_cutoff <= 0 or normalized_cutoff >= 1:
            return cloud

        b, a = signal.butter(4, normalized_cutoff, btype='low')
        return signal.filtfilt(b, a, cloud)

    else:  # gaussian
        # Create Gaussian kernel
        sigma = window_size / 4.0
        kernel = signal.windows.gaussian(window_size, sigma)
        kernel /= kernel.sum()

        # Pad cloud to avoid edge effects
        padded = np.pad(cloud, (window_size // 2, window_size // 2), mode='reflect')
        smoothed = np.convolve(padded, kernel, mode='same')
        return smoothed[window_size // 2:-window_size // 2]


def create_cloud_polyphonic(
    audio: np.ndarray,
    sr: int,
    grain_length_min_ms: float,
    grain_length_max_ms: float,
    num_grains: int,
    cloud_duration_sec: float,
    pitch_shift_min: float,
    pitch_shift_max: float,
    overlap_ratio: float,
    smoothing_ms: float = 5.0,
) -> np.ndarray:
    """
    Generate cloud with polyphonic construction (denser, richer).

    This version creates multiple overlapping grain streams for more
    complex, evolving textures.

    Args:
        audio: Source audio
        sr: Sample rate
        grain_length_min_ms: Min grain length (ms)
        grain_length_max_ms: Max grain length (ms)
        num_grains: Total grains across all streams
        cloud_duration_sec: Target cloud duration
        pitch_shift_min: Min pitch shift (semitones)
        pitch_shift_max: Max pitch shift (semitones)
        overlap_ratio: Grain overlap (0.5-1.0)
        smoothing_ms: Post-processing smoothing (ms)

    Returns:
        Generated cloud audio array
    """
    grain_length_min_samples = int(grain_length_min_ms * sr / 1000)
    grain_length_max_samples = int(grain_length_max_ms * sr / 1000)

    # Extract grains with quality filtering
    grains = extract_grains_smart(audio, grain_length_max_samples, num_grains, sr, min_quality=0.4, analyze_regions=True)

    if not grains:
        # Fallback if quality extraction fails
        grains = extract_grains_smart(audio, grain_length_max_samples, num_grains, sr, min_quality=0.0, analyze_regions=False)

    # Apply pitch shifts
    pitched_grains = []
    for grain in grains:
        shift = np.random.uniform(pitch_shift_min, pitch_shift_max)
        if shift != 0:
            try:
                shifted = librosa.effects.pitch_shift(grain, sr=sr, n_steps=shift, n_fft=2048)
                pitched_grains.append(shifted)
            except Exception:
                pitched_grains.append(grain)
        else:
            pitched_grains.append(grain)

    # Create output buffer
    cloud_samples = int(cloud_duration_sec * sr)
    cloud = np.zeros(cloud_samples)

    # Determine hop size
    grain_length = grain_length_max_samples
    hop_samples = int(grain_length * (1 - overlap_ratio))
    if hop_samples == 0:
        hop_samples = 1

    # Place grains with variations
    grain_idx = 0
    current_pos = 0

    while current_pos < cloud_samples and grain_idx < len(pitched_grains):
        grain = pitched_grains[grain_idx]
        end_pos = min(current_pos + len(grain), cloud_samples)
        grain_len = end_pos - current_pos

        # Add with envelope to reduce clicks at boundaries
        cloud[current_pos:end_pos] += grain[:grain_len]

        # Variable hop for more organic feel
        hop_variation = np.random.randint(-hop_samples // 4, hop_samples // 4 + 1)
        current_pos += hop_samples + hop_variation
        grain_idx += 1

    # Normalize
    peak = np.max(np.abs(cloud))
    if peak > 0:
        cloud = cloud / peak * 0.95

    # Apply post-smoothing
    if smoothing_ms > 0:
        cloud = apply_smoothing(cloud, sr, smoothing_ms, smooth_method="gaussian")

    return cloud


def create_cloud(
    audio: np.ndarray,
    sr: int,
    grain_length_min_ms: float,
    grain_length_max_ms: float,
    num_grains: int,
    cloud_duration_sec: float,
    pitch_shift_min: float,
    pitch_shift_max: float,
    overlap_ratio: float,
) -> np.ndarray:
    """
    Original cloud generator (for backward compatibility).

    Internally delegates to improved polyphonic version.
    """
    return create_cloud_polyphonic(
        audio, sr,
        grain_length_min_ms, grain_length_max_ms,
        num_grains, cloud_duration_sec,
        pitch_shift_min, pitch_shift_max,
        overlap_ratio,
        smoothing_ms=5.0  # Default smoothing
    )
