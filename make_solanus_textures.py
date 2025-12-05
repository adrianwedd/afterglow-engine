#!/usr/bin/env python3
"""
make_solanus_textures.py

Automatically carve a FLAC file into a TR-8S-ready sample set:
loopable pads, swells, granular clouds, and hiss/noise layers.

Usage:
    python make_solanus_textures.py [--input FILE] [--help]

Dependencies:
    librosa, numpy, scipy, soundfile
"""

import os
import sys
import argparse
import numpy as np
import librosa
import soundfile as sf
from scipy import signal
from scipy.signal.windows import hann


# ============================================================================
# CONFIGURATION: Adjust these to tweak behavior
# ============================================================================

CONFIG = {
    # Input/Output
    "input_file": "VA - Dreamy Harbor [2017] [TRESOR291]/01 Vainqueur - Solanus (Extracted 2).flac",
    "output_dir": "export/TR8S",
    "sample_rate": 44100,
    "output_bit_depth": 16,  # 16 or 24
    "target_peak_dbfs": -1.0,

    # Pad mining
    "pad_window_sec": 2.0,           # Target pad duration
    "pad_hop_sec": 0.3,              # Hop size for sliding window search
    "pad_min_rms_db": -35.0,         # Too quiet = reject
    "pad_max_rms_db": -8.0,          # Too loud = reject
    "pad_max_onset_rate": 4.0,       # Onsets per second (too high = busy)
    "pad_crossfade_ms": 80.0,        # Crossfade for loop smoothing
    "pad_count": 12,                 # Number of pads to extract

    # Swells
    "swell_duration_sec": 5.0,       # Target swell length
    "swell_fade_in_sec": 0.3,        # Fade-in duration
    "swell_fade_out_sec": 1.5,       # Fade-out duration
    "swell_time_stretch": 1.3,       # Time-stretch factor (>1 = slower)
    "swell_count": 6,                # Number of swells to generate

    # Granular clouds
    "cloud_duration_sec": 6.0,       # Output cloud length
    "cloud_grain_min_ms": 50,        # Min grain length
    "cloud_grain_max_ms": 150,       # Max grain length
    "cloud_grains_per_cloud": 180,   # Number of grains per cloud
    "cloud_max_pitch_shift": 8,      # Semitones (±)
    "cloud_overlap_ratio": 0.65,     # Grain overlap
    "cloud_lowpass_hz": 8000,        # Post-processing filter (0 = skip)
    "cloud_count": 6,                # Number of clouds to generate

    # Hiss/air
    "hiss_loop_duration_sec": 1.5,   # Hiss loop length
    "hiss_highpass_hz": 6000,        # High-pass cutoff
    "hiss_bandpass_low_hz": 5000,    # Band-pass low (if enabled)
    "hiss_bandpass_high_hz": 14000,  # Band-pass high (if enabled)
    "hiss_use_bandpass": True,       # Use band-pass instead of high-pass
    "hiss_tremolo_rate_hz": 2.5,     # Tremolo rate
    "hiss_tremolo_depth": 0.5,       # Tremolo depth (0-1)
    "hiss_crossfade_ms": 50,         # Loop crossfade
    "hiss_loop_count": 8,            # Number of hiss loops
    "hiss_flicker_min_ms": 50,       # Min flicker length
    "hiss_flicker_max_ms": 250,      # Max flicker length
    "hiss_flicker_count": 4,         # Number of flicker one-shots
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def db_to_linear(db):
    """Convert dB to linear amplitude."""
    return 10 ** (db / 20.0)


def linear_to_db(linear, min_db=-80.0):
    """Convert linear amplitude to dB."""
    if linear <= 0:
        return min_db
    return 20 * np.log10(linear)


def rms_energy_db(audio):
    """Calculate RMS energy in dB."""
    rms = np.sqrt(np.mean(audio ** 2))
    return linear_to_db(rms)


def normalize_audio(audio, target_peak_dbfs=-1.0):
    """Normalize audio to target peak level."""
    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio
    target_linear = db_to_linear(target_peak_dbfs)
    return audio * (target_linear / peak)


def save_wav(filepath, audio, sr, bit_depth=16):
    """Save audio as WAV with specified bit depth."""
    ensure_dir(os.path.dirname(filepath))
    # Clip to prevent overflow
    audio = np.clip(audio, -1.0, 1.0)
    subtype = f"PCM_{bit_depth}"
    sf.write(filepath, audio, sr, subtype=subtype)


def crossfade_loop(audio, sr, crossfade_ms=80):
    """
    Make audio loopable by crossfading end → beginning.

    Args:
        audio: 1D or 2D (stereo) audio array
        sr: sample rate
        crossfade_ms: crossfade duration in milliseconds

    Returns:
        Loopable audio (same shape as input)
    """
    crossfade_samples = int(crossfade_ms * sr / 1000.0)
    if crossfade_samples > len(audio) // 2:
        crossfade_samples = len(audio) // 2

    # Create fade envelope
    fade_out = np.linspace(1, 0, crossfade_samples)
    fade_in = np.linspace(0, 1, crossfade_samples)

    # Apply to end and beginning
    audio_out = audio.copy()
    if audio.ndim == 1:
        audio_out[-crossfade_samples:] *= fade_out
        audio_out[:crossfade_samples] *= fade_in
        # Overlap-add the crossfade
        audio_out[:crossfade_samples] += audio[-crossfade_samples:] * fade_out
    else:
        # Stereo
        audio_out[-crossfade_samples:] *= fade_out[None, :]
        audio_out[:crossfade_samples] *= fade_in[None, :]
        audio_out[:crossfade_samples] += audio[-crossfade_samples:] * fade_out[None, :]

    return audio_out


def apply_hann_window_edges(audio, window_ms=20, sr=44100):
    """Apply Hann window fade at edges to prevent clicks."""
    window_samples = int(window_ms * sr / 1000.0)
    if window_samples > len(audio) // 2:
        window_samples = len(audio) // 2

    window = hann(window_samples * 2, sym=False)
    if audio.ndim == 1:
        audio[:window_samples] *= window[:window_samples]
        audio[-window_samples:] *= window[window_samples:]
    else:
        audio[:window_samples] *= window[:window_samples, None]
        audio[-window_samples:] *= window[window_samples:, None]

    return audio


def apply_fade_in(audio, fade_samples):
    """Apply linear fade-in."""
    if fade_samples > len(audio):
        fade_samples = len(audio)
    fade = np.linspace(0, 1, fade_samples)
    audio_out = audio.copy()
    if audio.ndim == 1:
        audio_out[:fade_samples] *= fade
    else:
        audio_out[:fade_samples] *= fade[None, :]
    return audio_out


def apply_fade_out(audio, fade_samples):
    """Apply linear fade-out."""
    if fade_samples > len(audio):
        fade_samples = len(audio)
    fade = np.linspace(1, 0, fade_samples)
    audio_out = audio.copy()
    if audio.ndim == 1:
        audio_out[-fade_samples:] *= fade
    else:
        audio_out[-fade_samples:] *= fade[None, :]
    return audio_out


def design_butterworth_lowpass(cutoff_hz, sr, order=5):
    """Design a Butterworth low-pass filter."""
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist
    normalized_cutoff = np.clip(normalized_cutoff, 0.01, 0.99)
    b, a = signal.butter(order, normalized_cutoff, btype='low')
    return b, a


def design_butterworth_highpass(cutoff_hz, sr, order=5):
    """Design a Butterworth high-pass filter."""
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist
    normalized_cutoff = np.clip(normalized_cutoff, 0.01, 0.99)
    b, a = signal.butter(order, normalized_cutoff, btype='high')
    return b, a


def design_butterworth_bandpass(low_hz, high_hz, sr, order=5):
    """Design a Butterworth band-pass filter."""
    nyquist = sr / 2
    low_norm = low_hz / nyquist
    high_norm = high_hz / nyquist
    low_norm = np.clip(low_norm, 0.01, 0.99)
    high_norm = np.clip(high_norm, 0.01, 0.99)
    b, a = signal.butter(order, [low_norm, high_norm], btype='band')
    return b, a


def apply_filter(audio, b, a):
    """Apply IIR filter using filtfilt (zero-phase)."""
    if audio.ndim == 1:
        return signal.filtfilt(b, a, audio)
    else:
        # Stereo: filter each channel separately
        return np.array([signal.filtfilt(b, a, audio[i]) for i in range(audio.shape[0])])


def apply_tremolo(audio, rate_hz, depth, sr):
    """Apply amplitude modulation (tremolo)."""
    n_samples = len(audio)
    t = np.arange(n_samples) / sr
    modulation = 1.0 - depth * 0.5 + depth * 0.5 * np.sin(2 * np.pi * rate_hz * t)
    if audio.ndim == 1:
        return audio * modulation
    else:
        return audio * modulation[None, :]


# ============================================================================
# LOADING & PREPROCESSING
# ============================================================================

def load_audio(filepath, sr=44100):
    """
    Load audio file.

    Returns:
        (audio, sr) where audio is (channels, samples) or (samples,) for mono
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")

    print(f"Loading {filepath}...")
    try:
        audio, sr_orig = librosa.load(filepath, sr=sr, mono=False)
        print(f"  Loaded at {sr} Hz, shape: {audio.shape}")

        # Ensure (channels, samples) shape
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]  # (samples,) -> (1, samples)

        return audio, sr
    except Exception as e:
        print(f"Error loading audio: {e}", file=sys.stderr)
        raise


def to_mono(audio):
    """Convert stereo to mono (mean of channels)."""
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=0)


# ============================================================================
# PAD MINING
# ============================================================================

def find_pad_windows(audio_mono, sr, config):
    """
    Find good pad candidate windows using onset detection and RMS analysis.

    Returns:
        List of (start_sample, end_sample) tuples
    """
    window_samples = int(config["pad_window_sec"] * sr)
    hop_samples = int(config["pad_hop_sec"] * sr)

    if len(audio_mono) < window_samples:
        print("Warning: audio shorter than pad window. Skipping pad mining.")
        return []

    print(f"Analyzing for pad candidates (window={config['pad_window_sec']}s, hop={config['pad_hop_sec']}s)...")

    # Compute onset strength and detect onsets
    onset_strength = librosa.onset.onset_strength(y=audio_mono, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        y=audio_mono, sr=sr, units='samples'
    )

    candidates = []
    for start in range(0, len(audio_mono) - window_samples, hop_samples):
        end = start + window_samples
        segment = audio_mono[start:end]

        # Check RMS level
        rms_db = rms_energy_db(segment)
        if rms_db < config["pad_min_rms_db"] or rms_db > config["pad_max_rms_db"]:
            continue

        # Check onset density
        onsets_in_window = np.sum((onset_frames >= start) & (onset_frames < end))
        onset_rate = onsets_in_window / config["pad_window_sec"]
        if onset_rate > config["pad_max_onset_rate"]:
            continue

        candidates.append((start, end, rms_db, onset_rate))

    if not candidates:
        print("  No pad candidates found!")
        return []

    # Sort by onset rate (lower = better), take top candidates
    candidates.sort(key=lambda x: x[3])
    selected = candidates[:config["pad_count"]]

    print(f"  Found {len(candidates)} candidates, selected {len(selected)} best")
    return [(s, e) for s, e, _, _ in selected]


def make_pad_loops(audio, sr, windows, config):
    """
    Convert selected windows into loopable pads.

    Returns:
        List of (audio_array, filename) tuples
    """
    pads = []

    for i, (start, end) in enumerate(windows):
        segment = audio[:, start:end] if audio.ndim == 2 else audio[start:end]

        # Make loopable
        if segment.ndim == 2:
            segment = crossfade_loop(segment, sr, config["pad_crossfade_ms"])
        else:
            segment = crossfade_loop(segment, sr, config["pad_crossfade_ms"])

        # Normalize
        segment = normalize_audio(segment, config["target_peak_dbfs"])

        # To mono if stereo
        if segment.ndim == 2:
            segment = to_mono(segment)

        filename = f"solanus_pad_{i+1:02d}.wav"
        pads.append((segment, filename))

    return pads


# ============================================================================
# SWELLS
# ============================================================================

def make_swells(audio, sr, config):
    """
    Generate swell textures using time-stretching and envelope shaping.

    Returns:
        List of (audio_array, filename) tuples
    """
    swells = []

    # Use source audio to generate multiple swells
    audio_mono = to_mono(audio) if audio.ndim == 2 else audio

    for i in range(config["swell_count"]):
        # Random starting position
        target_samples = int(config["swell_duration_sec"] * sr)
        max_start = max(0, len(audio_mono) - target_samples)
        if max_start == 0:
            start = 0
        else:
            start = np.random.randint(0, max_start)

        swell = audio_mono[start:start + target_samples]

        # Pad if too short
        if len(swell) < target_samples:
            swell = np.pad(swell, (0, target_samples - len(swell)))

        # Time-stretch for variation
        if i % 2 == 0:
            # Time-stretch every other swell
            swell = librosa.effects.time_stretch(swell, rate=config["swell_time_stretch"])
            # Resample back to target length
            if len(swell) != target_samples:
                swell = librosa.resample(swell, orig_sr=sr, target_sr=sr, res_type='kaiser_best')
                swell = swell[:target_samples]
                if len(swell) < target_samples:
                    swell = np.pad(swell, (0, target_samples - len(swell)))

        # Apply envelope
        fade_in_samples = int(config["swell_fade_in_sec"] * sr)
        fade_out_samples = int(config["swell_fade_out_sec"] * sr)

        swell = apply_fade_in(swell, fade_in_samples)
        swell = apply_fade_out(swell, fade_out_samples)

        # Normalize
        swell = normalize_audio(swell, config["target_peak_dbfs"])

        filename = f"solanus_swell_{i+1:02d}.wav"
        swells.append((swell, filename))

    return swells


# ============================================================================
# GRANULAR CLOUDS
# ============================================================================

def make_granular_clouds(audio, sr, config):
    """
    Generate granular cloud textures by extracting and overlapping grains.

    Returns:
        List of (audio_array, filename) tuples
    """
    clouds = []
    audio_mono = to_mono(audio) if audio.ndim == 2 else audio

    for cloud_idx in range(config["cloud_count"]):
        cloud_samples = int(config["cloud_duration_sec"] * sr)
        cloud = np.zeros(cloud_samples)

        # Generate grains
        grain_length_min = int(config["cloud_grain_min_ms"] * sr / 1000.0)
        grain_length_max = int(config["cloud_grain_max_ms"] * sr / 1000.0)

        for _ in range(config["cloud_grains_per_cloud"]):
            grain_length = np.random.randint(grain_length_min, grain_length_max + 1)

            # Random start position in source
            max_start = max(0, len(audio_mono) - grain_length)
            if max_start == 0:
                grain_start = 0
            else:
                grain_start = np.random.randint(0, max_start)

            grain = audio_mono[grain_start:grain_start + grain_length].copy()

            # Apply Hann window
            window = hann(len(grain), sym=False)
            grain = grain * window

            # Random pitch shift
            if config["cloud_max_pitch_shift"] > 0:
                shift = np.random.uniform(
                    -config["cloud_max_pitch_shift"],
                    config["cloud_max_pitch_shift"]
                )
                grain = librosa.effects.pitch_shift(grain, sr=sr, n_steps=shift)

            # Random placement in output
            cloud_start = np.random.randint(0, max(1, cloud_samples - len(grain)))
            cloud_end = min(cloud_start + len(grain), cloud_samples)
            grain_len = cloud_end - cloud_start

            cloud[cloud_start:cloud_end] += grain[:grain_len]

        # Normalize to prevent clipping
        peak = np.max(np.abs(cloud))
        if peak > 0:
            cloud = cloud / peak * 0.95

        # Post-processing: optional low-pass filter
        if config["cloud_lowpass_hz"] > 0:
            b, a = design_butterworth_lowpass(config["cloud_lowpass_hz"], sr, order=3)
            cloud = apply_filter(cloud, b, a)

        # Final normalization
        cloud = normalize_audio(cloud, config["target_peak_dbfs"])

        filename = f"solanus_cloud_{cloud_idx+1:02d}.wav"
        clouds.append((cloud, filename))

    return clouds


# ============================================================================
# HISS / AIR TEXTURES
# ============================================================================

def make_hiss_loops(audio, sr, config):
    """
    Generate high-frequency hiss loops from source audio.

    Returns:
        List of (audio_array, filename) tuples
    """
    hiss_loops = []
    audio_mono = to_mono(audio) if audio.ndim == 2 else audio

    for i in range(config["hiss_loop_count"]):
        # Extract random segment
        target_samples = int(config["hiss_loop_duration_sec"] * sr)
        max_start = max(0, len(audio_mono) - target_samples)
        if max_start == 0:
            start = 0
        else:
            start = np.random.randint(0, max_start)

        hiss = audio_mono[start:start + target_samples].copy()

        # Pad if too short
        if len(hiss) < target_samples:
            hiss = np.pad(hiss, (0, target_samples - len(hiss)))

        # Apply high-pass or band-pass filter
        if config["hiss_use_bandpass"]:
            b, a = design_butterworth_bandpass(
                config["hiss_bandpass_low_hz"],
                config["hiss_bandpass_high_hz"],
                sr, order=4
            )
        else:
            b, a = design_butterworth_highpass(config["hiss_highpass_hz"], sr, order=4)

        hiss = apply_filter(hiss, b, a)

        # Apply tremolo (subtle amplitude modulation)
        hiss = apply_tremolo(
            hiss,
            config["hiss_tremolo_rate_hz"],
            config["hiss_tremolo_depth"],
            sr
        )

        # Make loopable
        hiss = crossfade_loop(hiss, sr, config["hiss_crossfade_ms"])

        # Normalize
        hiss = normalize_audio(hiss, config["target_peak_dbfs"] - 6.0)  # Slightly quieter

        filename = f"solanus_hiss_loop_{i+1:02d}.wav"
        hiss_loops.append((hiss, filename))

    return hiss_loops


def make_hiss_flickers(audio, sr, config):
    """
    Generate short, bright flicker bursts.

    Returns:
        List of (audio_array, filename) tuples
    """
    flickers = []
    audio_mono = to_mono(audio) if audio.ndim == 2 else audio

    for i in range(config["hiss_flicker_count"]):
        # Random duration
        duration_ms = np.random.uniform(
            config["hiss_flicker_min_ms"],
            config["hiss_flicker_max_ms"]
        )
        duration_samples = int(duration_ms * sr / 1000.0)

        # Extract random segment
        max_start = max(0, len(audio_mono) - duration_samples)
        if max_start == 0:
            start = 0
        else:
            start = np.random.randint(0, max_start)

        flicker = audio_mono[start:start + duration_samples].copy()

        # Pad if too short
        if len(flicker) < duration_samples:
            flicker = np.pad(flicker, (0, duration_samples - len(flicker)))

        # Apply high-pass filter (bright)
        b, a = design_butterworth_highpass(config["hiss_highpass_hz"] + 2000, sr, order=4)
        flicker = apply_filter(flicker, b, a)

        # Quick envelope (attack + release)
        attack_samples = int(0.01 * sr)
        release_samples = int(0.05 * sr)
        flicker = apply_fade_in(flicker, attack_samples)
        flicker = apply_fade_out(flicker, release_samples)

        # Normalize
        flicker = normalize_audio(flicker, config["target_peak_dbfs"] - 3.0)

        filename = f"solanus_hiss_flicker_{i+1:02d}.wav"
        flickers.append((flicker, filename))

    return flickers


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate TR-8S sample set from Solanus track"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=CONFIG["input_file"],
        help=f"Input FLAC file (default: {CONFIG['input_file']})"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=CONFIG["output_dir"],
        help=f"Output directory (default: {CONFIG['output_dir']})"
    )

    args = parser.parse_args()

    # Update config
    CONFIG["input_file"] = args.input
    CONFIG["output_dir"] = args.output_dir

    print("=" * 70)
    print("SOLANUS TEXTURE GENERATOR FOR TR-8S")
    print("=" * 70)

    # Load audio
    try:
        audio, sr = load_audio(CONFIG["input_file"], sr=CONFIG["sample_rate"])
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    audio_mono = to_mono(audio)

    # Initialize counts
    stats = {
        "pads": 0,
        "swells": 0,
        "clouds": 0,
        "hiss_loops": 0,
        "hiss_flickers": 0,
    }

    # ========== PAD MINING ==========
    print("\n[1/5] Mining pad candidates...")
    pad_windows = find_pad_windows(audio_mono, sr, CONFIG)
    if pad_windows:
        pads = make_pad_loops(audio, sr, pad_windows, CONFIG)
        ensure_dir(f"{CONFIG['output_dir']}/pads")
        for pad_audio, filename in pads:
            filepath = f"{CONFIG['output_dir']}/pads/{filename}"
            save_wav(filepath, pad_audio, sr, CONFIG["output_bit_depth"])
            stats["pads"] += 1
        print(f"  ✓ Exported {len(pads)} pads")

    # ========== SWELLS ==========
    print("\n[2/5] Generating swells...")
    swells = make_swells(audio, sr, CONFIG)
    ensure_dir(f"{CONFIG['output_dir']}/swells")
    for swell_audio, filename in swells:
        filepath = f"{CONFIG['output_dir']}/swells/{filename}"
        save_wav(filepath, swell_audio, sr, CONFIG["output_bit_depth"])
        stats["swells"] += 1
    print(f"  ✓ Exported {len(swells)} swells")

    # ========== GRANULAR CLOUDS ==========
    print("\n[3/5] Generating granular clouds...")
    clouds = make_granular_clouds(audio, sr, CONFIG)
    ensure_dir(f"{CONFIG['output_dir']}/clouds")
    for cloud_audio, filename in clouds:
        filepath = f"{CONFIG['output_dir']}/clouds/{filename}"
        save_wav(filepath, cloud_audio, sr, CONFIG["output_bit_depth"])
        stats["clouds"] += 1
    print(f"  ✓ Exported {len(clouds)} clouds")

    # ========== HISS LOOPS ==========
    print("\n[4/5] Generating hiss loops...")
    hiss_loops = make_hiss_loops(audio, sr, CONFIG)
    ensure_dir(f"{CONFIG['output_dir']}/hiss")
    for hiss_audio, filename in hiss_loops:
        filepath = f"{CONFIG['output_dir']}/hiss/{filename}"
        save_wav(filepath, hiss_audio, sr, CONFIG["output_bit_depth"])
        stats["hiss_loops"] += 1
    print(f"  ✓ Exported {len(hiss_loops)} hiss loops")

    # ========== HISS FLICKERS ==========
    print("\n[5/5] Generating hiss flickers...")
    flickers = make_hiss_flickers(audio, sr, CONFIG)
    for flicker_audio, filename in flickers:
        filepath = f"{CONFIG['output_dir']}/hiss/{filename}"
        save_wav(filepath, flicker_audio, sr, CONFIG["output_bit_depth"])
        stats["hiss_flickers"] += 1
    print(f"  ✓ Exported {len(flickers)} hiss flickers")

    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"  Pads:            {stats['pads']}")
    print(f"  Swells:          {stats['swells']}")
    print(f"  Clouds:          {stats['clouds']}")
    print(f"  Hiss loops:      {stats['hiss_loops']}")
    print(f"  Hiss flickers:   {stats['hiss_flickers']}")
    print(f"  Total:           {sum(stats.values())} files")
    print(f"\n  Output: {CONFIG['output_dir']}/")
    print(f"  Format: {CONFIG['sample_rate']} Hz, {CONFIG['output_bit_depth']}-bit WAV")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
