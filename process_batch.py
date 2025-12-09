#!/usr/bin/env python3
"""
process_batch.py: Master batch processor for Afterglow Engine.
Orchestrates mining, curation, synthesis, formatting, and reporting.
"""

import os
import argparse
import subprocess
import shutil
import yaml
import glob

def run_step(cmd, desc):
    print(f"\n>>> [BATCH] {desc}...")
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"!!! Error in step '{desc}': {e}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True, help="Directory containing source audio files")
    parser.add_argument('--project_name', default="AG_BATCH_01")
    parser.add_argument('--config', default="config.yaml")
    args = parser.parse_args()
    
    batch_export_root = os.path.join("export", args.project_name)
    os.makedirs(batch_export_root, exist_ok=True)
    
    # Validate config
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"[!] Failed to load config: {e}")
        return

    if not config or 'paths' not in config:
        print("[!] Invalid config: missing 'paths' section")
        return

    # Update config for batch
    config['paths']['source_audio_dir'] = args.input_dir
    config['paths']['export_dir'] = batch_export_root
    
    temp_config = f"config_{args.project_name}.yaml"
    with open(temp_config, 'w') as f:
        yaml.dump(config, f)
        
    print(f"[*] Batch Config saved to {temp_config}")
    
    # Step A: Mine Pads
    if not run_step(f"python make_textures.py --config {temp_config} --mine-pads --make-drones", "Mining Pads & Drones"):
        return
    
    # Step B: Mine Drums & Silences
    print("\n>>> [BATCH] Mining Drums & Silences...")
    extensions = ['*.flac', '*.wav', '*.aiff', '*.mp3']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(args.input_dir, ext)))
    
    for f in files:
        # Drums
        cmd_drums = f"python mine_drums.py --config {temp_config} --source \"{f}\""
        if not run_step(cmd_drums, f"Drums: {os.path.basename(f)}"):
            pass # Continue to next file even if one fails
        
        # Silences
        cmd_silence = f"python mine_silences.py --source \"{f}\" --export \"{batch_export_root}\""
        if not run_step(cmd_silence, f"Silences: {os.path.basename(f)}"):
            pass
        
    print("\n>>> [BATCH] Curation (Skipped - run curate_best.py manually for now)")
    print(f"\n[✓] Batch processing complete for phase 1. Output in {batch_export_root}")
    print("    Next steps: Curate, Cloud, Dust, Format.")

if __name__ == "__main__":
    main()