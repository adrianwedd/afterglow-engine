"""
Lightweight config validation to catch obvious mistakes early.
Run automatically by make_textures.py after loading config.
"""

import sys


def validate_config(config: dict) -> None:
    errors = []

    # Global sample rate
    sr = config.get("global", {}).get("sample_rate")
    if not isinstance(sr, int) or sr <= 0:
        errors.append("global.sample_rate must be a positive integer")

    # Clouds: grain lengths
    clouds = config.get("clouds", {})
    gmin = clouds.get("grain_length_min_ms")
    gmax = clouds.get("grain_length_max_ms")
    if gmin is not None and gmax is not None and gmin > gmax:
        errors.append("clouds.grain_length_min_ms cannot exceed grain_length_max_ms")

    # Pad miner: RMS bounds
    pad_miner = config.get("pad_miner", {})
    min_rms = pad_miner.get("min_rms_db")
    max_rms = pad_miner.get("max_rms_db")
    if min_rms is not None and max_rms is not None and min_rms > max_rms:
        errors.append("pad_miner.min_rms_db cannot exceed max_rms_db")

    # Pre-analysis: onset rate and RMS bounds
    pre = config.get("pre_analysis", {})
    pre_min_rms = pre.get("min_rms_db")
    pre_max_rms = pre.get("max_rms_db")
    if pre_min_rms is not None and pre_max_rms is not None and pre_min_rms > pre_max_rms:
        errors.append("pre_analysis.min_rms_db cannot exceed max_rms_db")

    # Bit depth
    bit_depth = config.get("global", {}).get("output_bit_depth")
    if bit_depth not in (16, 24):
        errors.append("global.output_bit_depth must be 16 or 24")

    if errors:
        for e in errors:
            print(f"[config] {e}", file=sys.stderr)
        raise ValueError("Invalid configuration; see messages above.")
