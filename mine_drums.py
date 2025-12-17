#!/usr/bin/env python3
"""
mine_drums.py: Extract transient (drum/percussion) sounds from audio.

Usage:
  python mine_drums.py
"""

import os
import sys
import argparse
import copy
import numpy as np
import librosa
import soundfile as sf
import yaml
from pathlib import Path

# Import musiclib modules (assumes running from repo root)
from musiclib import io_utils, dsp_utils, audio_analyzer
from musiclib.logger import get_logger, log_success
from musiclib.exceptions import SilentArtifact

logger = get_logger(__name__)

# Configuration for this run
DEFAULT_CONFIG = {
    "global": {
        "sample_rate": 44100,
        "output_bit_depth": 24,
        "target_peak_dbfs": -1.0
    },
    "paths": {
        "source_audio_dir": "source_audio",
        "export_dir": "export/tr8s"
    },
    "drum_miner": {
        "enabled": True,
        # Onset detection parameters
        "onset_backtrack": True,      # Shift onset to nearest minimum energy (start of attack)
        "pre_max": 20,                # Amount of time before peak to consider for picking
        "post_max": 20,               # Amount of time after peak to consider
        "pre_avg": 100,               # Moving average window before
        "post_avg": 100,              # Moving average window after
        "delta": 0.05,                # Threshold for peak picking
        "wait": 30,                   # Wait N frames before picking next onset (prevents double hits)
        
        # Slicing parameters
        "slice_mode": "onset_to_onset",  # 'onset_to_onset' or 'fixed_length'
        "fixed_length_sec": 0.5,         # If fixed_length
        "max_length_sec": 0.8,           # Max length for any slice
        "min_length_sec": 0.05,          # Min length to be saved
        "fade_in_ms": 2,                 # Super fast fade in to de-click
        "fade_out_ms": 20,               # Short fade out
        
        # Filtering parameters
        "min_peak_db": -30.0,            # Ignore very quiet hits
        "max_peak_db": -0.5,             # Ignore clipped hits (optional)
        "max_saved_per_file": 2000       # Max drums to extract per file
    }
}

def deep_update(base: dict, override: dict) -> dict:
    """Recursively merge dictionaries without losing nested defaults."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def extract_drum_slices(audio: np.ndarray, sr: int, config: dict) -> list:
    """
    Detect onsets and slice audio into individual hits.
    """
    dm_config = config['drum_miner']

    logger.info("    Analyzing onsets...")

    # onset_detect returns frame indices
    onset_frames = librosa.onset.onset_detect(
        y=audio,
        sr=sr,
        backtrack=dm_config['onset_backtrack'],
        pre_max=dm_config['pre_max'],
        post_max=dm_config['post_max'],
        pre_avg=dm_config['pre_avg'],
        post_avg=dm_config['post_avg'],
        delta=dm_config['delta'],
        wait=dm_config['wait'],
        units='samples' # Get samples directly
    )

    if len(onset_frames) == 0:
        return []

    logger.info(f"    Found {len(onset_frames)} raw onsets.")
    
    slices = []
    
    for i, start_sample in enumerate(onset_frames):
        # Determine end sample
        if i < len(onset_frames) - 1:
            end_sample = onset_frames[i+1]
        else:
            end_sample = len(audio)
            
        # Enforce max length
        max_len_samples = int(dm_config['max_length_sec'] * sr)
        if (end_sample - start_sample) > max_len_samples:
            end_sample = start_sample + max_len_samples
            
        # Check minimum length
        min_len_samples = int(dm_config['min_length_sec'] * sr)
        if (end_sample - start_sample) < min_len_samples:
            continue
            
        # Extract audio
        drum_audio = audio[start_sample:end_sample]
        
        # Check peak level
        peak_db = dsp_utils.linear_to_db(np.max(np.abs(drum_audio)))
        if peak_db < dm_config['min_peak_db']:
            continue
        if peak_db > dm_config['max_peak_db']:
            # Maybe too hot, but usually we want loud drums. 
            # If strictly clipping, maybe skip? 
            # Let's keep it but warn? Or just keep.
            pass
            
        # Apply fades
        fade_in_samples = int(dm_config['fade_in_ms'] * sr / 1000)
        fade_out_samples = int(dm_config['fade_out_ms'] * sr / 1000)
        
        drum_audio = dsp_utils.apply_fade_in(drum_audio, fade_in_samples)
        drum_audio = dsp_utils.apply_fade_out(drum_audio, fade_out_samples)

        # Normalize (skip if audio is silent/invalid)
        try:
            drum_audio = dsp_utils.normalize_audio(drum_audio, config['global']['target_peak_dbfs'])
        except SilentArtifact as e:
            logger.debug(f"Skipping drum slice: {e}")
            continue

        slices.append(drum_audio)
        
        if len(slices) >= dm_config['max_saved_per_file']:
            break
            
    return slices

def main():
    parser = argparse.ArgumentParser(description="Mine drum/percussion sounds")
    parser.add_argument('--config', type=str, help='Path to config (optional)')
    parser.add_argument('--source', type=str, required=True, help='Source audio file path')
    args = parser.parse_args()
    
    # Setup config
    config = copy.deepcopy(DEFAULT_CONFIG)
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            user_config = yaml.safe_load(f)
            if isinstance(user_config, dict):
                deep_update(config, user_config)
            else:
                logger.warning(f"Ignoring invalid config format in {args.config}")
    # Basic validation of required sections
    for section in ("paths", "global", "drum_miner"):
        if section not in config:
            logger.error(f"Config missing required section '{section}'")
            return 1

    # Paths
    source_path = args.source
    export_base = config['paths']['export_dir']

    if not os.path.exists(source_path):
        logger.error(f"Source not found: {source_path}")
        return 1

    logger.info(f"\n[DRUM MINER] Processing: {source_path}")
    
    # Load audio
    sr = config['global']['sample_rate']
    try:
        audio, _ = io_utils.load_audio(source_path, sr=sr, mono=True)
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        return 1

    if audio is None:
        logger.error("Audio load returned None")
        return 1

    # Extract
    slices = extract_drum_slices(audio, sr, config)
    logger.info(f"    → Extracted {len(slices)} valid drum slices.")
    
    # Save
    stem = io_utils.get_filename_stem(source_path)
    output_dir = os.path.join(export_base, stem, "drums")
    os.makedirs(output_dir, exist_ok=True)
    
    saved_count = 0
    for i, drum_audio in enumerate(slices):
        filename = f"{stem}_drum_{i+1:03d}.wav"
        out_path = os.path.join(output_dir, filename)

        # Compute minimal metadata for grading?
        # For now just save everything we found

        if not io_utils.save_audio(out_path, drum_audio, sr, bit_depth=24):
            logger.warning(f"    Failed to save: {out_path}")
            continue
        saved_count += 1
        if saved_count % 50 == 0:
            logger.info(f"    Saved {saved_count}...")

    log_success(logger, f"Saved {saved_count} drum/percussion files to {output_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
