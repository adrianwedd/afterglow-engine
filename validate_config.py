"""
Lightweight config validation to catch obvious mistakes early.
Run automatically by make_textures.py after loading config.
"""

import sys
from musiclib.logger import get_logger
from musiclib.exceptions import InvalidParameter

logger = get_logger(__name__)


def validate_config(config: dict) -> None:
    errors = []

    # Global sample rate
    sr = config.get("global", {}).get("sample_rate")
    if not isinstance(sr, int) or sr <= 0:
        errors.append("global.sample_rate must be a positive integer")
    elif sr < 8000 or sr > 192000:
        errors.append(f"global.sample_rate ({sr}) outside reasonable range [8000, 192000]")

    # Target peak dBFS validation
    target_peak = config.get("global", {}).get("target_peak_dbfs")
    if target_peak is not None:
        if not isinstance(target_peak, (int, float)):
            errors.append("global.target_peak_dbfs must be a number")
        elif target_peak > 0:
            errors.append(f"global.target_peak_dbfs ({target_peak}) must be negative (0 dBFS is digital maximum)")
        elif target_peak < -60:
            # Downgraded to warning - some users may want very quiet output
            logger.warning(f"target_peak_dbfs ({target_peak}) is unusually quiet (< -60 dBFS)")

    # Clouds: grain lengths
    clouds = config.get("clouds", {})
    gmin = clouds.get("grain_length_min_ms")
    gmax = clouds.get("grain_length_max_ms")
    if gmin is not None and gmax is not None and gmin > gmax:
        errors.append("clouds.grain_length_min_ms cannot exceed grain_length_max_ms")
    if gmin is not None and gmin <= 0:
        errors.append(f"clouds.grain_length_min_ms ({gmin}) must be positive")
    if gmax is not None and gmax > 10000:
        errors.append(f"clouds.grain_length_max_ms ({gmax}) is unreasonably large (> 10s)")

    # Clouds: grain density
    grains_per_sec = clouds.get("grains_per_sec")
    if grains_per_sec is not None:
        if not isinstance(grains_per_sec, (int, float)) or grains_per_sec <= 0:
            errors.append("clouds.grains_per_sec must be a positive number")
        elif grains_per_sec > 1000:
            errors.append(f"clouds.grains_per_sec ({grains_per_sec}) is unreasonably high (> 1000)")

    # Clouds: filter length (H4 - Critical for FFT validity)
    filter_length = clouds.get("filter_length_samples")
    if filter_length is not None and sr:
        if not isinstance(filter_length, int) or filter_length <= 0:
            errors.append("clouds.filter_length_samples must be a positive integer")
        elif filter_length > sr:
            errors.append(f"clouds.filter_length_samples ({filter_length}) exceeds sample_rate ({sr})")
        elif filter_length < 64:
            # Downgraded to warning - some advanced users may want smaller windows
            logger.warning(f"filter_length_samples ({filter_length}) is small (< 64), may affect filtering quality")

    # Pad miner: RMS bounds
    pad_miner = config.get("pad_miner", {})
    min_rms = pad_miner.get("min_rms_db")
    max_rms = pad_miner.get("max_rms_db")
    if min_rms is not None and max_rms is not None and min_rms > max_rms:
        errors.append("pad_miner.min_rms_db cannot exceed max_rms_db")

    # Pad miner: duration constraints
    min_duration = pad_miner.get("min_duration_sec")
    if min_duration is not None:
        if not isinstance(min_duration, (int, float)) or min_duration <= 0:
            errors.append("pad_miner.min_duration_sec must be a positive number")
        elif min_duration > 3600:
            errors.append(f"pad_miner.min_duration_sec ({min_duration}) is unreasonably large (> 1 hour)")

    # Pad miner: segment expansion
    expand_sec = pad_miner.get("expand_segment_sec")
    if expand_sec is not None and (not isinstance(expand_sec, (int, float)) or expand_sec < 0):
        errors.append("pad_miner.expand_segment_sec must be a non-negative number")

    # Pre-analysis: onset rate and RMS bounds
    pre = config.get("pre_analysis", {})
    pre_min_rms = pre.get("min_rms_db")
    pre_max_rms = pre.get("max_rms_db")
    if pre_min_rms is not None and pre_max_rms is not None and pre_min_rms > pre_max_rms:
        errors.append("pre_analysis.min_rms_db cannot exceed max_rms_db")
    if pre.get("analysis_window_sec") is not None and pre.get("analysis_window_sec") <= 0:
        errors.append("pre_analysis.analysis_window_sec must be > 0")
    if pre.get("analysis_hop_sec") is not None and pre.get("analysis_hop_sec") <= 0:
        errors.append("pre_analysis.analysis_hop_sec must be > 0")
    # Pre-analysis: stable windows
    min_stable = pre.get("min_stable_windows")
    if min_stable is not None and (not isinstance(min_stable, int) or min_stable <= 0):
        errors.append("pre_analysis.min_stable_windows must be a positive integer")
    # Pre-analysis: centroid gating
    cent_low = pre.get("centroid_low_hz")
    cent_high = pre.get("centroid_high_hz")
    if cent_low is not None and cent_high is not None and cent_low > cent_high:
        errors.append("pre_analysis.centroid_low_hz cannot exceed centroid_high_hz")
    # Overlap ratio sanity
    overlap = config.get("clouds", {}).get("overlap_ratio")
    if overlap is not None and not (0 < overlap < 1):
        errors.append("clouds.overlap_ratio must be between 0 and 1 (exclusive)")

    # Bit depth
    bit_depth = config.get("global", {}).get("output_bit_depth")
    if bit_depth not in (16, 24):
        errors.append("global.output_bit_depth must be 16 or 24")

    # Curation
    curation = config.get("curation", {})
    if not isinstance(curation.get("auto_delete_grade_f", False), bool):
        errors.append("curation.auto_delete_grade_f must be boolean")
    thresh = curation.get("thresholds", {})
    if not isinstance(thresh.get("min_rms_db", -60.0), (int, float)):
        errors.append("curation.thresholds.min_rms_db must be a number")
    if not isinstance(thresh.get("clipping_tolerance", 0.0), (int, float)) or thresh.get("clipping_tolerance", 0.0) < 0:
        errors.append("curation.thresholds.clipping_tolerance must be a positive number")
    if not isinstance(thresh.get("max_crest_factor", 1.0), (int, float)) or thresh.get("max_crest_factor", 1.0) <= 0:
        errors.append("curation.thresholds.max_crest_factor must be a positive number")

    # Musicality
    musicality = config.get("musicality", {})
    ref_bpm = musicality.get("reference_bpm")
    if ref_bpm not in (None, "detect"):
        try:
            val = float(ref_bpm)
            if val <= 0:
                errors.append("musicality.reference_bpm must be > 0 or 'detect'")
        except Exception:
            errors.append("musicality.reference_bpm must be a number or 'detect'")
    bars = musicality.get("bar_lengths", [])
    if bars and any((not isinstance(b, (int, float)) or b <= 0) for b in bars):
        errors.append("musicality.bar_lengths must be positive numbers")
    snap = musicality.get("snap_to_grid")
    if snap not in (None, True, False):
        errors.append("musicality.snap_to_grid must be true/false")

    # Hiss generation
    hiss = config.get("hiss", {})
    highpass_hz = hiss.get("highpass_hz")
    if highpass_hz is not None:
        if not isinstance(highpass_hz, (int, float)) or highpass_hz <= 0:
            errors.append("hiss.highpass_hz must be a positive number")
        elif sr and highpass_hz >= sr / 2:
            errors.append(f"hiss.highpass_hz ({highpass_hz}) must be less than Nyquist frequency ({sr/2} Hz)")

    burst_min = hiss.get("burst_duration_min_ms")
    burst_max = hiss.get("burst_duration_max_ms")
    if burst_min is not None and burst_max is not None and burst_min > burst_max:
        errors.append("hiss.burst_duration_min_ms cannot exceed burst_duration_max_ms")
    if burst_min is not None and burst_min <= 0:
        errors.append(f"hiss.burst_duration_min_ms ({burst_min}) must be positive")

    # Swells and drones (legacy)
    swells = config.get("swells", {})
    attack_sec = swells.get("attack_sec")
    decay_sec = swells.get("decay_sec")
    if attack_sec is not None and (not isinstance(attack_sec, (int, float)) or attack_sec < 0):
        errors.append("swells.attack_sec must be a non-negative number")
    if decay_sec is not None and (not isinstance(decay_sec, (int, float)) or decay_sec < 0):
        errors.append("swells.decay_sec must be a non-negative number")

    swell_dur = swells.get("total_duration_sec")
    if swell_dur is not None:
        if not isinstance(swell_dur, (int, float)) or swell_dur <= 0:
            errors.append("swells.total_duration_sec must be a positive number")
        elif swell_dur > 300:
            errors.append(f"swells.total_duration_sec ({swell_dur}) is unreasonably large (> 5 minutes)")

    drones = config.get("drones", {})
    drone_dur = drones.get("target_duration_sec")
    if drone_dur is not None:
        if not isinstance(drone_dur, (int, float)) or drone_dur <= 0:
            errors.append("drones.target_duration_sec must be a positive number")
        elif drone_dur > 600:
            errors.append(f"drones.target_duration_sec ({drone_dur}) is unreasonably large (> 10 minutes)")

    # Drone maker (v0.8 schema)
    drone_maker = config.get("drone_maker", {})
    target_durations = drone_maker.get("target_durations_sec")
    if target_durations is not None:
        if not isinstance(target_durations, list):
            errors.append("drone_maker.target_durations_sec must be a list")
        elif not target_durations:
            errors.append("drone_maker.target_durations_sec cannot be empty")
        elif not all(isinstance(d, (int, float)) and d > 0 for d in target_durations):
            errors.append("drone_maker.target_durations_sec must contain only positive numbers")

    loop_crossfade = drone_maker.get("loop_crossfade_ms")
    if loop_crossfade is not None and (not isinstance(loop_crossfade, (int, float)) or loop_crossfade < 0):
        errors.append("drone_maker.loop_crossfade_ms must be a non-negative number")

    dm_pitch_range = drone_maker.get("pitch_shift_range", {})
    if dm_pitch_range:
        dm_min_shift = dm_pitch_range.get("min")
        dm_max_shift = dm_pitch_range.get("max")
        if dm_min_shift is not None and dm_max_shift is not None:
            if not isinstance(dm_min_shift, (int, float)) or not isinstance(dm_max_shift, (int, float)):
                errors.append("drone_maker.pitch_shift_range.min/max must be numbers")
            elif dm_min_shift > dm_max_shift:
                errors.append(f"drone_maker.pitch_shift_range.min ({dm_min_shift}) cannot exceed max ({dm_max_shift})")

    # Granular maker (v0.8 schema)
    granular_maker = config.get("granular_maker", {})
    gm_pitch_range = granular_maker.get("pitch_shift_range", {})
    if gm_pitch_range:
        gm_min_shift = gm_pitch_range.get("min")
        gm_max_shift = gm_pitch_range.get("max")
        if gm_min_shift is not None and gm_max_shift is not None:
            if not isinstance(gm_min_shift, (int, float)) or not isinstance(gm_max_shift, (int, float)):
                errors.append("granular_maker.pitch_shift_range.min/max must be numbers")
            elif gm_min_shift > gm_max_shift:
                errors.append(f"granular_maker.pitch_shift_range.min ({gm_min_shift}) cannot exceed max ({gm_max_shift})")

    # Path validation
    paths = config.get("paths", {})
    export_dir = paths.get("export_dir")
    if export_dir and (not isinstance(export_dir, str) or export_dir.strip() == ""):
        errors.append("paths.export_dir must be a non-empty string")
    source_dir = paths.get("source_audio_dir")
    if source_dir and (not isinstance(source_dir, str) or source_dir.strip() == ""):
        errors.append("paths.source_audio_dir must be a non-empty string")

    if errors:
        error_msg = "Invalid configuration:\n" + "\n".join([f"- {e}" for e in errors])
        logger.error(error_msg)
        raise InvalidParameter(error_msg, context={"error_count": len(errors)})


if __name__ == "__main__":
    import yaml
    import os
    from musiclib.logger import log_success

    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                config = yaml.safe_load(f)
                validate_config(config)
                log_success(logger, "Configuration is valid.")
            except Exception as e:
                logger.error(f"Config validation failed: {e}")
                sys.exit(1)
    else:
        logger.error(f"{config_path} not found. Run make_textures.py first to generate it.")
        sys.exit(1)
