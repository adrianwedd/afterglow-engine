#!/usr/bin/env python3
"""
curate_best.py: Select top N samples from each category based on audio features.
"""

import os
import shutil
import numpy as np
import librosa
from musiclib import dsp_utils

def score_sample(filepath: str, category: str) -> float:
    """
    Compute a 'quality' score for a sample based on its category.
    Higher is better.
    """
    try:
        # Load with default SR to ensure consistency, or native?
        # Native is faster.
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
        # Penalize: Clipping
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
        
        # Penalize "raw" pads if we have "processed" ones? 
        # Actually user asked for "gold and gems". 
        # The processed drones (warm/airy) are often better than raw.
        # If filename contains "original_loop", it's a drone.
        
    elif category == "swells":
        # Prefer: Dynamic range, movement
        hop = 512
        if len(y) > 2048:
            frame_rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
            rms_var = np.var(frame_rms)
            score += rms_var * 1000.0
        else:
            score -= 100 # Too short for a swell
            
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

def find_files(roots, patterns):
    """Find files matching patterns in given roots."""
    found = []
    for root_dir in roots:
        if not os.path.exists(root_dir): continue
        for root, dirs, files in os.walk(root_dir):
            if "best_of_collection" in root: continue
            for f in files:
                if not f.endswith(".wav"): continue
                # check patterns
                match = False
                for p in patterns:
                    if p in f.lower() or p in root.lower():
                        match = True
                        break
                if match:
                    found.append(os.path.join(root, f))
    return found

def main():
    # Define search roots
    search_roots = [
        "export/tr8s",
        "archive/temp_work_impossible_extraction/export/tr8s"
    ]
    
    output_dir = "export/tr8s/08 - The Impossible/best_of_collection"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # Define categories and their search patterns
    # (Category Name, [Keywords])
    categories = {
        "drums": (["drum"], ["hiss", "loop", "pad", "silence", "swell"]), # (Include, Exclude)
        "silences": (["silence"], []),
        "hiss": (["hiss"], []),
        "pads": (["pad", "loop"], ["swell", "drum", "hiss", "silence"]), # Catch raw pads and drone loops
        "swells": (["swell"], [])
    }
    
    for cat, (includes, excludes) in categories.items():
        print(f"Scanning category: {cat}...")
        
        # 1. Gather candidates
        candidates = []
        for root_dir in search_roots:
            if not os.path.exists(root_dir): continue
            for root, dirs, files in os.walk(root_dir):
                if "best_of_collection" in root: continue
                
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
            # Optimization: for large sets (drums), maybe don't score ALL if we just want top 10?
            # But we need the best. 500 is fast enough.
            if i % 100 == 0 and i > 0: print(f"    Scoring {i}/{len(candidates)}...")
            s = score_sample(c, cat)
            scored.append((s, c))
            
        # 3. Sort & Pick
        scored.sort(key=lambda x: x[0], reverse=True)
        top_n = scored[:10]
        
        # 4. Copy
        cat_dir = os.path.join(output_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        for score, path in top_n:
            fname = os.path.basename(path)
            # Handle potential name collisions if coming from different source folders
            dest_path = os.path.join(cat_dir, fname)
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(fname)
                dest_path = os.path.join(cat_dir, f"{name}_{np.random.randint(1000)}{ext}")
                
            shutil.copy2(path, dest_path)
            print(f"    Picked: {os.path.basename(dest_path)} (Score: {score:.1f})")

if __name__ == "__main__":
    main()