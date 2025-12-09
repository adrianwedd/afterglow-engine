#!/usr/bin/env python3
"""
mine_silences.py: Extract quiet, textural spaces (room tone, dust, low-level noise).

Usage:
  python mine_silences.py --source "path/to/audio.flac"
"""

import os
import sys
import argparse
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from musiclib import io_utils, dsp_utils

def mine_silences(
    source_path: str,
    export_dir: str,
    sr: int = 44100,
    normalization_target_db: float = -12.0
):
    print(f"\n[SILENCE MINER] Processing: {source_path}")
    
    audio, _ = io_utils.load_audio(source_path, sr=sr, mono=True)
    if audio is None:
        return

    # Configuration for "Soft Silence"
    # We want things that are NOT silent (digital zero) but ARE quiet.
    min_rms_db = -80.0
    max_rms_db = -45.0  # Threshold for "quiet"
    
    # "Shorter" - user requested.
    min_duration_sec = 0.1
    max_duration_sec = 0.6
    
    # Analysis
    # We'll use a sliding window
    # Calculate RMS envelope
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db_env = librosa.amplitude_to_db(rms, ref=1.0)
    
    # Grid strategy with overlap
    chunk_len_samples = int(0.3 * sr) # ~300ms average
    step = int(chunk_len_samples / 2)
    
    found_count = 0
    
    # Output setup
    stem = io_utils.get_filename_stem(source_path)
    output_dir = os.path.join(export_dir, stem, "silences")
    os.makedirs(output_dir, exist_ok=True)
    
    # Limit total extraction to avoid thousands
    max_extracted = 50
    
    # Walk through audio
    for start in range(0, len(audio) - chunk_len_samples, step):
        chunk = audio[start : start + chunk_len_samples]
        
        # 1. Check RMS
        chunk_rms_db = dsp_utils.rms_energy_db(chunk)
        if not (min_rms_db <= chunk_rms_db <= max_rms_db):
            continue
            
        # 2. Check for transients (we want "silence/texture", not "quiet drum hit")
        # High crest factor = transient. Low crest factor = noise/hum.
        peak = np.max(np.abs(chunk))
        rms_val = dsp_utils.db_to_linear(chunk_rms_db)
        crest = peak / rms_val if rms_val > 0 else 0
        
        if crest > 5.0: # Arbitrary threshold: strictly flat(ish) textures
            continue
            
        # 3. Check for digital silence (variance)
        if np.var(chunk) < 1e-9:
            continue
            
        # It's a valid soft silence!
        
        # Normalize to target level (makes silence audible as texture)
        chunk_norm = dsp_utils.normalize_audio(chunk, normalization_target_db)
        
        # Apply fades to avoid clicks
        chunk_norm = dsp_utils.apply_fade_in(chunk_norm, 200) # Short micro-fade
        chunk_norm = dsp_utils.apply_fade_out(chunk_norm, 200)
        
        filename = f"{stem}_silence_{found_count+1:03d}.wav"
        out_path = os.path.join(output_dir, filename)
        sf.write(out_path, chunk_norm, sr, subtype='PCM_24')
        
        found_count += 1
        if found_count >= max_extracted:
            break
            
    print(f"    → Extracted {found_count} soft silence/texture samples.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--export', default='export/tr8s')
    parser.add_argument('--norm_db', type=float, default=-12.0, help="Normalization target in dB")
    args = parser.parse_args()
    
    mine_silences(args.source, args.export, normalization_target_db=args.norm_db)
