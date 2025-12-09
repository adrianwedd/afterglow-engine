#!/usr/bin/env python3
"""
format_for_tr8s.py: Organize and rename files for Roland TR-8S import.
"""

import os
import shutil
import argparse
import re

def clean_filename(name):
    name = name.lower()
    name = os.path.splitext(name)[0]
    name = re.sub(r'^\d+\s*-\s*[\w\s]+_', '', name) 
    name = name.replace("original_loop", "loop")
    name = name.replace("original_swell", "swell")
    
    if "drum" in name:
        num = re.search(r'\d+', name)
        n = num.group() if num else "01"
        return f"DRM_{n}"
        
    elif "pad" in name:
        base = "PAD"
        num = re.search(r'pad(\d+)', name)
        n = num.group(1) if num else "00"
        
        suffix = ""
        if "bright" in name: suffix += "B"
        elif "dark" in name: suffix += "D"
        elif "warm" in name: suffix += "W"
        elif "mid" in name: suffix += "M"
        
        if "dust" in name: suffix += "X" 
        
        return f"{base}_{n}{suffix}"
        
    elif "swell" in name:
        num = re.search(r'swell(\d+)', name)
        n = num.group(1) if num else "01"
        return f"SWL_{n}"
        
    elif "hiss" in name:
        return f"FX_HISS_{name[-3:]}"
        
    elif "silence" in name:
        num = re.search(r'\d+', name)
        n = num.group() if num else "01"
        return f"TEX_{n}"
        
    elif "cloud" in name:
         num = re.search(r'\d+', name)
         n = num.group() if num else "01"
         return f"CLD_{n}"

    return name[:8] 

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--kit_name', default="AG_KIT")
    parser.add_argument('--force', action='store_true', help="Overwrite existing kit if present")
    args = parser.parse_args()
    
    kit_root = os.path.join(args.output_dir, args.kit_name)
    
    if os.path.exists(kit_root):
        if args.force:
            print(f"[*] Removing existing kit: {kit_root}")
            shutil.rmtree(kit_root)
        else:
            print(f"[!] Kit directory exists: {kit_root}")
            print("    Use --force to overwrite.")
            return
    
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
            
            cat = "FX" 
            lower_f = f.lower()
            
            if "drum" in lower_f: cat = "DRUMS"
            elif "pad" in lower_f and "swell" not in lower_f and "cloud" not in lower_f: cat = "PADS"
            elif "cloud" in lower_f: cat = "PADS"
            
            new_name = clean_filename(f)
            dest_folder = os.path.join(kit_root, cat)
            dest_path = os.path.join(dest_folder, new_name + ".WAV")
            
            uniq = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{new_name}_{uniq}.WAV")
                uniq += 1
            
            shutil.copy2(src_path, dest_path)
            count += 1
            
    print(f"[✓] Formatted {count} samples.")

if __name__ == "__main__":
    main()