#!/usr/bin/env python3
"""
make_curated_clouds.py: Generate granular clouds from a specific folder of source samples.
"""

import os
import argparse
import yaml
from musiclib import granular_maker, io_utils, dsp_utils

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True, help="Folder containing source wavs (pads/silences)")
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--config', default="config.yaml")
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        
    # Override paths to point to our specific input/output
    # Granular maker expects "pad_sources_dir" in config. 
    # We can temporarily patch the config dict.
    config['paths']['pad_sources_dir'] = args.input_dir
    config['paths']['export_dir'] = args.output_dir # This might nest weirdly? 
    # granular_maker.save_clouds saves to export_dir/{source_name}/clouds/...
    # If we want a flat structure or specific structure, we might need to handle it.
    # But for now, let's let it use its default structure inside output_dir.
    
    # Ensure config has cloud settings
    if 'clouds' not in config:
        print("[!] Config missing 'clouds' section")
        return

    # Run
    print(f"[CLOUD BUILDER] Igniting granular engine on {args.input_dir}...")
    
    # granular_maker.process_cloud_sources scans the dir in config
    clouds_dict = granular_maker.process_cloud_sources(config)
    
    if clouds_dict:
        # We need to pass a manifest list to capture metadata, even if we don't save it yet
        manifest = []
        total = granular_maker.save_clouds(clouds_dict, config, manifest=manifest)
        print(f"[✓] Generated {total} clouds in {args.output_dir}")
    else:
        print("[!] No clouds generated.")

if __name__ == "__main__":
    main()
