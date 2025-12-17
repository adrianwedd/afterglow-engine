#!/usr/bin/env python3
"""
dust_pads.py: Layer hiss/texture onto clean pads to create "dusted" variants.
"""

import os
import argparse
import numpy as np
import soundfile as sf
from musiclib import io_utils, dsp_utils
from musiclib.logger import get_logger, log_success
from musiclib.exceptions import SilentArtifact

logger = get_logger(__name__)

def dust_pad(pad_path, hiss_path, output_path, hiss_db=-12.0, sr=44100):
    # Load Pad
    # io_utils uses librosa.load, which returns (channels, samples) for stereo
    pad, _ = io_utils.load_audio(pad_path, sr=sr, mono=False)
    if pad is None: return False
    
    # Fix Librosa shape (C, N) -> (N, C) if stereo
    # We assume N > C usually.
    if pad.ndim == 2 and pad.shape[0] < pad.shape[1]:
        pad = pad.T
    
    # Load Hiss
    hiss, _ = io_utils.load_audio(hiss_path, sr=sr, mono=False)
    if hiss is None: return False
    
    # Fix Librosa shape for hiss too
    if hiss.ndim == 2 and hiss.shape[0] < hiss.shape[1]:
        hiss = hiss.T
    
    # Ensure Pad is stereo (usually nice for dusting)
    # dsp_utils.mono_to_stereo expects (N,) and returns (N, 2)
    if pad.ndim == 1:
        pad = dsp_utils.mono_to_stereo(pad)
    
    # Ensure Hiss is stereo
    if hiss.ndim == 1:
        hiss = dsp_utils.mono_to_stereo(hiss)
        
    # Loop Hiss to match Pad length
    # Now that we transposed, len() is correct (samples)
    pad_len = len(pad)
    hiss_len = len(hiss)
    
    if hiss_len < pad_len:
        tile_count = int(np.ceil(pad_len / hiss_len))
        # axis=0 is samples now
        hiss_tiled = np.tile(hiss, (tile_count, 1))
        hiss_aligned = hiss_tiled[:pad_len]
    else:
        hiss_aligned = hiss[:pad_len]
        
    # Mix
    hiss_gain = dsp_utils.db_to_linear(hiss_db)
    
    # Simple mix
    mixed = pad + (hiss_aligned * hiss_gain)

    # Normalize (preserve headroom)
    try:
        mixed = dsp_utils.normalize_audio(mixed, -1.0)
    except SilentArtifact as e:
        logger.warning(f"Cannot dust {output_path}: {e}")
        return False

    # Save (using io_utils for export-root containment)
    if not io_utils.save_audio(output_path, mixed, sr, bit_depth=24):
        logger.warning(f"Failed to save (export-root check): {output_path}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pads_dir', required=True)
    parser.add_argument('--hiss_dir', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--mix_db', type=float, default=-12.0)
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get lists
    pads = [os.path.join(args.pads_dir, f) for f in os.listdir(args.pads_dir) if f.endswith('.wav')]
    hisses = [os.path.join(args.hiss_dir, f) for f in os.listdir(args.hiss_dir) if f.endswith('.wav')]

    if not pads or not hisses:
        logger.warning("Missing pads or hiss files.")
        return

    logger.info(f"[DUSTER] Mixing {len(pads)} pads with random hiss layers...")

    count = 0
    import random

    for pad_p in pads:
        # Pick a random hiss for each pad
        hiss_p = random.choice(hisses)

        fname = os.path.basename(pad_p)
        name, ext = os.path.splitext(fname)
        hiss_name = os.path.splitext(os.path.basename(hiss_p))[0]
        # Shorten hiss name
        if "hiss_" in hiss_name:
            hiss_suffix = hiss_name.replace("hiss_", "")[:8]
        else:
            hiss_suffix = hiss_name[:5]

        out_name = f"{name}_dust_{hiss_suffix}{ext}"
        out_path = os.path.join(args.output_dir, out_name)

        if dust_pad(pad_p, hiss_p, out_path, args.mix_db):
            log_success(logger, f"  Created {out_name}")
            count += 1

    log_success(logger, f"Created {count} dusted pads.")

if __name__ == "__main__":
    main()