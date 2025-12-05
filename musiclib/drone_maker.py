"""
Drone/pad/swell maker: generate pad loops and swells with processing variants.
"""

from typing import List, Tuple
import numpy as np
import librosa
from . import io_utils, dsp_utils


def process_pad_source(
    audio: np.ndarray,
    sr: int,
    pitch_shifts: List[int],
    time_stretches: List[float],
) -> List[Tuple[np.ndarray, str]]:
    """
    Apply pitch shifts and time stretches to audio.

    Args:
        audio: Input audio
        sr: Sample rate
        pitch_shifts: List of pitch shifts in semitones
        time_stretches: List of time-stretch factors

    Returns:
        List of (audio, description) tuples
    """
    results = []

    # Original
    results.append((audio, "original"))

    # Pitch shifts
    for shift in pitch_shifts:
        if shift != 0:
            shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=shift)
            results.append((shifted, f"pitch_{shift:+d}"))

    # Time stretches
    for factor in time_stretches:
        if factor != 1.0:
            stretched = librosa.effects.time_stretch(audio, rate=factor)
            results.append((stretched, f"stretch_{factor:.1f}x"))

    return results


def extract_pad_loop(
    audio: np.ndarray,
    sr: int,
    duration_sec: float,
) -> np.ndarray:
    """
    Extract a stable pad loop from audio.

    Args:
        audio: Input audio
        sr: Sample rate
        duration_sec: Target pad duration

    Returns:
        Extracted pad audio
    """
    target_samples = int(duration_sec * sr)

    if len(audio) <= target_samples:
        return audio

    # Use the middle/stable region
    start = (len(audio) - target_samples) // 2
    return audio[start : start + target_samples]


def create_tonal_variant(
    audio: np.ndarray,
    sr: int,
    variant_type: str,
    config: dict,
) -> np.ndarray:
    """
    Create a tonal variant of audio (warm, airy, dark).

    Args:
        audio: Input audio
        sr: Sample rate
        variant_type: "warm", "airy", or "dark"
        config: Configuration dictionary

    Returns:
        Processed audio
    """
    drone_config = config['drones']
    audio_out = audio.copy()

    if variant_type == "warm":
        # Low-pass filter for warmth
        cutoff = drone_config['warm_lowpass_hz']
        b, a = dsp_utils.design_butterworth_lowpass(cutoff, sr, order=4)
        audio_out = dsp_utils.apply_filter(audio_out, b, a)

    elif variant_type == "airy":
        # High-pass filter for air/brightness
        cutoff = drone_config['airy_highpass_hz']
        b, a = dsp_utils.design_butterworth_highpass(cutoff, sr, order=4)
        audio_out = dsp_utils.apply_filter(audio_out, b, a)

    elif variant_type == "dark":
        # Aggressive high-cut for darkness
        cutoff = drone_config['dark_high_cut_hz']
        b, a = dsp_utils.design_butterworth_lowpass(cutoff, sr, order=5)
        audio_out = dsp_utils.apply_filter(audio_out, b, a)

    return audio_out


def make_pad_loops(
    audio: np.ndarray,
    sr: int,
    stem_name: str,
    config: dict,
) -> List[Tuple[np.ndarray, str]]:
    """
    Create multiple tonal variants of a pad loop.

    Args:
        audio: Input audio
        sr: Sample rate
        stem_name: Source name for filename
        config: Configuration dictionary

    Returns:
        List of (audio, filename) tuples
    """
    drone_config = config['drones']
    pm_config = config['pad_miner']

    # Extract pad loop of target duration
    duration = drone_config['pad_loop_duration_sec']
    pad = extract_pad_loop(audio, sr, duration)

    # Make loopable
    crossfade_ms = pm_config['crossfade_ms']
    pad = dsp_utils.time_domain_crossfade_loop(pad, crossfade_ms, sr)

    # Normalize
    peak_dbfs = config['global']['target_peak_dbfs']
    pad = dsp_utils.normalize_audio(pad, peak_dbfs)

    # Create variants
    results = []
    for variant in drone_config['pad_variants']:
        variant_audio = create_tonal_variant(pad, sr, variant, config)
        filename = f"{stem_name}_loop_{variant}.wav"
        results.append((variant_audio, filename))

    return results


def make_swells(
    audio: np.ndarray,
    sr: int,
    stem_name: str,
    config: dict,
    swell_index: int = 1,
) -> List[Tuple[np.ndarray, str]]:
    """
    Create swell one-shots from audio.

    Args:
        audio: Input audio
        sr: Sample rate
        stem_name: Source name for filename
        config: Configuration dictionary
        swell_index: Index for naming (1, 2, etc.)

    Returns:
        List of (audio, filename) tuples
    """
    drone_config = config['drones']
    peak_dbfs = config['global']['target_peak_dbfs']

    # Extract swell duration
    swell_duration = drone_config['swell_duration_sec']
    target_samples = int(swell_duration * sr)

    if len(audio) < target_samples:
        swell = audio
    else:
        # Use middle region
        start = (len(audio) - target_samples) // 2
        swell = audio[start : start + target_samples]

    # Apply fade in/out envelope
    fade_in_samples = int(drone_config['fade_in_sec'] * sr)
    fade_out_samples = int(drone_config['fade_out_sec'] * sr)

    swell = dsp_utils.apply_fade_in(swell, fade_in_samples)
    swell = dsp_utils.apply_fade_out(swell, fade_out_samples)

    # Normalize
    swell = dsp_utils.normalize_audio(swell, peak_dbfs)

    filename = f"{stem_name}_swell{swell_index:02d}.wav"
    return [(swell, filename)]


def make_reversed_variants(
    audio: np.ndarray,
    sr: int,
    stem_name: str,
    config: dict,
) -> List[Tuple[np.ndarray, str]]:
    """
    Create reversed variants of audio (optional).

    Args:
        audio: Input audio
        sr: Sample rate
        stem_name: Source name
        config: Configuration dictionary

    Returns:
        List of (audio, filename) tuples
    """
    if not config['drones']['enable_reversal']:
        return []

    reversed_audio = np.flip(audio)
    reversed_audio = dsp_utils.normalize_audio(
        reversed_audio, config['global']['target_peak_dbfs']
    )

    filename = f"{stem_name}_reversed.wav"
    return [(reversed_audio, filename)]


def process_pad_sources(config: dict) -> dict:
    """
    Process all audio files in pad_sources directory.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary {source_name: [(audio, filename), ...]}
    """
    sr = config['global']['sample_rate']
    pad_sources_dir = config['paths']['pad_sources_dir']
    files = io_utils.discover_audio_files(pad_sources_dir)

    if not files:
        print(f"[*] No pad source files found in {pad_sources_dir}")
        return {}

    print(f"\n[DRONE MAKER] Processing {len(files)} pad source file(s)...")

    results = {}
    for filepath in files:
        stem = io_utils.get_filename_stem(filepath)
        print(f"  Processing: {stem}")

        audio, _ = io_utils.load_audio(filepath, sr=sr, mono=True)
        if audio is None:
            continue

        # Get all pitch/stretch variants
        drone_config = config['drones']
        variants = process_pad_source(
            audio,
            sr=sr,
            pitch_shifts=drone_config['pitch_shift_semitones'],
            time_stretches=drone_config['time_stretch_factors'],
        )

        outputs = []
        for variant_audio, variant_desc in variants:
            variant_name = f"{stem}_{variant_desc}"

            # Create pad loops
            loops = make_pad_loops(variant_audio, sr, variant_name, config)
            outputs.extend(loops)

            # Create swells
            swells = make_swells(variant_audio, sr, variant_name, config, swell_index=1)
            outputs.extend(swells)

            # Create reversed variants
            reversed_vars = make_reversed_variants(variant_audio, sr, variant_name, config)
            outputs.extend(reversed_vars)

        results[stem] = outputs
        print(f"    → Generated {len(outputs)} audio file(s)")

    return results


def save_drone_outputs(
    drone_dict: dict,
    config: dict,
) -> Tuple[int, int]:
    """
    Save drone maker outputs to export directories.

    Args:
        drone_dict: Dictionary {source_name: [(audio, filename), ...]}
        config: Configuration dictionary

    Returns:
        (total_pads_saved, total_swells_saved)
    """
    sr = config['global']['sample_rate']
    bit_depth = config['global']['output_bit_depth']
    export_dir = config['paths']['export_dir']

    pad_export_dir = f"{export_dir}/pads"
    swell_export_dir = f"{export_dir}/swells"

    io_utils.ensure_directory(pad_export_dir)
    io_utils.ensure_directory(swell_export_dir)

    pads_saved = 0
    swells_saved = 0

    for source_name, outputs in drone_dict.items():
        for audio, filename in outputs:
            if 'swell' in filename:
                filepath = f"{swell_export_dir}/{filename}"
                export_type = "swell"
                if io_utils.save_audio(filepath, audio, sr=sr, bit_depth=bit_depth):
                    swells_saved += 1
            else:
                filepath = f"{pad_export_dir}/{filename}"
                export_type = "pad"
                if io_utils.save_audio(filepath, audio, sr=sr, bit_depth=bit_depth):
                    pads_saved += 1
            print(f"    ✓ {filename}")

    return pads_saved, swells_saved
