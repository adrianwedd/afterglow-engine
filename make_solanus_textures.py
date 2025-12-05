#!/usr/bin/env python3
"""
make_solanus_textures.py

Thin wrapper around the shared pipeline to generate the Solanus texture set
using the current config and musiclib modules. Copies the input file into the
standard `source_audio/` and `pad_sources/` folders, then runs the full
make_textures pipeline so behaviors stay in sync with v0.2+ changes.
"""

import argparse
import shutil
import sys
from pathlib import Path

import make_textures


DEFAULT_INPUT = Path("VA - Dreamy Harbor [2017] [TRESOR291]") / "01 Vainqueur - Solanus (Extracted 2).flac"


def prepare_sources(input_path: Path, config: dict) -> None:
    """Copy the input file into the expected source directories."""
    source_dir = Path(config["paths"]["source_audio_dir"])
    pad_dir = Path(config["paths"]["pad_sources_dir"])
    source_dir.mkdir(parents=True, exist_ok=True)
    pad_dir.mkdir(parents=True, exist_ok=True)

    for target_dir in (source_dir, pad_dir):
        destination = target_dir / input_path.name
        if destination.resolve() == input_path.resolve():
            continue
        shutil.copy2(input_path, destination)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate Solanus textures using the shared pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the Solanus source audio (FLAC/WAV/AIFF/FLAC).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config.yaml (defaults to repo config).",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"[!] Input file not found: {args.input}")
        return 1

    # Load config and ensure dirs
    config = make_textures.load_or_create_config(args.config)
    make_textures.ensure_directories(config)

    # Copy input into pipeline source locations
    prepare_sources(args.input, config)

    print("\n=== Solanus Texture Generation (shared pipeline) ===")
    make_textures.run_mine_pads(config)
    make_textures.run_make_drones(config)
    make_textures.run_make_clouds(config)
    make_textures.run_make_hiss(config)
    print("\n[✓] Solanus textures ready under", config["paths"]["export_dir"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
