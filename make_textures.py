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
import tempfile
import shutil
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
  export_dir: export/tr8s     # Output directory (TR-8S compatible)

# Pad miner settings (sustained segment extraction)
pad_miner:
  target_durations_sec: [2.0] # List of durations for extracted pads (v0.8)
  min_rms_db: -40.0                     # Minimum RMS level (dB)
  max_rms_db: -10.0                     # Maximum RMS level (dB) - too loud = reject
  max_onset_rate_per_second: 3.0        # Max onsets/sec (too high = too percussive)
  spectral_flatness_threshold: 0.5      # Lower = more tonal (0-1 scale)
  max_candidates_per_file: 3            # How many pads to extract per source file
  loop_crossfade_ms: 100                # Loop smoothing crossfade (v0.8)
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

  pitch_shift_range:                    # Bidirectional pitch range (v0.8)
    min: -7                             # Lower bound (semitones)
    max: 7                              # Upper bound (semitones)

  overlap_ratio: 0.65                   # Grain overlap (0.5-1.0)
  lowpass_hz: 8000                      # Post-processing low-pass (optional)
  clouds_per_source: 2                  # Number of cloud variations per source
  target_peak_dbfs: -3.0                # Gentler normalization for dense overlaps

# Hiss / air texture settings
hiss:
  # Hiss loop parameters
  loop_duration_sec: 1.5                # Duration of hiss loops
  highpass_hz: 6000                     # High-pass cutoff for noise
  bandpass_low_hz: 4000                 # Band-pass low cutoff (v0.8)
  bandpass_high_hz: 14000               # Band-pass high cutoff (v0.8)
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

# Export settings (v0.6)
export:
  pads_stereo: false                    # Output pads as stereo
  clouds_stereo: false                  # Output clouds as stereo
  swells_stereo: false                  # Output swells as stereo
  hiss_stereo: false                    # Output hiss as stereo

# Brightness tagging (v0.5)
brightness_tags:
  enabled: true                         # Enable dark/mid/bright classification
  centroid_low_hz: 1500                 # Dark ↔ mid threshold
  centroid_high_hz: 3500                # Mid ↔ bright threshold

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

# Curation (v0.5)
curation:
  auto_delete_grade_f: false            # Automatically delete "Fail" grade outputs

  thresholds:
    min_rms_db: -60.0                   # Silence threshold
    max_rms_db: -1.0                    # Near-clipping threshold
    max_dc_offset: 0.15                 # DC offset limit
    max_crest_factor: 20.0              # Extreme transient limit

# Musical context (v0.7)
musicality:
  target_key: null                      # Target key for transposition (e.g., "C", "Am")
                                        # null = no transposition

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
        print(f"\n[✓] Saved {total} pad(s) to {config['paths']['export_dir']}/ ")
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
        print(f"\n[✓] Saved {total} cloud(s) to {config['paths']['export_dir']}/ ")
    else:
        print(f"\n[!] No clouds generated (check {config['paths']['pad_sources_dir']})")


def dry_run_preview(config: dict, operations: list) -> None:
    """
    Preview what would be generated without creating files.

    Args:
        config: Configuration dictionary
        operations: List of operation names ['mine_pads', 'make_drones', etc.]
    """
    print("\n" + "=" * 60)
    print(" DRY RUN PREVIEW")
    print("=" * 60)
    print("\nNo files will be created. Scanning source directories...\n")

    total_estimate = 0

    if 'mine_pads' in operations:
        source_dir = config['paths']['source_audio_dir']
        files = io_utils.discover_audio_files(source_dir)
        max_candidates = config['pad_miner']['max_candidates_per_file']
        estimate = len(files) * max_candidates
        total_estimate += estimate

        print(f"[MINE PADS]")
        print(f"  Source directory: {source_dir}")
        print(f"  Audio files found: {len(files)}")
        print(f"  Max candidates per file: {max_candidates}")
        print(f"  → Estimated pads: ~{estimate}")
        print()

    if 'make_drones' in operations:
        pad_sources_dir = config['paths']['pad_sources_dir']
        files = io_utils.discover_audio_files(pad_sources_dir)

        # Estimate: pads + swells per source
        variants = len(config['drones'].get('pad_variants', ['warm']))
        pitch_shifts = len(config['drones'].get('pitch_shift_semitones', [0]))
        time_stretches = len(config['drones'].get('time_stretch_factors', [1.0]))
        reversal = 2 if config['drones'].get('enable_reversal', False) else 1

        pads_per_source = variants * pitch_shifts * time_stretches * reversal
        swells_per_source = pitch_shifts * time_stretches * reversal

        total_drones = len(files) * (pads_per_source + swells_per_source)
        total_estimate += total_drones

        print(f"[MAKE DRONES]")
        print(f"  Source directory: {pad_sources_dir}")
        print(f"  Audio files found: {len(files)}")
        print(f"  Variants: {variants} pad types × {pitch_shifts} pitches × {time_stretches} stretches × {reversal} directions")
        print(f"  → Estimated pads: ~{len(files) * pads_per_source}")
        print(f"  → Estimated swells: ~{len(files) * swells_per_source}")
        print()

    if 'make_clouds' in operations:
        pad_sources_dir = config['paths']['pad_sources_dir']
        files = io_utils.discover_audio_files(pad_sources_dir)
        clouds_per_source = config['clouds'].get('clouds_per_source', 2)
        estimate = len(files) * clouds_per_source
        total_estimate += estimate

        print(f"[MAKE CLOUDS]")
        print(f"  Source directory: {pad_sources_dir}")
        print(f"  Audio files found: {len(files)}")
        print(f"  Clouds per source: {clouds_per_source}")
        print(f"  Grains per cloud: {config['clouds'].get('grains_per_cloud', 200)}")
        print(f"  → Estimated clouds: ~{estimate}")
        print()

    if 'make_hiss' in operations:
        drums_dir = config['paths']['drums_dir']
        files = io_utils.discover_audio_files(drums_dir)
        loops_per_source = config['hiss'].get('hiss_loops_per_source', 2)
        flickers = config['hiss'].get('flicker_count', 4)
        estimate = len(files) * (loops_per_source + flickers)
        total_estimate += estimate

        print(f"[MAKE HISS]")
        print(f"  Source directory: {drums_dir}")
        print(f"  Audio files found: {len(files)}")
        print(f"  Loops per source: {loops_per_source}")
        print(f"  Flickers per source: {flickers}")
        print(f"  → Estimated textures: ~{estimate}")
        print()

    print("=" * 60)
    print(f" TOTAL ESTIMATED OUTPUT: ~{total_estimate} files")
    print(f" Export directory: {config['paths']['export_dir']}")
    print("=" * 60)
    print("\nTo generate these files, run without --dry-run flag.")


def run_make_hiss(config: dict) -> None:
    """Execute hiss/flicker generation."""
    hiss_dict = hiss_maker.make_all_hiss(config)
    if hiss_dict:
        total = hiss_maker.save_hiss(hiss_dict, config, manifest=config.get("_manifest"))
        print(f"\n[✓] Saved {total} hiss audio file(s) to {config['paths']['export_dir']}/ ")
    else:
        print(f"\n[!] No hiss textures generated")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sound-design textures for Roland TR-8S",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python make_textures.py --all --dry-run    # Preview what would be generated
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
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be generated without creating files'
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

    # Determine which operations to run
    operations = []
    if args.all or args.mine_pads:
        operations.append('mine_pads')
    if args.all or args.make_drones:
        operations.append('make_drones')
    if args.all or args.make_clouds:
        operations.append('make_clouds')
    if args.all or args.make_hiss:
        operations.append('make_hiss')

    # Handle dry-run mode
    if args.dry_run:
        dry_run_preview(config, operations)
        return 0

    # Normal execution mode
    ensure_directories(config)

    print("\n" + "=" * 60)
    print(" Music Texture Generator for TR-8S")
    print("=" * 60)

    # Run requested operations
    if 'mine_pads' in operations:
        run_mine_pads(config)

    if 'make_drones' in operations:
        run_make_drones(config)

    if 'make_clouds' in operations:
        run_make_clouds(config)

    if 'make_hiss' in operations:
        run_make_hiss(config)

    # Emit manifest if any rows were collected
    manifest = config.get("_manifest", [])
    if manifest:
        export_dir = config['paths']['export_dir']
        os.makedirs(export_dir, exist_ok=True)
        manifest_path = os.path.join(export_dir, "manifest.csv")
        fieldnames = sorted({k for row in manifest for k in row.keys()})

        # Atomic write: write to temp file first, then move
        # This prevents race conditions and partial writes if interrupted
        with tempfile.NamedTemporaryFile(mode='w', dir=export_dir, delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest)
            tmp_path = tmp.name

        # Atomic move (POSIX guarantees atomicity on same filesystem)
        shutil.move(tmp_path, manifest_path)
        print(f"[manifest] Wrote {len(manifest)} rows to {manifest_path}")

    print("\n" + "=" * 60)
    print(" Export directory: " + config['paths']['export_dir'])
    print(" Ready to copy to TR-8S SD card!")
    print("=" * 60 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())