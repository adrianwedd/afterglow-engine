"""
Pad mining: extract sustained segments from audio files.
"""

from typing import List, Tuple
import numpy as np
import librosa
from . import io_utils, dsp_utils, audio_analyzer


def extract_sustained_segments(
    audio: np.ndarray,
    sr: int,
    target_duration_sec: float = 2.0,
    min_rms_db: float = -40.0,
    max_rms_db: float = -10.0,
    max_onset_rate: float = 3.0,
    spectral_flatness_threshold: float = 0.5,
    window_hop_sec: float = 0.5,
    use_pre_analysis: bool = True,
    config: dict = None,
) -> List[Tuple[int, int]]:
    """
    Extract sustained segment candidates from audio.

    Enhancements:
    - Optional pre-analysis to favor stable regions with low DC offset & crest
    - Gating to filter out clipped and transient-heavy regions early
    - Spectral tonality check to prefer sustained, harmonic material

    Args:
        audio: Audio array
        sr: Sample rate
        target_duration_sec: Target segment duration
        min_rms_db: Minimum RMS level to accept
        max_rms_db: Maximum RMS level to accept (too loud = reject)
        max_onset_rate: Max onsets per second (too high = too percussive)
        spectral_flatness_threshold: Lower = more tonal (0-1 scale)
        window_hop_sec: Hop size for sliding window analysis
        use_pre_analysis: If True, use AudioAnalyzer for pre-filtering
        config: Configuration dictionary (optional)

    Returns:
        List of (start_sample, end_sample) tuples for valid segments
    """
    window_samples = int(target_duration_sec * sr)
    hop_samples = int(window_hop_sec * sr)

    if len(audio) < window_samples:
        return []

    candidates = []

    # Pre-analyze if requested (identifies stable regions with low DC/crest)
    stable_mask = None
    analyzer = None
    use_pre_analysis_thresholds = False
    pre_min_rms_db = min_rms_db
    pre_max_rms_db = max_rms_db
    pre_max_onset_rate = max_onset_rate

    if use_pre_analysis and config is not None:
        pre_analysis_config = config.get('pre_analysis', {})
        if pre_analysis_config.get('enabled', True):
            analysis_window_sec = pre_analysis_config.get('analysis_window_sec', 1.0)
            analysis_hop_sec = pre_analysis_config.get('analysis_hop_sec', 0.5)

            # Use pre_analysis thresholds if present, otherwise fall back to pad_miner args
            pre_min_rms_db = pre_analysis_config.get('min_rms_db', min_rms_db)
            pre_max_rms_db = pre_analysis_config.get('max_rms_db', max_rms_db)
            pre_max_onset_rate = pre_analysis_config.get('max_onset_rate_hz', max_onset_rate)
            pre_max_dc_offset = pre_analysis_config.get('max_dc_offset', 0.1)
            pre_max_crest = pre_analysis_config.get('max_crest_factor', 10.0)

            # If pre_analysis config has thresholds, use them for window-level checks too
            if 'min_rms_db' in pre_analysis_config or 'max_rms_db' in pre_analysis_config or 'max_onset_rate_hz' in pre_analysis_config:
                use_pre_analysis_thresholds = True

            dsp_utils.vprint(f"    [pre-analysis] Analyzing for pad mining: onset_rate={pre_max_onset_rate}, RMS=[{pre_min_rms_db}, {pre_max_rms_db}] dB, DC={pre_max_dc_offset}, crest={pre_max_crest}")
            analyzer = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=analysis_window_sec, hop_sec=analysis_hop_sec)
            stable_mask = analyzer.get_stable_regions(
                max_onset_rate=pre_max_onset_rate,
                rms_low_db=pre_min_rms_db,
                rms_high_db=pre_max_rms_db,
                max_dc_offset=pre_max_dc_offset,
                max_crest=pre_max_crest,
            )
        else:
            dsp_utils.vprint(f"    [pre-analysis] Disabled: using standard sustained segment detection")
    else:
        dsp_utils.vprint(f"    [pre-analysis] No config provided; using standard sustained segment detection")

    # Compute onset strength
    onset_strength = librosa.onset.onset_strength(y=audio, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_strength, sr=sr, units='samples'
    )

    # Analyze sliding windows
    # Use pre-analysis thresholds if they were explicitly set, otherwise use pad_miner defaults
    window_min_rms_db = pre_min_rms_db if use_pre_analysis_thresholds else min_rms_db
    window_max_rms_db = pre_max_rms_db if use_pre_analysis_thresholds else max_rms_db
    window_max_onset_rate = pre_max_onset_rate if use_pre_analysis_thresholds else max_onset_rate

    for start in range(0, len(audio) - window_samples, hop_samples):
        end = start + window_samples
        segment = audio[start:end]

        # Check RMS level (using appropriate thresholds)
        rms_db = dsp_utils.rms_energy_db(segment)
        if rms_db < window_min_rms_db or rms_db > window_max_rms_db:
            continue

        # Check onset density (using appropriate thresholds)
        onsets_in_window = np.sum((onset_frames >= start) & (onset_frames < end))
        onset_rate = onsets_in_window / target_duration_sec
        if onset_rate > window_max_onset_rate:
            continue

        # Check spectral flatness (tonality)
        spectral_flat = librosa.feature.spectral_flatness(y=segment)
        if np.mean(spectral_flat) > spectral_flatness_threshold:
            continue

        # Optional: check pre-analysis stability mask
        if use_pre_analysis and stable_mask is not None and analyzer is not None:
            # Map segment position to analyzer windows (use analyzer's hop, not mining hop)
            analyzer_hop_samples = int(analyzer.hop_sec * sr)
            analyzer_window_idx = start // analyzer_hop_samples
            if analyzer_window_idx < len(stable_mask):
                if not stable_mask[analyzer_window_idx]:
                    continue

        candidates.append((start, end))

    return candidates


def extract_top_pads(
    candidates: List[Tuple[int, int]],
    audio: np.ndarray,
    sr: int,
    max_candidates: int = 3,
) -> List[np.ndarray]:
    """
    Select top pad candidates based on RMS stability and tonality.

    Args:
        candidates: List of (start, end) tuples
        audio: Full audio array
        sr: Sample rate
        max_candidates: Maximum number of pads to extract

    Returns:
        List of audio arrays for selected pads
    """
    if not candidates:
        return []

    # Score each candidate
    scored = []
    for start, end in candidates:
        segment = audio[start:end]
        rms_db = dsp_utils.rms_energy_db(segment)
        onset_strength = librosa.onset.onset_strength(y=segment, sr=sr)
        onset_mean = np.mean(onset_strength)
        tonality = np.mean(librosa.feature.spectral_flatness(y=segment))

        # Score: low onset activity, good tonality (low flatness), middle RMS
        score = -onset_mean - tonality
        scored.append((score, segment))

    # Sort by score (highest first) and take top candidates
    scored.sort(key=lambda x: x[0], reverse=True)
    return [seg for _, seg in scored[:max_candidates]]


def mine_pads_from_file(
    filepath: str,
    config: dict,
) -> List[Tuple[np.ndarray, str]]:
    """
    Mine pad candidates from a single audio file for multiple target durations.

    Args:
        filepath: Path to audio file
        config: Configuration dictionary with pad_miner settings

    Returns:
        List of (pad_audio, brightness_tag) tuples
    """
    sr = config['global']['sample_rate']
    audio, _ = io_utils.load_audio(filepath, sr=sr, mono=True)

    if audio is None:
        return []

    pm_config = config['pad_miner']

    # Support both legacy 'target_duration_sec' (float) and new 'target_durations_sec' (list)
    target_durations = pm_config.get('target_durations_sec')
    if target_durations is None:
        # Fallback to old config key for backwards compatibility
        target_durations = [pm_config.get('target_duration_sec', 2.0)]
    if not isinstance(target_durations, list):
        target_durations = [target_durations]

    # Crossfade length (new config key, with fallback)
    crossfade_ms = pm_config.get('loop_crossfade_ms', pm_config.get('crossfade_ms', 100))

    # Brightness tagging
    brightness_config = config.get('brightness_tags', {})
    enable_brightness = brightness_config.get('enabled', True)
    centroid_low = brightness_config.get('centroid_low_hz', 1500)
    centroid_high = brightness_config.get('centroid_high_hz', 3500)

    # Export config
    export_config = config.get('export', {})
    pads_stereo = export_config.get('pads_stereo', False)

    pads_with_tags = []

    for target_duration_sec in target_durations:
        candidates = extract_sustained_segments(
            audio,
            sr=sr,
            target_duration_sec=target_duration_sec,
            min_rms_db=pm_config['min_rms_db'],
            max_rms_db=pm_config['max_rms_db'],
            max_onset_rate=pm_config['max_onset_rate_per_second'],
            spectral_flatness_threshold=pm_config['spectral_flatness_threshold'],
            window_hop_sec=pm_config['window_hop_sec'],
            use_pre_analysis=True,
            config=config,
        )

        if not candidates:
            continue

        pads = extract_top_pads(
            candidates,
            audio,
            sr=sr,
            max_candidates=pm_config['max_candidates_per_file'],
        )

        for pad_audio in pads:
            # Apply crossfade to make pads loopable
            pad_audio = dsp_utils.time_domain_crossfade_loop(pad_audio, crossfade_ms, sr)

            # Normalize
            peak_dbfs = config['global']['target_peak_dbfs']
            pad_audio = dsp_utils.normalize_audio(pad_audio, peak_dbfs)

            # Convert to stereo if requested
            if pads_stereo:
                pad_audio = dsp_utils.mono_to_stereo(pad_audio)

            # Classify brightness
            brightness_tag = ""
            if enable_brightness:
                brightness_tag = dsp_utils.classify_brightness(pad_audio, sr, centroid_low, centroid_high)

            pads_with_tags.append((pad_audio, brightness_tag))

    if not pads_with_tags:
        print(f"  [*] No sustained segments found in {filepath}")

    return pads_with_tags


def mine_all_pads(config: dict) -> dict:
    """
    Mine pads from all audio files in source_audio directory.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_filename: [pad_arrays]}
    """
    source_dir = config['paths']['source_audio_dir']
    files = io_utils.discover_audio_files(source_dir)

    if not files:
        print(f"[!] No audio files found in {source_dir}")
        return {}

    print(f"\n[PAD MINER] Processing {len(files)} file(s)...")

    results = {}
    for filepath in files:
        stem = io_utils.get_filename_stem(filepath)
        print(f"  Processing: {stem}")

        pads = mine_pads_from_file(filepath, config)
        if pads:
            results[stem] = pads
            print(f"    → Found {len(pads)} pad candidate(s)")

    return results


def save_mined_pads(
    pad_dict: dict,
    config: dict,
) -> int:
    """
    Save mined pads to export directory.

    Args:
        pad_dict: Dictionary {source_name: [(pad_audio, brightness_tag), ...]}
        config: Configuration dictionary

    Returns:
        Total number of pads saved
    """
    sr = config['global']['sample_rate']
    bit_depth = config['global']['output_bit_depth']
    export_dir = config['paths']['export_dir']
    pad_export_dir = f"{export_dir}/pads"

    io_utils.ensure_directory(pad_export_dir)

    total_saved = 0
    for source_name, pads_with_tags in pad_dict.items():
        for i, (pad_audio, brightness_tag) in enumerate(pads_with_tags, 1):
            # Build filename with optional brightness tag
            if brightness_tag:
                filename = f"{source_name}_pad{i:02d}_{brightness_tag}.wav"
            else:
                filename = f"{source_name}_pad{i:02d}.wav"
            filepath = f"{pad_export_dir}/{filename}"
            if io_utils.save_audio(filepath, pad_audio, sr=sr, bit_depth=bit_depth):
                total_saved += 1
                print(f"    ✓ {filename}")

    return total_saved
