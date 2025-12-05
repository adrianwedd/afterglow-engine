#!/usr/bin/env python3
"""
discover_audio.py: Recursively scan repo for audio files and build a catalog.

This script discovers all audio files (WAV, AIFF, FLAC, MP3) in a directory tree,
gathers metadata (duration, sample rate, channels), and exports a catalog in CSV/JSON
format for use in downstream batch workflows.

Usage:
    python discover_audio.py --root . --output audio_catalog.csv
    python discover_audio.py --root . --output audio_catalog.json
    python discover_audio.py --root . --output audio_catalog.csv --format csv
"""

import argparse
import os
import sys
import csv
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# Optional dependencies (graceful fallback)
try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import librosa
except ImportError:
    librosa = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Audio formats to discover
SUPPORTED_FORMATS = {'.wav', '.aiff', '.aif', '.flac', '.mp3'}

# Directories to skip (common non-source folders)
SKIP_DIRS = {
    'venv', '.venv', 'env', '.env',           # Virtual environments
    '.git', '.github', '.gitignore',          # Git
    '__pycache__', '.pytest_cache',           # Python cache
    'node_modules', '.node_modules',          # Node
    'export', 'exported', 'exports',          # Exports folder (our outputs)
    '.DS_Store', 'Thumbs.db',                 # OS metadata
    '.music', '.cache',                        # Other caches
}


def should_skip_directory(dir_name: str) -> bool:
    """Check if a directory should be skipped during traversal."""
    return dir_name.lower() in SKIP_DIRS or dir_name.startswith('.')


def get_audio_metadata(filepath: str) -> Optional[Dict]:
    """
    Extract metadata from an audio file.

    Args:
        filepath: Path to audio file

    Returns:
        Dict with keys: duration_sec, sample_rate, channels
        None if file cannot be read
    """
    try:
        # Try soundfile first (fast, doesn't load entire file)
        if sf is not None:
            try:
                info = sf.info(filepath)
                return {
                    'duration_sec': round(info.duration, 2),
                    'sample_rate': info.samplerate,
                    'channels': info.channels,
                }
            except Exception as e:
                logger.debug(f"soundfile failed for {filepath}: {e}")

        # Fallback to librosa
        if librosa is not None:
            try:
                y, sr = librosa.load(filepath, sr=None, mono=False)
                duration = len(y) / sr if len(y.shape) == 1 else y.shape[1] / sr
                channels = 1 if len(y.shape) == 1 else y.shape[0]
                return {
                    'duration_sec': round(duration, 2),
                    'sample_rate': sr,
                    'channels': channels,
                }
            except Exception as e:
                logger.debug(f"librosa failed for {filepath}: {e}")

        logger.warning(f"Cannot read metadata from {filepath} (soundfile and librosa unavailable or failed)")
        return None

    except Exception as e:
        logger.warning(f"Error reading {filepath}: {e}")
        return None


def discover_audio_files(root_dir: str) -> List[Dict]:
    """
    Recursively discover audio files and gather metadata.

    Args:
        root_dir: Root directory to scan

    Returns:
        List of dicts with keys: id, rel_path, duration_sec, sample_rate, channels, file_size_mb
    """
    if not os.path.isdir(root_dir):
        logger.error(f"Root directory not found: {root_dir}")
        return []

    results = []
    file_count = 0
    skipped_count = 0
    error_count = 0

    logger.info(f"Scanning {root_dir} for audio files...")

    for root, dirs, filenames in os.walk(root_dir):
        # Filter out directories to skip (modifies dirs in-place to prevent traversal)
        dirs[:] = [d for d in dirs if not should_skip_directory(d)]

        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()

            if ext not in SUPPORTED_FORMATS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, root_dir)
            file_count += 1

            # Get metadata
            metadata = get_audio_metadata(filepath)

            if metadata is None:
                logger.warning(f"  [SKIP] {rel_path} (unreadable)")
                error_count += 1
                continue

            # Get file size
            try:
                file_size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
            except Exception:
                file_size_mb = 0

            # Build record
            record = {
                'id': f"audio_{len(results):04d}",
                'rel_path': rel_path,
                'duration_sec': metadata['duration_sec'],
                'sample_rate': metadata['sample_rate'],
                'channels': metadata['channels'],
                'file_size_mb': file_size_mb,
            }
            results.append(record)
            logger.info(f"  [OK] {rel_path} ({metadata['duration_sec']}s, {metadata['sample_rate']}Hz, {metadata['channels']}ch)")

    logger.info(f"\nDiscovery complete:")
    logger.info(f"  Total files found: {file_count}")
    logger.info(f"  Readable files: {len(results)}")
    logger.info(f"  Skipped/errors: {error_count}")

    return results


def save_catalog_csv(catalog: List[Dict], output_path: str) -> None:
    """Save catalog to CSV file."""
    if not catalog:
        logger.warning("Catalog is empty; skipping CSV write")
        return

    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['id', 'rel_path', 'duration_sec', 'sample_rate', 'channels', 'file_size_mb']
            )
            writer.writeheader()
            writer.writerows(catalog)

        logger.info(f"Wrote catalog to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")
        sys.exit(1)


def save_catalog_json(catalog: List[Dict], output_path: str) -> None:
    """Save catalog to JSON file."""
    if not catalog:
        logger.warning("Catalog is empty; skipping JSON write")
        return

    try:
        with open(output_path, 'w') as f:
            json.dump(catalog, f, indent=2)

        logger.info(f"Wrote catalog to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON: {e}")
        sys.exit(1)


def save_catalog_markdown(catalog: List[Dict], output_path: str) -> None:
    """Save catalog to Markdown table."""
    if not catalog:
        logger.warning("Catalog is empty; skipping Markdown write")
        return

    try:
        with open(output_path, 'w') as f:
            f.write("# Audio Catalog\n\n")
            f.write("| ID | Path | Duration (s) | Sample Rate (Hz) | Channels | Size (MB) |\n")
            f.write("|---|---|---|---|---|---|\n")

            for record in catalog:
                f.write(
                    f"| {record['id']} | `{record['rel_path']}` | {record['duration_sec']} | "
                    f"{record['sample_rate']} | {record['channels']} | {record['file_size_mb']} |\n"
                )

            f.write(f"\n**Total:** {len(catalog)} files\n")

        logger.info(f"Wrote catalog to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write Markdown: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Discover audio files and build a catalog',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python discover_audio.py --root . --output audio_catalog.csv
  python discover_audio.py --root . --output audio_catalog.json --format json
  python discover_audio.py --root . --output audio_catalog.md --format markdown
        """
    )

    parser.add_argument('--root', type=str, default='.',
                        help='Root directory to scan (default: current directory)')
    parser.add_argument('--output', type=str, default='audio_catalog.csv',
                        help='Output file path (default: audio_catalog.csv)')
    parser.add_argument('--format', type=str, choices=['csv', 'json', 'markdown'],
                        help='Output format (auto-detected from file extension if not specified)')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Auto-detect format from extension if not specified
    if args.format is None:
        ext = Path(args.output).suffix.lower()
        if ext == '.json':
            args.format = 'json'
        elif ext == '.md':
            args.format = 'markdown'
        else:
            args.format = 'csv'

    # Discover files
    catalog = discover_audio_files(args.root)

    if not catalog:
        logger.warning("No audio files discovered")
        sys.exit(0)

    # Save in requested format
    if args.format == 'json':
        save_catalog_json(catalog, args.output)
    elif args.format == 'markdown':
        save_catalog_markdown(catalog, args.output)
    else:
        save_catalog_csv(catalog, args.output)


if __name__ == '__main__':
    main()
