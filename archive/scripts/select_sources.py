#!/usr/bin/env python3
"""
select_sources.py: Filter discovered audio files based on configurable rules.

This script reads a catalog (from discover_audio.py) and applies filtering rules
to identify which tracks are suitable for texture generation. Rules can be based on:
- Duration (min/max)
- Path patterns (prefer certain folders)
- Sample rate
- Number of channels

Output is a CSV/JSON file of selected sources ready for batch texture generation.

Usage:
    python select_sources.py --catalog audio_catalog.csv --output selected_sources.csv
    python select_sources.py --catalog audio_catalog.json --min-duration 30 --output selected.csv
"""

import argparse
import os
import sys
import csv
import json
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION: Adjust these to match your repo structure and preferences
# ============================================================================

# Minimum duration in seconds (ignore very short clips)
MIN_DURATION_SEC = 30

# Maximum duration in seconds (ignore very long files)
MAX_DURATION_SEC = 3600

# Preferred path patterns (tracks in these folders are scored higher)
PREFERRED_PATH_PATTERNS = [
    'bounces',
    'masters',
    'tracks',
    'songs',
    'finished',
    'complete',
]

# Anti-patterns: skip tracks matching these patterns
SKIP_PATH_PATTERNS = [
    'scratch',
    'test',
    'demo',
    'draft',
    '_old',
    'rejected',
    'unused',
]

# Prefer mono or stereo (can be 'mono', 'stereo', or None for no preference)
PREFERRED_CHANNELS = None  # Accept both mono and stereo

# Sample rate preference (Hz). Set to None for no preference.
# Common values: 44100, 48000, 96000
PREFERRED_SAMPLE_RATE = None

# ============================================================================

class SourceSelector:
    """Filter and score audio catalog entries."""

    def __init__(self, min_duration=MIN_DURATION_SEC, max_duration=MAX_DURATION_SEC):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def should_skip(self, record: Dict) -> Tuple[bool, str]:
        """
        Check if a record should be skipped.

        Returns:
            (should_skip, reason) tuple
        """
        rel_path = record['rel_path']
        duration = record['duration_sec']

        # Duration checks
        if duration < self.min_duration:
            return True, f"Too short ({duration}s < {self.min_duration}s)"
        if duration > self.max_duration:
            return True, f"Too long ({duration}s > {self.max_duration}s)"

        # Anti-pattern checks
        path_lower = rel_path.lower()
        for pattern in SKIP_PATH_PATTERNS:
            if pattern in path_lower:
                return True, f"Matches skip pattern: {pattern}"

        return False, ""

    def score_record(self, record: Dict) -> int:
        """
        Score a record (higher = better).

        Scoring criteria:
        - Preferred path patterns: +10 per match
        - Preferred channels: +5
        - Preferred sample rate: +5
        """
        score = 0
        rel_path = record['rel_path']
        path_lower = rel_path.lower()

        # Preferred path patterns
        for pattern in PREFERRED_PATH_PATTERNS:
            if pattern in path_lower:
                score += 10

        # Preferred channels
        if PREFERRED_CHANNELS == 'mono' and record['channels'] == 1:
            score += 5
        elif PREFERRED_CHANNELS == 'stereo' and record['channels'] == 2:
            score += 5

        # Preferred sample rate
        if PREFERRED_SAMPLE_RATE and record['sample_rate'] == PREFERRED_SAMPLE_RATE:
            score += 5

        return score

    def filter_and_score(self, catalog: List[Dict]) -> List[Dict]:
        """
        Filter catalog and add score field.

        Returns:
            Sorted list of records (highest score first)
        """
        selected = []

        for record in catalog:
            should_skip, reason = self.should_skip(record)

            if should_skip:
                logger.debug(f"SKIP {record['rel_path']}: {reason}")
                continue

            score = self.score_record(record)
            record['selection_score'] = score
            selected.append(record)

        # Sort by score (highest first), then by path
        selected.sort(key=lambda r: (-r['selection_score'], r['rel_path']))

        return selected


def load_catalog(catalog_path: str) -> List[Dict]:
    """Load catalog from CSV or JSON file."""
    if not os.path.exists(catalog_path):
        logger.error(f"Catalog file not found: {catalog_path}")
        sys.exit(1)

    try:
        ext = Path(catalog_path).suffix.lower()

        if ext == '.json':
            with open(catalog_path, 'r') as f:
                return json.load(f)
        else:  # CSV
            with open(catalog_path, 'r') as f:
                reader = csv.DictReader(f)
                # Convert numeric fields
                records = []
                for row in reader:
                    row['duration_sec'] = float(row['duration_sec'])
                    row['sample_rate'] = int(row['sample_rate'])
                    row['channels'] = int(row['channels'])
                    row['file_size_mb'] = float(row['file_size_mb'])
                    records.append(row)
                return records

    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        sys.exit(1)


def save_selected_csv(selected: List[Dict], output_path: str) -> None:
    """Save selected sources to CSV."""
    if not selected:
        logger.warning("No sources selected; skipping CSV write")
        return

    try:
        with open(output_path, 'w', newline='') as f:
            fieldnames = list(selected[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(selected)

        logger.info(f"Wrote {len(selected)} selected sources to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")
        sys.exit(1)


def save_selected_json(selected: List[Dict], output_path: str) -> None:
    """Save selected sources to JSON."""
    if not selected:
        logger.warning("No sources selected; skipping JSON write")
        return

    try:
        with open(output_path, 'w') as f:
            json.dump(selected, f, indent=2)

        logger.info(f"Wrote {len(selected)} selected sources to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON: {e}")
        sys.exit(1)


def print_summary(catalog: List[Dict], selected: List[Dict]) -> None:
    """Print a summary of selection results."""
    logger.info("\n" + "="*70)
    logger.info("SELECTION SUMMARY")
    logger.info("="*70)

    total_duration = sum(r['duration_sec'] for r in selected)
    avg_duration = total_duration / len(selected) if selected else 0

    logger.info(f"Input catalog:  {len(catalog)} files")
    logger.info(f"Selected:       {len(selected)} files")
    logger.info(f"Rejected:       {len(catalog) - len(selected)} files")
    logger.info(f"")
    logger.info(f"Total duration: {total_duration / 3600:.1f} hours")
    logger.info(f"Avg duration:   {avg_duration:.1f} seconds")
    logger.info(f"")

    if selected:
        logger.info("Top 5 selected (by score):")
        for i, record in enumerate(selected[:5], 1):
            logger.info(
                f"  {i}. [{record['selection_score']:2d}] {record['rel_path']} "
                f"({record['duration_sec']}s, {record['sample_rate']}Hz)"
            )

    logger.info("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Filter audio catalog and select sources for batch texture generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python select_sources.py --catalog audio_catalog.csv --output selected.csv
  python select_sources.py --catalog catalog.json --min-duration 60 --output selected.json
  python select_sources.py --catalog catalog.csv --max-duration 300 --output selected.csv

Configuration:
  Edit MIN_DURATION_SEC, PREFERRED_PATH_PATTERNS, etc. at the top of this script.
        """
    )

    parser.add_argument('--catalog', type=str, required=True,
                        help='Path to catalog file (from discover_audio.py)')
    parser.add_argument('--output', type=str, default='selected_sources.csv',
                        help='Output file path (default: selected_sources.csv)')
    parser.add_argument('--min-duration', type=float,
                        help=f'Override MIN_DURATION_SEC (default: {MIN_DURATION_SEC}s)')
    parser.add_argument('--max-duration', type=float,
                        help=f'Override MAX_DURATION_SEC (default: {MAX_DURATION_SEC}s)')
    parser.add_argument('--format', type=str, choices=['csv', 'json'],
                        help='Output format (auto-detected from extension if not specified)')

    args = parser.parse_args()

    # Load catalog
    logger.info(f"Loading catalog from {args.catalog}...")
    catalog = load_catalog(args.catalog)
    logger.info(f"Loaded {len(catalog)} entries")

    # Filter and score
    min_dur = args.min_duration if args.min_duration is not None else MIN_DURATION_SEC
    max_dur = args.max_duration if args.max_duration is not None else MAX_DURATION_SEC

    selector = SourceSelector(min_duration=min_dur, max_duration=max_dur)
    selected = selector.filter_and_score(catalog)

    # Print summary
    print_summary(catalog, selected)

    # Save results
    if not selected:
        logger.warning("No sources were selected!")
        sys.exit(0)

    # Auto-detect format from extension if not specified
    if args.format is None:
        ext = Path(args.output).suffix.lower()
        args.format = 'json' if ext == '.json' else 'csv'

    if args.format == 'json':
        save_selected_json(selected, args.output)
    else:
        save_selected_csv(selected, args.output)


if __name__ == '__main__':
    main()
