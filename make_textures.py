#!/usr/bin/env python3
"""
make_textures.py: Main CLI entrypoint for sound-design texture generation.

Usage:
  python make_textures.py --all
  python make_textures.py --mine-pads
  python make_textures.py --make-drones
  python make_textures.py --make-clouds
  python make_textures.py --make-hiss
"""

import argparse
import sys
import os
import csv
import yaml
from pathlib import Path

# Import musiclib modules
from musiclib import segment_miner, drone_maker, granular_maker, hiss_maker, io_utils, dsp_utils
from validate_config import validate_config


DEFAULT_CONFIG_YAML = """# Global audio settings
global:
  sample_rate: 44100          # Sample rate in Hz for all output
  output_bit_depth: 24        # 16 or 24-bit WAV output
  target_peak_dbfs: -1.0      # Target peak level for normalization

# Directory paths
paths:
  source_audio_dir: source_audio
  pad_sources_dir: pad_sources
  drums_dir: drums
  export_dir: export

# Pad miner settings (sustained segment extraction)
pad_miner:
  target_duration_sec: 2.0              # Duration of extracted pad segments
  min_rms_db: -40.0                     # Minimum RMS level (dB)
  max_rms_db: -10.0                     # Maximum RMS level (dB) - too loud = reject
  max_onset_rate_per_second: 3.0        # Max onsets/sec (too high = too percussive)
  spectral_flatness_threshold: 0.5      # Lower = more tonal (0-1 scale)
  max_candidates_per_file: 3            # How many pads to extract per source file
  crossfade_ms: 100                     # Crossfade length for loop smoothing
  window_hop_sec: 0.5                   # Hop size for sliding window analysis

# Drone / pad / swell maker settings
drones:
  # Pad loop parameters
  pad_loop_duration_sec: 2.0            # Target duration for loopable pads
  pad_variants:
    - warm                               # Low-pass filtered variant
    - airy                               # High-pass filtered variant
    - dark                               # Darker, more low-end

  # Tonal filtering for variants
  warm_lowpass_hz: 3000                 # Warm variant: low-pass cutoff
  airy_highpass_hz: 6000                # Airy variant: high-pass cutoff
  dark_high_cut_hz: 1500                # Dark variant: aggressive high-cut

  # Swell parameters
  swell_duration_sec: 6.0               # Target duration for swell one-shots
  fade_in_sec: 0.5                      # Fade-in duration for swells
  fade_out_sec: 1.5                     # Fade-out duration for swells

  # Processing options
  pitch_shift_semitones: [0, 7, 12]     # Pitch shifts to apply (semitones)
  time_stretch_factors: [1.0, 1.5, 2.0]  # Time-stretch factors (1.0 = original)
  enable_reversal: true                 # Whether to create reversed variants

# Granular cloud settings
clouds:
  grain_length_min_ms: 50               # Minimum grain length
  grain_length_max_ms: 150              # Maximum grain length
  grains_per_cloud: 200                 # Number of grains per cloud
  cloud_duration_sec: 6.0               # Target output duration
  max_pitch_shift_semitones: 7          # Max random pitch shift per grain
  overlap_ratio: 0.65                   # Grain overlap (0.5-1.0)
  lowpass_hz: 8000                      # Post-processing low-pass (optional)
  clouds_per_source: 2                  # Number of cloud variations per source

# Hiss / air texture settings
hiss:
  # Hiss loop parameters
  loop_duration_sec: 1.5                # Duration of hiss loops
  highpass_hz: 6000                     # High-pass cutoff for noise
  band_low_hz: 4000                     # Band-pass low cutoff (optional)
  band_high_hz: 14000                   # Band-pass high cutoff (optional)
  use_bandpass: true                    # Use band-pass instead of high-pass
  tremolo_rate_hz: 3.0                  # Amplitude modulation rate
  tremolo_depth: 0.6                    # Tremolo depth (0-1)
  hiss_loops_per_source: 2              # Number of hiss loop variants

  # Flicker burst parameters
  flicker_min_ms: 50                    # Minimum flicker duration
  flicker_max_ms: 300                   # Maximum flicker duration
  flicker_count: 4                      # Number of flicker one-shots to generate

  # Synthetic noise fallback
  use_synthetic_noise: true             # Use white noise if no drum files
  synthetic_noise_level_db: -10.0       # dB level for synthetic noise

# Audio pre-analysis and quality filtering (v0.3)
pre_analysis:
  enabled: true                         # Enable per-file quality analysis
  analysis_window_sec: 1.0              # Analysis window size (seconds)
  analysis_hop_sec: 0.5                 # Analysis hop size (seconds)

  # Stability filters (identify usable regions)
  max_onset_rate_hz: 3.0                # Max onsets per second (low = sustained)
  min_rms_db: -40.0                     # Minimum RMS level
  max_rms_db: -10.0                     # Maximum RMS level (avoid clipping)
  max_dc_offset: 0.1                    # Max DC bias (0-1 scale)
  max_crest_factor: 10.0                # Max peak/RMS ratio (low = sustained)

  # Quality scoring for grains
  grain_quality_threshold: 0.4          # Min quality score to accept grain
  skip_clipped_regions: true            # Avoid regions with clipping
  skip_transient_regions: true          # Avoid percussive regions

# Reproducibility
reproducibility:
  random_seed: null                     # Set to an integer for deterministic results
                                        # null = random (different results each run)
                                        # Example: random_seed: 42
"""


def load_or_create_config(config_path: str = "config.yaml") -> dict:
    """
    Load config from file or create default if missing.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configuration dictionary
    """
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            print(f"[*] Loaded config from {config_path}")
            return config
    else:
        print(f"[*] Config not found, creating default at {config_path}")
        with open(config_path, 'w') as f:
            f.write(DEFAULT_CONFIG_YAML)
        config = yaml.safe_load(DEFAULT_CONFIG_YAML)
        return config


def ensure_directories(config: dict) -> None:
    """Create required directories if they don't exist."""
    dirs_to_create = [
        config['paths']['source_audio_dir'],
        config['paths']['pad_sources_dir'],
        config['paths']['drums_dir'],
        config['paths']['export_dir'],
    ]

    for directory in dirs_to_create:
        os.makedirs(directory, exist_ok=True)


def run_mine_pads(config: dict) -> None:
    """Execute pad mining."""
    pad_dict = segment_miner.mine_all_pads(config)
    if pad_dict:
        total = segment_miner.save_mined_pads(pad_dict, config, manifest=config.get("_manifest"))
        print(f"\n[✓] Saved {total} pad(s) to {config['paths']['export_dir']}/")
    else:
        print(f"\n[!] No pads mined (check {config['paths']['source_audio_dir']})")


def run_make_drones(config: dict) -> None:
    """Execute drone/swell generation."""
    drone_dict = drone_maker.process_pad_sources(config)
    if drone_dict:
        pads, swells = drone_maker.save_drone_outputs(drone_dict, config, manifest=config.get("_manifest"))
        print(f"\n[✓] Saved {pads} pad(s) and {swells} swell(s)")
    else:
        print(f"\n[!] No drone sources processed (check {config['paths']['pad_sources_dir']})")


def run_make_clouds(config: dict) -> None:
    """Execute granular cloud generation."""
    clouds_dict = granular_maker.process_cloud_sources(config)
    if clouds_dict:
        total = granular_maker.save_clouds(clouds_dict, config, manifest=config.get("_manifest"))
        print(f"\n[✓] Saved {total} cloud(s) to {config['paths']['export_dir']}/")
    else:
        print(f"\n[!] No clouds generated (check {config['paths']['pad_sources_dir']})")


def run_make_hiss(config: dict) -> None:
    """Execute hiss/flicker generation."""
    hiss_dict = hiss_maker.make_all_hiss(config)
    if hiss_dict:
        total = hiss_maker.save_hiss(hiss_dict, config, manifest=config.get("_manifest"))
        print(f"\n[✓] Saved {total} hiss audio file(s) to {config['paths']['export_dir']}/")
    else:
        print(f"\n[!] No hiss textures generated")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sound-design textures for Roland TR-8S",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python make_textures.py --all              # Generate everything
  python make_textures.py --mine-pads        # Extract pads from source_audio/
  python make_textures.py --make-drones      # Create loops & swells from pad_sources/
  python make_textures.py --make-clouds      # Generate granular clouds
  python make_textures.py --make-hiss        # Create hiss & flicker textures
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all texture generation steps'
    )
    parser.add_argument(
        '--mine-pads',
        action='store_true',
        help='Mine sustained segments from source_audio/'
    )
    parser.add_argument(
        '--make-drones',
        action='store_true',
        help='Generate pad loops and swells from pad_sources/'
    )
    parser.add_argument(
        '--make-clouds',
        action='store_true',
        help='Create granular cloud textures'
    )
    parser.add_argument(
        '--make-hiss',
        action='store_true',
        help='Generate hiss loops and flicker bursts'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config.yaml (default: config.yaml)'
    )

    args = parser.parse_args()

    # If no subcommand specified, show help
    if not any([args.all, args.mine_pads, args.make_drones, args.make_clouds, args.make_hiss]):
        parser.print_help()
        return 1

    # Load or create config
    config = load_or_create_config(args.config)
    # Validate config early to catch obvious errors
    validate_config(config)

    # Manifest accumulator (shared across phases)
    config["_manifest"] = []

    # Set random seed if specified (for reproducible results)
    reproducibility_config = config.get('reproducibility', {})
    random_seed = reproducibility_config.get('random_seed', None)
    if random_seed is not None:
        dsp_utils.set_random_seed(random_seed)
        print(f"[*] Random seed set to {random_seed} (reproducible mode)")

    # Ensure all required directories exist
    ensure_directories(config)

    print("\n" + "=" * 60)
    print(" Music Texture Generator for TR-8S")
    print("=" * 60)

    # Run requested operations
    if args.all or args.mine_pads:
        run_mine_pads(config)

    if args.all or args.make_drones:
        run_make_drones(config)

    if args.all or args.make_clouds:
        run_make_clouds(config)

    if args.all or args.make_hiss:
        run_make_hiss(config)

    # Emit manifest if any rows were collected
    manifest = config.get("_manifest", [])
    if manifest:
        export_dir = config['paths']['export_dir']
        os.makedirs(export_dir, exist_ok=True)
        manifest_path = os.path.join(export_dir, "manifest.csv")
        fieldnames = sorted({k for row in manifest for k in row.keys()})
        with open(manifest_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest)
        print(f"[manifest] Wrote {len(manifest)} rows to {manifest_path}")

    print("\n" + "=" * 60)
    print(" Export directory: " + config['paths']['export_dir'])
    print(" Ready to copy to TR-8S SD card!")
    print("=" * 60 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
