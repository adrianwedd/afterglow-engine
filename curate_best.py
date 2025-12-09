#!/usr/bin/env python3
"""
curate_best.py: Select top N samples from each category based on audio features.
"""

import os
import shutil
import argparse
import numpy as np
import librosa
from musiclib import dsp_utils

def score_sample(filepath: str, category: str) -> float:
    """
    Compute a 'quality' score for a sample based on its category.
    Higher is better.
    """
    try:
        y, sr = librosa.load(filepath, sr=None)
    except Exception:
        return -999.0
        
    if len(y) == 0:
        return -999.0
        
    rms = np.sqrt(np.mean(y**2))
    rms_db = 20 * np.log10(rms + 1e-9)
    peak = np.max(np.abs(y))
    crest = peak / rms if rms > 0 else 0
    
    score = 0.0
    
    if category == "drums":
        # Prefer: High crest factor (punchy), Loud-ish
        if peak >= 0.99: score -= 100
        score += crest * 2.0
        score += rms_db * 0.1
        
    elif category == "pads" or category == "drones":
        # Prefer: Stability, Tonality, Richness
        flatness = np.mean(librosa.feature.spectral_flatness(y=y))
        score -= flatness * 20.0 
        if rms_db < -50: score -= 50
        duration = len(y) / sr
        score += duration * 2.0
        
    elif category == "swells":
        # Prefer: Dynamic range, movement
        hop = 512
        if len(y) > 2048:
            frame_rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
            rms_var = np.var(frame_rms)
            score += rms_var * 1000.0
        else:
            score -= 100 
            
    elif category == "silences":
        # Prefer: Consistency, non-zero
        if rms_db < -70: score -= 100 
        if rms_db > -30: score -= 50
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        if centroid > 0:
            score += np.log10(centroid)
            
    elif category == "hiss":
        # Prefer: High frequency content
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        score += centroid / 1000.0
        
    return score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_root', required=True, help="Root directory to search (e.g. export/tr8s)")
    parser.add_argument('--output_root', required=True, help="Directory to save best picks")
    parser.add_argument('--force', action='store_true', help="Overwrite output directory if exists")
    args = parser.parse_args()
    
    if os.path.exists(args.output_root):
        if args.force:
            print(f"[*] Removing existing output directory: {args.output_root}")
            shutil.rmtree(args.output_root)
        else:
            print(f"[!] Output directory exists: {args.output_root}")
            print("    Use --force to overwrite.")
            return

    os.makedirs(args.output_root)
    
    # Define categories and their search patterns
    categories = {
        "drums": (["drum"], ["hiss", "loop", "pad", "silence", "swell"]), 
        "silences": (["silence"], []),
        "hiss": (["hiss"], []),
        "pads": (["pad", "loop"], ["swell", "drum", "hiss", "silence"]), 
        "swells": (["swell"], [])
    }
    
    for cat, (includes, excludes) in categories.items():
        print(f"Scanning category: {cat}...")
        
        # 1. Gather candidates
        candidates = []
        if not os.path.exists(args.input_root):
             print(f"  Input root not found: {args.input_root}")
             continue
             
        for root, dirs, files in os.walk(args.input_root):
            # Don't recurse into output dir if it's inside input
            if os.path.abspath(args.output_root) in os.path.abspath(root): continue
            
            for f in files:
                if not f.endswith(".wav"): continue
                
                f_lower = f.lower()
                
                # Must match at least one include
                has_include = False
                for inc in includes:
                    if inc in f_lower:
                        has_include = True
                        break
                if not has_include: continue
                
                # Must NOT match any exclude
                has_exclude = False
                for exc in excludes:
                    if exc in f_lower:
                        has_exclude = True
                        break
                if has_exclude: continue
                
                candidates.append(os.path.join(root, f))
        
        print(f"  Found {len(candidates)} candidates.")
        if not candidates: continue
        
        # 2. Score
        scored = []
        for i, c in enumerate(candidates):
            if i % 100 == 0 and i > 0: print(f"    Scoring {i}/{len(candidates)}...")
            s = score_sample(c, cat)
            scored.append((s, c))
            
        # 3. Sort & Pick
        scored.sort(key=lambda x: x[0], reverse=True)
        top_n = scored[:10]
        
        # 4. Copy
        cat_dir = os.path.join(args.output_root, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        for score, path in top_n:
            fname = os.path.basename(path)
            dest_path = os.path.join(cat_dir, fname)
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(fname)
                dest_path = os.path.join(cat_dir, f"{name}_{np.random.randint(1000)}{ext}")
                
            shutil.copy2(path, dest_path)
            print(f"    Picked: {os.path.basename(dest_path)} (Score: {score:.1f})")

if __name__ == "__main__":
    main()
