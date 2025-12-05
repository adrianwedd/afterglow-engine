"""
Hiss/air texture generator: create high-frequency layers and flicker bursts.
"""

from typing import List, Tuple
import numpy as np
from . import io_utils, dsp_utils


def create_synthetic_noise(
    duration_sec: float,
    sr: int,
    level_db: float = -10.0,
) -> np.ndarray:
    """
    Generate white noise.

    Args:
        duration_sec: Duration in seconds
        sr: Sample rate
        level_db: Level in dB

    Returns:
        Noise audio array
    """
    num_samples = int(duration_sec * sr)
    noise = np.random.randn(num_samples) * 0.1  # Start with normalized noise
    level_linear = dsp_utils.db_to_linear(level_db)
    noise = noise * level_linear
    return noise


def make_hiss_loop(
    audio: np.ndarray,
    sr: int,
    duration_sec: float,
    bandpass: bool = True,
    low_hz: float = 4000,
    high_hz: float = 14000,
    highpass_hz: float = 6000,
    tremolo_rate: float = 3.0,
    tremolo_depth: float = 0.6,
    config_override: dict = None,
) -> np.ndarray:
    """
    Create a high-frequency hiss loop from audio or noise.

    Args:
        audio: Input audio
        sr: Sample rate
        duration_sec: Target duration
        bandpass: Use band-pass instead of high-pass
        low_hz: Band-pass low cutoff (if bandpass=True)
        high_hz: Band-pass high cutoff (if bandpass=True)
        highpass_hz: High-pass cutoff (if bandpass=False)
        tremolo_rate: Amplitude modulation rate in Hz
        tremolo_depth: Modulation depth (0-1)
        config_override: Optional config dict with hiss settings

    Returns:
        Processed hiss loop audio
    """
    target_samples = int(duration_sec * sr)

    # Extract or create source material
    if len(audio) > target_samples:
        # Take a random chunk
        max_start = len(audio) - target_samples
        start = np.random.randint(0, max_start)
        hiss = audio[start : start + target_samples]
    else:
        hiss = audio

    # Ensure correct length
    if len(hiss) < target_samples:
        hiss = np.pad(hiss, (0, target_samples - len(hiss)))
    else:
        hiss = hiss[:target_samples]

    # Apply band-pass or high-pass filter
    if bandpass:
        b, a = dsp_utils.design_butterworth_bandpass(low_hz, high_hz, sr, order=4)
    else:
        b, a = dsp_utils.design_butterworth_highpass(highpass_hz, sr, order=4)

    hiss = dsp_utils.apply_filter(hiss, b, a)

    # Apply tremolo (amplitude modulation)
    hiss = dsp_utils.apply_tremolo(hiss, tremolo_rate, tremolo_depth, sr)

    # Make loopable with crossfade
    crossfade_ms = 50
    hiss = dsp_utils.time_domain_crossfade_loop(hiss, crossfade_ms, sr)

    # Normalize
    hiss = dsp_utils.normalize_audio(hiss, -6.0)  # Slightly lower than main audio

    return hiss


def make_flicker_burst(
    audio: np.ndarray,
    sr: int,
    min_duration_ms: float,
    max_duration_ms: float,
    bandpass: bool = True,
    low_hz: float = 4000,
    high_hz: float = 14000,
    highpass_hz: float = 6000,
) -> np.ndarray:
    """
    Create a short flicker burst of high-frequency noise.

    Args:
        audio: Input audio
        sr: Sample rate
        min_duration_ms: Minimum duration in milliseconds
        max_duration_ms: Maximum duration in milliseconds
        bandpass: Use band-pass instead of high-pass
        low_hz: Band-pass low cutoff
        high_hz: Band-pass high cutoff
        highpass_hz: High-pass cutoff

    Returns:
        Flicker burst audio
    """
    duration_ms = np.random.uniform(min_duration_ms, max_duration_ms)
    duration_sec = duration_ms / 1000.0
    target_samples = int(duration_sec * sr)

    # Extract random segment
    if len(audio) > target_samples:
        max_start = len(audio) - target_samples
        start = np.random.randint(0, max_start)
        flicker = audio[start : start + target_samples]
    else:
        flicker = audio

    # Ensure correct length
    if len(flicker) < target_samples:
        flicker = np.pad(flicker, (0, target_samples - len(flicker)))
    else:
        flicker = flicker[:target_samples]

    # Apply filtering
    if bandpass:
        b, a = dsp_utils.design_butterworth_bandpass(low_hz, high_hz, sr, order=4)
    else:
        b, a = dsp_utils.design_butterworth_highpass(highpass_hz, sr, order=4)

    flicker = dsp_utils.apply_filter(flicker, b, a)

    # Apply envelope (fast attack, fast release for "flicker" effect)
    fade_in_samples = int(0.01 * sr)  # 10ms fade-in
    fade_out_samples = int(0.05 * sr)  # 50ms fade-out

    flicker = dsp_utils.apply_fade_in(flicker, fade_in_samples)
    flicker = dsp_utils.apply_fade_out(flicker, fade_out_samples)

    # Normalize
    flicker = dsp_utils.normalize_audio(flicker, -3.0)

    return flicker


def process_hiss_from_drums(config: dict) -> dict:
    """
    Process percussion files to create hiss loops and flickers.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_name: [(hiss_audio, filename), ...]}
    """
    sr = config['global']['sample_rate']
    drums_dir = config['paths']['drums_dir']
    files = io_utils.discover_audio_files(drums_dir)

    hiss_config = config['hiss']

    if not files:
        print(f"[*] No drum files found in {drums_dir}, will use synthetic noise")
        return {}

    print(f"\n[HISS MAKER] Processing {len(files)} drum file(s)...")

    results = {}
    for filepath in files:
        stem = io_utils.get_filename_stem(filepath)
        print(f"  Processing: {stem}")

        audio, _ = io_utils.load_audio(filepath, sr=sr, mono=True)
        if audio is None:
            continue

        outputs = []

        # Create hiss loops
        for i in range(hiss_config['hiss_loops_per_source']):
            hiss_loop = make_hiss_loop(
                audio,
                sr=sr,
                duration_sec=hiss_config['loop_duration_sec'],
                bandpass=hiss_config['use_bandpass'],
                low_hz=hiss_config.get('bandpass_low_hz', hiss_config.get('band_low_hz', 5000)),
                high_hz=hiss_config.get('bandpass_high_hz', hiss_config.get('band_high_hz', 14000)),
                highpass_hz=hiss_config['highpass_hz'],
                tremolo_rate=hiss_config['tremolo_rate_hz'],
                tremolo_depth=hiss_config['tremolo_depth'],
            )
            filename = f"hiss_loop_{stem}_{i + 1:02d}.wav"
            outputs.append((hiss_loop, filename))

        # Create flicker bursts
        for i in range(hiss_config['flicker_count']):
            flicker = make_flicker_burst(
                audio,
                sr=sr,
                min_duration_ms=hiss_config['flicker_min_ms'],
                max_duration_ms=hiss_config['flicker_max_ms'],
                bandpass=hiss_config['use_bandpass'],
                low_hz=hiss_config.get('bandpass_low_hz', hiss_config.get('band_low_hz', 5000)),
                high_hz=hiss_config.get('bandpass_high_hz', hiss_config.get('band_high_hz', 14000)),
                highpass_hz=hiss_config['highpass_hz'],
            )
            filename = f"hiss_flicker_{stem}_{i + 1:02d}.wav"
            outputs.append((flicker, filename))

        results[stem] = outputs
        print(f"    → Generated {len(outputs)} hiss audio file(s)")

    return results


def process_hiss_synthetic(config: dict) -> dict:
    """
    Create hiss loops and flickers from synthetic noise.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_name: [(hiss_audio, filename), ...]}
    """
    sr = config['global']['sample_rate']
    hiss_config = config['hiss']

    if not hiss_config['use_synthetic_noise']:
        return {}

    print("\n[HISS MAKER] Generating synthetic noise textures...")

    # Create synthetic noise source
    noise_duration = 30.0  # Generate 30 seconds of noise to sample from
    noise = create_synthetic_noise(
        noise_duration,
        sr=sr,
        level_db=hiss_config['synthetic_noise_level_db'],
    )

    outputs = []

    # Create hiss loops from noise
    for i in range(hiss_config['hiss_loops_per_source']):
        hiss_loop = make_hiss_loop(
            noise,
            sr=sr,
            duration_sec=hiss_config['loop_duration_sec'],
            bandpass=hiss_config['use_bandpass'],
            low_hz=hiss_config.get('bandpass_low_hz', hiss_config.get('band_low_hz', 5000)),
            high_hz=hiss_config.get('bandpass_high_hz', hiss_config.get('band_high_hz', 14000)),
            highpass_hz=hiss_config['highpass_hz'],
            tremolo_rate=hiss_config['tremolo_rate_hz'],
            tremolo_depth=hiss_config['tremolo_depth'],
        )
        filename = f"hiss_loop_{i + 1:02d}.wav"
        outputs.append((hiss_loop, filename))

    # Create flicker bursts from noise
    for i in range(hiss_config['flicker_count']):
        flicker = make_flicker_burst(
            noise,
            sr=sr,
            min_duration_ms=hiss_config['flicker_min_ms'],
            max_duration_ms=hiss_config['flicker_max_ms'],
            bandpass=hiss_config['use_bandpass'],
            low_hz=hiss_config.get('bandpass_low_hz', hiss_config.get('band_low_hz', 5000)),
            high_hz=hiss_config.get('bandpass_high_hz', hiss_config.get('band_high_hz', 14000)),
            highpass_hz=hiss_config['highpass_hz'],
        )
        filename = f"hiss_flicker_{i + 1:02d}.wav"
        outputs.append((flicker, filename))

    print(f"  → Generated {len(outputs)} synthetic hiss audio file(s)")

    return {"synthetic": outputs}


def make_all_hiss(config: dict) -> dict:
    """
    Generate hiss loops and flickers from drums or synthetic noise.

    Args:
        config: Configuration dictionary

    Returns:
        Combined dictionary of hiss outputs
    """
    results = {}

    # Try to process drum files
    drum_results = process_hiss_from_drums(config)
    results.update(drum_results)

    # Also generate synthetic hiss if configured
    synthetic_results = process_hiss_synthetic(config)
    results.update(synthetic_results)

    return results


def save_hiss(
    hiss_dict: dict,
    config: dict,
) -> int:
    """
    Save hiss loops and flickers to export directory.

    Args:
        hiss_dict: Dictionary {source_name: [(hiss_audio, filename), ...]}
        config: Configuration dictionary

    Returns:
        Total number of hiss files saved
    """
    sr = config['global']['sample_rate']
    bit_depth = config['global']['output_bit_depth']
    export_dir = config['paths']['export_dir']
    hiss_export_dir = f"{export_dir}/hiss"

    io_utils.ensure_directory(hiss_export_dir)

    total_saved = 0
    for source_name, outputs in hiss_dict.items():
        for hiss_audio, filename in outputs:
            filepath = f"{hiss_export_dir}/{filename}"
            if io_utils.save_audio(filepath, hiss_audio, sr=sr, bit_depth=bit_depth):
                total_saved += 1
                print(f"    ✓ {filename}")

    return total_saved
