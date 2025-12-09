#!/usr/bin/env python3
"""
dust_pads.py: Layer hiss/texture onto clean pads to create "dusted" variants.
"""

import os
import argparse
import numpy as np
import soundfile as sf
from musiclib import io_utils, dsp_utils

def dust_pad(pad_path, hiss_path, output_path, hiss_db=-12.0, sr=44100):
    # Load Pad
    pad, _ = io_utils.load_audio(pad_path, sr=sr, mono=False)
    if pad is None: return False
    
    # Load Hiss
    hiss, _ = io_utils.load_audio(hiss_path, sr=sr, mono=False)
    if hiss is None: return False
    
    # Ensure Pad is stereo (usually nice for dusting)
    if pad.ndim == 1:
        pad = dsp_utils.mono_to_stereo(pad)
    
    # Ensure Hiss is stereo
    if hiss.ndim == 1:
        hiss = dsp_utils.mono_to_stereo(hiss)
        
    # Loop Hiss to match Pad length
    pad_len = len(pad)
    hiss_len = len(hiss)
    
    if hiss_len < pad_len:
        tile_count = int(np.ceil(pad_len / hiss_len))
        hiss_tiled = np.tile(hiss, (tile_count, 1))
        hiss_aligned = hiss_tiled[:pad_len]
    else:
        hiss_aligned = hiss[:pad_len]
        
    # Mix
    hiss_gain = dsp_utils.db_to_linear(hiss_db)
    
    # Simple mix
    mixed = pad + (hiss_aligned * hiss_gain)
    
    # Normalize (preserve headroom)
    mixed = dsp_utils.normalize_audio(mixed, -1.0)
    
    # Save
    sf.write(output_path, mixed, sr, subtype='PCM_24')
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
        print("Missing pads or hiss files.")
        return
    
    print(f"[DUSTER] Mixing {len(pads)} pads with random hiss layers...")
    
    count = 0
    import random
    
    for pad_p in pads:
        # Pick a random hiss for each pad, or maybe all hisses?
        # Let's do 1 variant per pad to keep it manageable, or 2?
        # User asked for "Approach". Let's do 2 variants: 1 random hiss, 1 specific one?
        # Let's just pick one random hiss per pad for now to avoid explosion.
        
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
            print(f"  Created {out_name}")
            count += 1
            
    print(f"[✓] Created {count} dusted pads.")

if __name__ == "__main__":
    main()
