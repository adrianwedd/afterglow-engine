"""
Granular cloud generator: create abstract, evolving textures from audio.
"""

from typing import List, Tuple
import numpy as np
import librosa
from . import io_utils, dsp_utils


def extract_grains(
    audio: np.ndarray,
    grain_length_samples: int,
    num_grains: int,
    sr: int,
) -> List[np.ndarray]:
    """
    Extract random grains from audio with Hann windowing.

    Args:
        audio: Input audio
        grain_length_samples: Length of each grain in samples
        num_grains: Number of grains to extract
        sr: Sample rate

    Returns:
        List of windowed grain audio arrays
    """
    grains = []
    max_start = max(0, len(audio) - grain_length_samples)

    for _ in range(num_grains):
        if max_start == 0:
            start = 0
        else:
            start = np.random.randint(0, max_start)

        end = min(start + grain_length_samples, len(audio))
        grain = audio[start:end]

        # Pad if necessary
        if len(grain) < grain_length_samples:
            grain = np.pad(grain, (0, grain_length_samples - len(grain)))

        # Apply Hann window
        window = dsp_utils.hann_window(grain_length_samples)
        grain = grain * window

        grains.append(grain)

    return grains


def apply_pitch_shift_grain(
    grain: np.ndarray,
    sr: int,
    min_shift_semitones: float,
    max_shift_semitones: float,
) -> np.ndarray:
    """
    Apply random pitch shift to a grain within a range.

    Args:
        grain: Input grain
        sr: Sample rate
        min_shift_semitones: Minimum pitch shift (negative = lower)
        max_shift_semitones: Maximum pitch shift (positive = higher)

    Returns:
        Pitch-shifted grain
    """
    if min_shift_semitones == 0 and max_shift_semitones == 0:
        return grain

    shift = np.random.uniform(min_shift_semitones, max_shift_semitones)
    return librosa.effects.pitch_shift(grain, sr=sr, n_steps=shift)


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
    Generate a granular cloud texture from audio.

    Args:
        audio: Source audio
        sr: Sample rate
        grain_length_min_ms: Minimum grain length in milliseconds
        grain_length_max_ms: Maximum grain length in milliseconds
        num_grains: Number of grains to generate
        cloud_duration_sec: Target cloud duration
        pitch_shift_min: Minimum pitch shift in semitones (negative = lower)
        pitch_shift_max: Maximum pitch shift in semitones (positive = higher)
        overlap_ratio: Grain overlap ratio (0.5-1.0)

    Returns:
        Generated cloud audio array
    """
    grain_length_min_samples = int(grain_length_min_ms * sr / 1000)
    grain_length_max_samples = int(grain_length_max_ms * sr / 1000)
    grain_length_samples = np.random.randint(
        grain_length_min_samples, grain_length_max_samples + 1
    )

    # Extract grains
    grains = extract_grains(audio, grain_length_samples, num_grains, sr)

    # Apply pitch shifts
    grains = [
        apply_pitch_shift_grain(g, sr, pitch_shift_min, pitch_shift_max)
        for g in grains
    ]

    # Create output buffer
    cloud_samples = int(cloud_duration_sec * sr)
    cloud = np.zeros(cloud_samples)

    # Place grains with overlap
    hop_samples = int(grain_length_samples * (1 - overlap_ratio))
    if hop_samples == 0:
        hop_samples = 1

    grain_idx = 0
    current_pos = 0

    while current_pos < cloud_samples and grain_idx < len(grains):
        grain = grains[grain_idx]
        end_pos = min(current_pos + len(grain), cloud_samples)
        grain_len = end_pos - current_pos

        cloud[current_pos:end_pos] += grain[:grain_len]
        current_pos += hop_samples
        grain_idx += 1

    # Normalize and prevent clipping
    peak = np.max(np.abs(cloud))
    if peak > 0:
        cloud = cloud / peak * 0.95

    return cloud


def apply_cloud_filtering(
    cloud: np.ndarray,
    sr: int,
    lowpass_hz: float = None,
) -> np.ndarray:
    """
    Apply optional filtering to soften cloud texture.

    Args:
        cloud: Input cloud audio
        sr: Sample rate
        lowpass_hz: Low-pass cutoff frequency (optional)

    Returns:
        Filtered cloud audio
    """
    if lowpass_hz and lowpass_hz > 0:
        b, a = dsp_utils.design_butterworth_lowpass(lowpass_hz, sr, order=3)
        cloud = dsp_utils.apply_filter(cloud, b, a)

    return cloud


def make_clouds_from_source(
    audio: np.ndarray,
    sr: int,
    stem_name: str,
    config: dict,
    source_index: int = 1,
) -> List[Tuple[np.ndarray, str]]:
    """
    Create multiple cloud variations from a source audio.

    Args:
        audio: Source audio
        sr: Sample rate
        stem_name: Source name for filename
        config: Configuration dictionary
        source_index: Source index for naming

    Returns:
        List of (cloud_audio, brightness_tag) tuples
    """
    cloud_config = config['clouds']
    peak_dbfs = config['global']['target_peak_dbfs']

    # Brightness tagging
    brightness_config = config.get('brightness_tags', {})
    enable_brightness = brightness_config.get('enabled', True)
    centroid_low = brightness_config.get('centroid_low_hz', 1500)
    centroid_high = brightness_config.get('centroid_high_hz', 3500)

    # Export config
    export_config = config.get('export', {})
    clouds_stereo = export_config.get('clouds_stereo', False)

    # Pitch shift range (new config format with fallback)
    pitch_range = cloud_config.get('pitch_shift_range')
    if pitch_range and isinstance(pitch_range, dict):
        pitch_min = pitch_range.get('min', -8)
        pitch_max = pitch_range.get('max', 8)
    else:
        # Fallback to old single value format
        old_max_shift = cloud_config.get('max_pitch_shift_semitones', 7)
        pitch_min = -old_max_shift
        pitch_max = old_max_shift

    clouds_per_source = cloud_config['clouds_per_source']
    results = []

    for i in range(clouds_per_source):
        cloud = create_cloud(
            audio,
            sr=sr,
            grain_length_min_ms=cloud_config['grain_length_min_ms'],
            grain_length_max_ms=cloud_config['grain_length_max_ms'],
            num_grains=cloud_config['grains_per_cloud'],
            cloud_duration_sec=cloud_config['cloud_duration_sec'],
            pitch_shift_min=pitch_min,
            pitch_shift_max=pitch_max,
            overlap_ratio=cloud_config['overlap_ratio'],
        )

        # Apply filtering
        cloud = apply_cloud_filtering(
            cloud, sr, lowpass_hz=cloud_config.get('lowpass_hz')
        )

        # Normalize
        cloud = dsp_utils.normalize_audio(cloud, peak_dbfs)

        # Convert to stereo if requested
        if clouds_stereo:
            cloud = dsp_utils.mono_to_stereo(cloud)

        # Classify brightness
        brightness_tag = ""
        if enable_brightness:
            brightness_tag = dsp_utils.classify_brightness(cloud, sr, centroid_low, centroid_high)

        filename = f"cloud_{stem_name}_{i + 1:02d}.wav"
        results.append((cloud, brightness_tag, filename))

    return results


def process_cloud_sources(config: dict) -> dict:
    """
    Process all audio files in pad_sources directory to create clouds.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_name: [(cloud_audio, filename), ...]}
    """
    sr = config['global']['sample_rate']
    pad_sources_dir = config['paths']['pad_sources_dir']
    files = io_utils.discover_audio_files(pad_sources_dir)

    if not files:
        print(f"[*] No pad source files found for cloud generation in {pad_sources_dir}")
        return {}

    print(f"\n[GRANULAR MAKER] Processing {len(files)} source file(s)...")

    results = {}
    for filepath in files:
        stem = io_utils.get_filename_stem(filepath)
        print(f"  Processing: {stem}")

        audio, _ = io_utils.load_audio(filepath, sr=sr, mono=True)
        if audio is None:
            continue

        clouds = make_clouds_from_source(audio, sr, stem, config)
        results[stem] = clouds
        print(f"    → Generated {len(clouds)} cloud(s)")

    return results


def save_clouds(
    clouds_dict: dict,
    config: dict,
) -> int:
    """
    Save granular clouds to export directory.

    Args:
        clouds_dict: Dictionary {source_name: [(cloud_audio, brightness_tag, filename), ...]}
        config: Configuration dictionary

    Returns:
        Total number of clouds saved
    """
    sr = config['global']['sample_rate']
    bit_depth = config['global']['output_bit_depth']
    export_dir = config['paths']['export_dir']
    cloud_export_dir = f"{export_dir}/clouds"

    io_utils.ensure_directory(cloud_export_dir)

    total_saved = 0
    for source_name, clouds_data in clouds_dict.items():
        for cloud_audio, brightness_tag, filename in clouds_data:
            # Build filename with optional brightness tag
            if brightness_tag:
                base_filename = filename.replace('.wav', '')
                filename_with_tag = f"{base_filename}_{brightness_tag}.wav"
            else:
                filename_with_tag = filename
            filepath = f"{cloud_export_dir}/{filename_with_tag}"
            if io_utils.save_audio(filepath, cloud_audio, sr=sr, bit_depth=bit_depth):
                total_saved += 1
                print(f"    ✓ {filename_with_tag}")

    return total_saved
