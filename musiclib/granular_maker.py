"""
Granular cloud generator: create abstract, evolving textures from audio.

v0.2 ARCHITECTURE with IMPROVED GRAIN QUALITY

This module provides the public API for cloud generation (process_cloud_sources,
make_clouds_from_source, save_clouds) while enhancing the internals with:

- Smart grain extraction (analyzes quality, avoids silent/transient regions)
- Per-grain length variation (respects min/max range)
- Cycling grain placement (fills buffer completely, no silence tail)
- Optional post-smoothing (reduces clicks and artifacts)
- Full config integration (brightness tags, stereo export, counts)
"""

from typing import List, Tuple
import numpy as np
import librosa
from scipy import signal
from . import io_utils, dsp_utils, audio_analyzer


# ============================================================================
# GRAIN QUALITY ANALYSIS (ENHANCED)
# ============================================================================

def analyze_grain_quality(
    grain: np.ndarray,
    sr: int,
    check_silence: bool = True,
    check_dc: bool = True,
    check_clipping: bool = True,
    check_skew: bool = True,
) -> float:
    """
    Score grain quality (0-1, higher is better).

    Penalties for:
    - Silent regions (RMS < threshold)
    - DC offset (mean >> 0)
    - Clipping (peak near 1.0 or extreme crest factor)
    - Extreme spectral skew
    - High energy concentration (transient-like)

    Args:
        grain: Audio grain to analyze
        sr: Sample rate
        check_silence: Penalize silent grains
        check_dc: Penalize grains with DC offset
        check_clipping: Penalize clipping and extreme crest
        check_skew: Penalize lopsided envelopes

    Returns:
        Quality score (0.0 to 1.0)
    """
    score = 1.0

    if len(grain) < 2:
        return 0.1  # Too short

    # Check for silence
    rms = dsp_utils.rms_energy(grain)
    if check_silence and rms < 0.005:  # Very quiet
        score *= 0.1
    elif check_silence and rms < 0.01:
        score *= 0.3

    # Check for DC offset (bias away from zero)
    mean_abs = np.abs(np.mean(grain))
    if check_dc and mean_abs > 0.15:  # Large DC offset
        score *= 0.5
    elif check_dc and mean_abs > 0.08:
        score *= 0.75

    # Check for clipping and extreme crest factor
    if check_clipping:
        peak = np.max(np.abs(grain))
        if peak > 0.98:  # Near-clipping
            score *= 0.3
        elif peak > 0.95:  # Clipping
            score *= 0.5

        # Crest factor: peak / RMS (high = transient-like, undesirable for sustained grains)
        crest = peak / (rms + 1e-6)
        if crest > 15.0:  # Extreme crest (very sharp transient)
            score *= 0.4
        elif crest > 10.0:  # High crest
            score *= 0.6

    # Check for extreme skew (lopsided envelope)
    if check_skew and len(grain) > 10:
        first_half_energy = np.sum(grain[: len(grain) // 2] ** 2)
        second_half_energy = np.sum(grain[len(grain) // 2 :] ** 2)
        total_energy = first_half_energy + second_half_energy
        if total_energy > 0:
            skew = abs(first_half_energy - second_half_energy) / total_energy
            if skew > 0.85:  # Very lopsided
                score *= 0.3
            elif skew > 0.7:  # Lopsided
                score *= 0.6

    return max(0.0, min(1.0, score))


# ============================================================================
# CORE EXTRACTION & SYNTHESIS (IMPROVED)
# ============================================================================

def extract_grains(
    audio: np.ndarray,
    grain_length_min_ms: float,
    grain_length_max_ms: float,
    num_grains: int,
    sr: int,
    use_quality_filter: bool = True,
    min_quality: float = 0.4,
    analyzer: audio_analyzer.AudioAnalyzer = None,
    max_onset_rate_hz: float = 3.0,
    min_rms_db: float = -40.0,
    max_rms_db: float = -10.0,
    max_dc_offset: float = 0.1,
    max_crest_factor: float = 10.0,
    min_stable_windows: int = 2,
    centroid_low_hz: float = None,
    centroid_high_hz: float = None,
) -> List[np.ndarray]:
    """
    Extract grains from audio with optional quality filtering.

    Enhancements:
    - Per-grain length variation (respects min/max range)
    - Quality-filtered extraction (skips bad regions if requested)
    - Pre-analysis using AudioAnalyzer to favor stable regions
    - Avoids clipped, DC-biased, or transient-heavy regions

    Args:
        audio: Input audio
        grain_length_min_ms: Minimum grain length in ms
        grain_length_max_ms: Maximum grain length in ms
        num_grains: Number of grains to extract
        sr: Sample rate
        use_quality_filter: If True, skip low-quality grains
        min_quality: Minimum quality score (0-1) to accept
        analyzer: AudioAnalyzer instance for pre-analysis (optional)
        max_onset_rate_hz: Max onsets per second to accept (for stable regions)
        min_rms_db: Minimum RMS level (dB) to accept
        max_rms_db: Maximum RMS level (dB) to accept
        max_dc_offset: Maximum DC offset to accept
        max_crest_factor: Maximum peak/RMS ratio to accept
        min_stable_windows: Minimum consecutive stable windows required
        centroid_low_hz: Min spectral centroid (Hz) for stable regions
        centroid_high_hz: Max spectral centroid (Hz) for stable regions

    Returns:
        List of windowed grain audio arrays
    """
    grain_length_min_samples = int(grain_length_min_ms * sr / 1000)
    grain_length_max_samples = int(grain_length_max_ms * sr / 1000)

    grains = []
    max_start = max(0, len(audio) - grain_length_max_samples)

    if max_start == 0:
        # Audio too short; extract what we can
        for _ in range(num_grains):
            grain_length = np.random.randint(grain_length_min_samples, grain_length_max_samples + 1)
            grain = audio[:grain_length]
            if len(grain) < grain_length:
                grain = np.pad(grain, (0, grain_length - len(grain)))
            window = dsp_utils.hann_window(len(grain))
            grain = grain * window
            grains.append(grain)
        return grains

    # Prepare stability mask if analyzer provided
    stable_mask = None
    if use_quality_filter and analyzer is not None:
        stable_mask = analyzer.get_stable_regions(
            max_onset_rate=max_onset_rate_hz,
            rms_low_db=min_rms_db,
            rms_high_db=max_rms_db,
            max_dc_offset=max_dc_offset,
            max_crest=max_crest_factor,
            centroid_low_hz=centroid_low_hz,
            centroid_high_hz=centroid_high_hz,
        )
        num_stable = np.sum(stable_mask) if stable_mask is not None else 0
        centroid_msg = f", centroid=[{centroid_low_hz},{centroid_high_hz}]" if (centroid_low_hz or centroid_high_hz) else ""
        dsp_utils.vprint(f"      [stable regions] {num_stable} / {len(stable_mask)} windows stable (onset_rate={max_onset_rate_hz}, RMS=[{min_rms_db},{max_rms_db}] dB, DC={max_dc_offset}, crest={max_crest_factor}, consecutive={min_stable_windows}{centroid_msg})")
        if num_stable == 0:
            print(f"      [fallback] 0/{len(stable_mask)} windows stable; using least-onset fallback")

    # Extract grains with optional quality filtering
    attempts = 0
    max_attempts = num_grains * 10 if use_quality_filter else num_grains

    while len(grains) < num_grains and attempts < max_attempts:
        attempts += 1

        # Random grain length in range (per-grain variation)
        grain_length = np.random.randint(grain_length_min_samples, grain_length_max_samples + 1)

        # If we have stability mask, bias towards stable regions
        if use_quality_filter and stable_mask is not None and np.any(stable_mask):
            # Sample from stable regions
            result = analyzer.sample_from_stable_region(
                grain_length / sr, 
                stable_mask=stable_mask,
                min_stable_windows=min_stable_windows,
            )
            if result is not None:
                start, _ = result
            else:
                # Fallback: if strict sampling failed (e.g. runs too short), try soft fallback
                sorted_windows = analyzer.get_sorted_windows(
                    rms_low_db=min_rms_db,
                    rms_high_db=max_rms_db,
                    max_dc_offset=max_dc_offset,
                    max_crest=max_crest_factor,
                    centroid_low_hz=centroid_low_hz,
                    centroid_high_hz=centroid_high_hz,
                )
                if len(sorted_windows) > 0:
                    top_n = max(1, len(sorted_windows) // 5) # Top 20%
                    best_windows = sorted_windows[:top_n]
                    window_idx = np.random.choice(best_windows)
                    start, window_end = analyzer.get_sample_range_for_window(window_idx)
                    max_len = window_end - start
                    grain_length = min(grain_length, max_len)
                    # Add small random offset within the window while preserving length
                    max_offset = max(0, max_len - grain_length)
                    offset = np.random.randint(0, max(1, max_offset + 1))
                    start = min(start + offset, len(audio) - grain_length)
                else:
                    start = np.random.randint(0, max(1, max_start - grain_length + 1))
        elif use_quality_filter and analyzer is not None:
            # Soft fallback: if mask was empty, pick from top 20% "best" windows
            sorted_windows = analyzer.get_sorted_windows(
                rms_low_db=min_rms_db,
                rms_high_db=max_rms_db,
                max_dc_offset=max_dc_offset,
                max_crest=max_crest_factor,
                centroid_low_hz=centroid_low_hz,
                centroid_high_hz=centroid_high_hz,
            )
            if len(sorted_windows) > 0:
                top_n = max(1, len(sorted_windows) // 5) # Top 20%
                best_windows = sorted_windows[:top_n]
                window_idx = np.random.choice(best_windows)
                start, window_end = analyzer.get_sample_range_for_window(window_idx)
                max_len = window_end - start
                grain_length = min(grain_length, max_len)
                max_offset = max(0, max_len - grain_length)
                offset = np.random.randint(0, max(1, max_offset + 1))
                start = min(start + offset, len(audio) - grain_length)
            else:
                start = np.random.randint(0, max(1, max_start - grain_length + 1))
        else:
            start = np.random.randint(0, max(1, max_start - grain_length + 1))

        end = min(start + grain_length, len(audio))
        grain = audio[start:end]

        # Pad if necessary
        if len(grain) < grain_length:
            grain = np.pad(grain, (0, grain_length - len(grain)))

        # Quality check
        if use_quality_filter and analyze_grain_quality(grain, sr) < min_quality:
            continue

        # Apply Hann window
        window = dsp_utils.hann_window(len(grain))
        grain = grain * window
        grains.append(grain)

    return grains


def apply_pitch_shift_grain(
    grain: np.ndarray,
    sr: int,
    min_shift_semitones: float,
    max_shift_semitones: float,
    min_grain_length_samples: int = 256,
    max_rate: float = 2.0,
) -> np.ndarray:
    """
    Apply random pitch shift to a grain using resampling (tape speed effect).

    This changes both pitch and duration, avoiding phase vocoder artifacts
    on short grains.

    Args:
        grain: Input grain
        sr: Sample rate
        min_shift_semitones: Minimum pitch shift
        max_shift_semitones: Maximum pitch shift

    Returns:
        Resampled (pitch-shifted) grain
    """
    if min_shift_semitones == 0 and max_shift_semitones == 0:
        return grain

    # Skip pitch-shift for very short grains to avoid artifacts and extreme resample rates
    if len(grain) < min_grain_length_samples:
        return grain

    shift = np.random.uniform(min_shift_semitones, max_shift_semitones)
    if shift == 0:
        return grain

    # If librosa is unavailable, skip pitch-shift gracefully
    if librosa is None:
        return grain

    # Calculate resampling rate
    # rate > 1.0 = pitch up (shorter)
    # rate < 1.0 = pitch down (longer)
    rate = 2.0 ** (shift / 12.0)
    # Clamp rate to avoid extreme resampling (CPU and density impact)
    rate = max(1.0 / max_rate, min(max_rate, rate))

    try:
        # Resample using clamped rate
        resampled = librosa.resample(grain, orig_sr=sr, target_sr=sr / rate)
        return resampled
    except Exception:
        return grain


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
    config: dict = None,
) -> np.ndarray:
    """
    Generate a granular cloud texture from audio.

    Enhancements:
    - Pre-analyzes audio to identify stable, high-quality regions (if enabled)
    - Uses improved extraction (quality filtering, per-grain length)
    - Biases grain selection towards stable regions with low onset density
    - Grain placement cycles to fill buffer completely (no silence tail)

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
        config: Configuration dictionary (optional; uses defaults if not provided)

    Returns:
        Generated cloud audio array
    """
    # Extract pre-analysis config (with sensible defaults)
    if config is None:
        config = {}

    pre_analysis_config = config.get('pre_analysis', {})
    use_pre_analysis = pre_analysis_config.get('enabled', True)
    analysis_window_sec = pre_analysis_config.get('analysis_window_sec', 1.0)
    analysis_hop_sec = pre_analysis_config.get('analysis_hop_sec', 0.5)
    quality_threshold = pre_analysis_config.get('grain_quality_threshold', 0.4)
    max_dc_offset = pre_analysis_config.get('max_dc_offset', 0.1)
    max_crest = pre_analysis_config.get('max_crest_factor', 10.0)
    max_onset_rate = pre_analysis_config.get('max_onset_rate_hz', 3.0)
    min_rms_db = pre_analysis_config.get('min_rms_db', -40.0)
    max_rms_db = pre_analysis_config.get('max_rms_db', -10.0)
    min_stable_windows = pre_analysis_config.get('min_stable_windows', 2)
    centroid_low = pre_analysis_config.get('centroid_low_hz')
    centroid_high = pre_analysis_config.get('centroid_high_hz')

    # Create analyzer only if enabled
    analyzer = None
    if use_pre_analysis:
        dsp_utils.vprint(f"  [pre-analysis] Analyzing audio: {analysis_window_sec}s window, {analysis_hop_sec}s hop, onset_rate={max_onset_rate}, RMS=[{min_rms_db}, {max_rms_db}] dB, DC_offset={max_dc_offset}, crest={max_crest}")
        analyzer = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=analysis_window_sec, hop_sec=analysis_hop_sec)
    else:
        dsp_utils.vprint(f"  [pre-analysis] Disabled: using random grain extraction")

    # Extract grains with quality filtering and optional pre-analysis
    grains = extract_grains(
        audio,
        grain_length_min_ms,
        grain_length_max_ms,
        num_grains,
        sr,
        use_quality_filter=True,
        min_quality=quality_threshold,
        analyzer=analyzer,
        max_onset_rate_hz=max_onset_rate,
        min_rms_db=min_rms_db,
        max_rms_db=max_rms_db,
        max_dc_offset=max_dc_offset,
        max_crest_factor=max_crest,
        min_stable_windows=min_stable_windows,
        centroid_low_hz=centroid_low,
        centroid_high_hz=centroid_high,
    )

    if not grains:
        # Fallback: extract without quality filter or pre-analysis
        grains = extract_grains(
            audio,
            grain_length_min_ms,
            grain_length_max_ms,
            num_grains,
            sr,
            use_quality_filter=False,
            analyzer=None,
        )

    # Apply pitch shifts (resampling)
    grains = [
        apply_pitch_shift_grain(g, sr, pitch_shift_min, pitch_shift_max)
        for g in grains
    ]

    # Shuffle grains to avoid temporal linearity
    np.random.shuffle(grains)

    # Create output buffer
    cloud_samples = int(cloud_duration_sec * sr)
    cloud = np.zeros(cloud_samples)

    # Determine hop size
    grain_length_samples = int(
        (grain_length_min_ms + grain_length_max_ms) / 2 * sr / 1000
    )
    hop_samples = max(1, int(grain_length_samples * (1 - overlap_ratio)))

    # Place grains with cycling (cycles through grains to fill buffer)
    grain_idx = 0
    current_pos = 0

    while current_pos < cloud_samples:
        grain = grains[grain_idx % len(grains)]  # Cycle through grains
        end_pos = min(current_pos + len(grain), cloud_samples)
        grain_len = end_pos - current_pos

        cloud[current_pos:end_pos] += grain[:grain_len]
        current_pos += hop_samples
        grain_idx += 1

    # Normalize and prevent clipping
    peak = np.max(np.abs(cloud))
    if peak > 0:
        cloud = cloud / peak * 0.95

    # Apply short fade in/out to prevent clicks (guard so fades don't dominate)
    fade_samples = int(0.01 * sr) # 10ms nominal
    fade_samples = min(fade_samples, len(cloud) // 4)
    cloud = dsp_utils.apply_fade_in(cloud, fade_samples)
    cloud = dsp_utils.apply_fade_out(cloud, fade_samples)

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


# ============================================================================
# HIGH-LEVEL CLOUD GENERATION API (v0.2 COMPATIBLE)
# ============================================================================

def make_clouds_from_source(
    audio: np.ndarray,
    sr: int,
    stem_name: str,
    config: dict,
    source_index: int = 1,
) -> List[Tuple[np.ndarray, str, str]]:
    """
    Create multiple cloud variations from a source audio.

    Respects config for:
    - clouds_per_source: number of variants to generate
    - grain lengths, pitch ranges, overlap
    - brightness tagging and stereo export settings

    Args:
        audio: Source audio
        sr: Sample rate
        stem_name: Source name for filename
        config: Configuration dictionary
        source_index: Source index for naming

    Returns:
        List of (cloud_audio, brightness_tag, filename) tuples
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

    clouds_per_source = cloud_config.get('clouds_per_source', 2)
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
            config=config,
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
            brightness_tag = dsp_utils.classify_brightness(
                cloud, sr, centroid_low, centroid_high
            )

        filename = f"cloud_{stem_name}_{i + 1:02d}.wav"
        results.append((cloud, brightness_tag, filename))

    return results


def process_cloud_sources(config: dict) -> dict:
    """
    Process all audio files in pad_sources directory to create clouds.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_name: [(cloud_audio, brightness_tag, filename), ...]}
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

    total_saved = 0
    for source_name, clouds_data in clouds_dict.items():
        # Group by source name
        target_dir = f"{export_dir}/{source_name}/clouds"
        io_utils.ensure_directory(target_dir)

        for cloud_audio, brightness_tag, filename in clouds_data:
            # Build filename with optional brightness tag
            if brightness_tag:
                base_filename = filename.replace('.wav', '')
                filename_with_tag = f"{base_filename}_{brightness_tag}.wav"
            else:
                filename_with_tag = filename
            filepath = f"{target_dir}/{filename_with_tag}"
            if io_utils.save_audio(filepath, cloud_audio, sr=sr, bit_depth=bit_depth):
                total_saved += 1
                print(f"    ✓ {filename_with_tag}")

    return total_saved
