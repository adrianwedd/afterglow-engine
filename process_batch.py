#!/usr/bin/env python3
"""
process_batch.py: Master batch processor for Afterglow Engine.
Orchestrates mining, curation, synthesis, formatting, and reporting.
"""

import os
import sys
import argparse
import subprocess
import shutil
import yaml
import glob
import atexit
from musiclib.logger import get_logger, log_success

logger = get_logger(__name__)

def run_step(cmd, desc):
    logger.info(f"\n>>> [BATCH] {desc}...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in step '{desc}': {e}")
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
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    if not config or 'paths' not in config:
        logger.error("Invalid config: missing 'paths' section")
        sys.exit(1)

    # Update config for batch
    config['paths']['source_audio_dir'] = args.input_dir
    config['paths']['export_dir'] = batch_export_root

    temp_config = f"config_{args.project_name}.yaml"

    # Register cleanup handler to remove temp config on exit
    def cleanup_temp_config():
        if os.path.exists(temp_config):
            try:
                os.remove(temp_config)
                logger.info(f"Cleaned up temporary config: {temp_config}")
            except Exception as e:
                logger.error(f"Failed to remove temp config {temp_config}: {e}")

    atexit.register(cleanup_temp_config)

    # Write temp config
    with open(temp_config, 'w') as f:
        yaml.dump(config, f)

    logger.info(f"Batch Config saved to {temp_config}")

    batch_success = True

    # Step A: Mine Pads
    if not run_step(["python", "make_textures.py", "--config", temp_config, "--mine-pads", "--make-drones"], "Mining Pads & Drones"):
        batch_success = False

    # Step B: Mine Drums & Silences
    logger.info("\n>>> [BATCH] Mining Drums & Silences...")
    extensions = ['*.flac', '*.wav', '*.aiff', '*.mp3']
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(args.input_dir, ext)))
    
    for f in files:
        # Drums
        cmd_drums = ["python", "mine_drums.py", "--config", temp_config, "--source", f]
        if not run_step(cmd_drums, f"Drums: {os.path.basename(f)}"):
            batch_success = False
        
        # Silences
        cmd_silence = ["python", "mine_silences.py", "--source", f, "--export", batch_export_root]
        if not run_step(cmd_silence, f"Silences: {os.path.basename(f)}"):
            batch_success = False

    logger.info("\n>>> [BATCH] Curation (Skipped - run curate_best.py manually for now)")

    if batch_success:
        log_success(logger, f"\nBatch processing complete for phase 1. Output in {batch_export_root}")
        logger.info("    Next steps: Curate, Cloud, Dust, Format.")
        sys.exit(0)
    else:
        logger.error(f"\nBatch processing completed with ERRORS. Check output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
