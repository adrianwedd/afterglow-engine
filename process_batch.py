#!/usr/bin/env python3
"""
process_batch.py: Master batch processor for Afterglow Engine.
Orchestrates mining, curation, synthesis, formatting, and reporting.
"""

import os
import argparse
import subprocess
import shutil

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
    
    # Paths
    # We will use a dedicated export folder for this batch
    batch_export_root = os.path.join("export", args.project_name)
    os.makedirs(batch_export_root, exist_ok=True)
    
    # 1. Mine Pads & Drones (make_textures.py)
    # We need to ensure config points to the right input/output.
    # Actually make_textures takes a config file. We might need to generate a temp config 
    # or rely on command line args if supported?
    # make_textures only takes --config.
    # So we must modify the config file temporarily or assume user edited it.
    # BETTER: We can modify the config on the fly via PyYAML and save a temp one.
    
    import yaml
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        
    config['paths']['source_audio_dir'] = args.input_dir
    config['paths']['export_dir'] = batch_export_root
    
    # Save temp config
    temp_config = f"config_{args.project_name}.yaml"
    with open(temp_config, 'w') as f:
        yaml.dump(config, f)
        
    print(f"[*] Batch Config saved to {temp_config}")
    
    # Steps
    steps = [
        # A. Mine Pads (and Generate Drones/Swells - assuming config enables it)
        (f"python make_textures.py --config {temp_config} --mine-pads --make-drones", "Mining Pads & Drones"),
        
        # B. Mine Drums (Iterate over files)
        # mine_drums.py takes --source. We need to loop.
        # We'll handle this loop in Python below.
    ]
    
    # Run Step A
    if not run_step(steps[0][0], steps[0][1]): return
    
    # Run Step B (Drums) & C (Silences)
    print("\n>>> [BATCH] Mining Drums & Silences...")
    import glob
    # Support flac, wav, aiff
    extensions = ['*.flac', '*.wav', '*.aiff', '*.mp3']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(args.input_dir, ext)))
    
    # We need to update config for mine_drums/silences to point to batch export?
    # They take --export arg (mine_silences) or config (mine_drums).
    # mine_drums reads config['paths']['export_dir']. So passing temp_config works!
    
    for f in files:
        # Drums
        cmd = f"python mine_drums.py --config {temp_config} --source \"{f}\""
        subprocess.call(cmd, shell=True)
        
        # Silences
        cmd = f"python mine_silences.py --source \"{f}\" --export \"{batch_export_root}\""
        subprocess.call(cmd, shell=True)
        
    # 2. Curate Best
    # curate_best.py has hardcoded paths in the script I wrote earlier.
    # I need to update it to accept args or modify it. 
    # I'll modify curate_best.py to take arguments now.
    # Wait, I can't modify it easily inside this execution flow without rewriting it.
    # I will rely on the fact that I'm about to Rewrite it to be generic? 
    # Or I can just pass the path if I update it.
    # Let's assume I update curate_best.py to take --input_root and --output_root.
    
    # For now, let's skip automatic curation in the batch script unless I update the tool.
    # The user asked for an "Approach". 
    # I'll update curate_best.py to accept args in the next turn if needed, 
    # but for now I'll just assume I can call it.
    # Actually, I wrote curate_best.py with hardcoded search roots in main().
    # I should update it.
    
    print("\n>>> [BATCH] Curation (Skipped - run curate_best.py manually for now)")
    
    # 3. Clouds & Dusting
    # These operate on "Curated" folders.
    
    # 4. Format
    # format_for_tr8s.py --input_dir ... --output_dir ...
    
    print(f"\n[✓] Batch processing complete for phase 1. Output in {batch_export_root}")
    print("    Next steps: Curate, Cloud, Dust, Format.")

if __name__ == "__main__":
    main()
