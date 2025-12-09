#!/usr/bin/env python3
"""
format_for_tr8s.py: Organize and rename files for Roland TR-8S import.
Structure:
  KIT_NAME/
    DRUMS/
      KICK_xxx.WAV
      SNARE_xxx.WAV
    PADS/
    FX/
"""

import os
import shutil
import argparse
import re

def clean_filename(name):
    # Remove "08 - The Impossible" etc.
    # Keep it simple: 8 chars? TR-8S supports long names but short is better for screen.
    # Let's try to preserve meaningful tags.
    
    name = name.lower()
    name = os.path.splitext(name)[0]
    
    # Remove common prefixes from mining
    name = re.sub(r'^\d+\s*-\s*[\w\s]+_', '', name) # Remove "08 - The Impossible_"
    name = name.replace("original_loop", "loop")
    name = name.replace("original_swell", "swell")
    
    # Map to short codes
    # drum_001 -> BD_01? We don't know if it's a BD.
    # Let's just keep "DRM", "PAD", "SWL", "HIS", "SIL"
    
    if "drum" in name:
        # try to keep number
        num = re.search(r'\d+', name)
        n = num.group() if num else "01"
        return f"DRM_{n}"
        
    elif "pad" in name:
        # pad85_mid -> PAD_85M
        # pad85_mid_loop_warm -> PAD_85MW
        base = "PAD"
        
        # Find number
        num = re.search(r'pad(\d+)', name)
        n = num.group(1) if num else "00"
        
        suffix = ""
        if "bright" in name: suffix += "B"
        elif "dark" in name: suffix += "D"
        elif "warm" in name: suffix += "W"
        elif "mid" in name: suffix += "M"
        
        if "dust" in name: suffix += "X" # Dusted
        
        return f"{base}_{n}{suffix}"
        
    elif "swell" in name:
        # swell01 -> SWL_01
        num = re.search(r'swell(\d+)', name)
        n = num.group(1) if num else "01"
        return f"SWL_{n}"
        
    elif "hiss" in name:
        return f"FX_HISS_{name[-3:]}" # last 3 chars usually number
        
    elif "silence" in name:
        num = re.search(r'\d+', name)
        n = num.group() if num else "01"
        return f"TEX_{n}"
        
    elif "cloud" in name:
         num = re.search(r'\d+', name)
         n = num.group() if num else "01"
         return f"CLD_{n}"

    return name[:8] # Fallback

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--kit_name', default="AG_KIT")
    args = parser.parse_args()
    
    kit_root = os.path.join(args.output_dir, args.kit_name)
    if os.path.exists(kit_root):
        shutil.rmtree(kit_root)
    
    # Create structure
    subfolders = ["DRUMS", "PADS", "FX"]
    for s in subfolders:
        os.makedirs(os.path.join(kit_root, s), exist_ok=True)
        
    print(f"[FORMATTER] Formatting kit '{args.kit_name}' in {kit_root}...")
    
    count = 0
    
    for root, dirs, files in os.walk(args.input_dir):
        for f in files:
            if not f.lower().endswith('.wav'): continue
            
            src_path = os.path.join(root, f)
            
            # Determine category
            cat = "FX" # Default
            lower_f = f.lower()
            
            if "drum" in lower_f: cat = "DRUMS"
            elif "pad" in lower_f and "swell" not in lower_f and "cloud" not in lower_f: cat = "PADS"
            elif "cloud" in lower_f: cat = "PADS" # Clouds are texture/pads
            # Swells, Hiss, Silence go to FX
            
            # New Name
            new_name = clean_filename(f)
            # Ensure unique
            dest_folder = os.path.join(kit_root, cat)
            dest_path = os.path.join(dest_folder, new_name + ".WAV")
            
            # Simple collision handling
            uniq = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{new_name}_{uniq}.WAV")
                uniq += 1
            
            shutil.copy2(src_path, dest_path)
            count += 1
            
    print(f"[✓] Formatted {count} samples.")

if __name__ == "__main__":
    main()
