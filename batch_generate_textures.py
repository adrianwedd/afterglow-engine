#!/usr/bin/env python3
"""
batch_generate_textures.py: Process multiple tracks through the texture pipeline.

This script reads a list of selected audio sources and runs the texture generation
pipeline on each track in a controlled, reproducible way. For each track:

1. Creates a working directory: work/<track_slug>/
2. Sets up source_audio/, pad_sources/, drums/ subdirectories
3. Copies/symlinks the source track(s)
4. Runs make_textures.py for that track
5. Collects outputs to: export/tr8s/by_source/<track_slug>/
6. Logs results in a summary file

Usage:
    python batch_generate_textures.py --sources selected_sources.csv
    python batch_generate_textures.py --sources selected.csv --profile bright
    python batch_generate_textures.py --sources selected.csv --dry-run
    python batch_generate_textures.py --sources selected.csv --start-index 5 --count 10
"""

import argparse
import os
import sys
import csv
import json
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """
    Convert filename to a safe directory name (slug).

    Examples:
        "01 Vainqueur - Solanus (Extracted 2).flac" -> "01_vainqueur_solanus_extracted_2"
        "track [2023].wav" -> "track_2023"
    """
    # Remove extension
    text = Path(text).stem
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with underscores
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    return text


def load_sources(sources_path: str) -> List[Dict]:
    """Load selected sources from CSV or JSON."""
    if not os.path.exists(sources_path):
        logger.error(f"Sources file not found: {sources_path}")
        sys.exit(1)

    try:
        ext = Path(sources_path).suffix.lower()

        if ext == '.json':
            with open(sources_path, 'r') as f:
                return json.load(f)
        else:  # CSV
            with open(sources_path, 'r') as f:
                reader = csv.DictReader(f)
                records = []
                for row in reader:
                    # Convert numeric fields if they exist
                    for key in ['duration_sec', 'sample_rate', 'channels', 'file_size_mb', 'selection_score']:
                        if key in row:
                            try:
                                row[key] = float(row[key]) if '.' in row[key] else int(row[key])
                            except (ValueError, KeyError):
                                pass
                    records.append(row)
                return records

    except Exception as e:
        logger.error(f"Failed to load sources: {e}")
        sys.exit(1)


class TrackProcessor:
    """Orchestrate texture generation for a single track."""

    def __init__(self, repo_root: str = '.', dry_run: bool = False, profile: Optional[str] = None):
        self.repo_root = os.path.abspath(repo_root)
        self.dry_run = dry_run
        self.profile = profile
        self.work_dir = os.path.join(self.repo_root, 'work')
        self.export_dir = os.path.join(self.repo_root, 'export', 'tr8s', 'by_source')

    def setup_track_directories(self, track_slug: str) -> Dict[str, str]:
        """
        Create working directories for a track.

        Returns:
            Dict with keys: work_root, source_audio, pad_sources, drums
        """
        work_root = os.path.join(self.work_dir, track_slug)
        source_audio = os.path.join(work_root, 'source_audio')
        pad_sources = os.path.join(work_root, 'pad_sources')
        drums = os.path.join(work_root, 'drums')

        if not self.dry_run:
            for directory in [source_audio, pad_sources, drums]:
                os.makedirs(directory, exist_ok=True)

        return {
            'work_root': work_root,
            'source_audio': source_audio,
            'pad_sources': pad_sources,
            'drums': drums,
        }

    def prepare_source_files(self, source_record: Dict, dirs: Dict) -> bool:
        """
        Copy/symlink source files into working directories.

        For now, copies the main track to both source_audio/ and pad_sources/.
        Can be extended to handle stems, drum loops, etc.

        Returns:
            True if successful, False otherwise
        """
        source_path = os.path.join(self.repo_root, source_record['rel_path'])

        if not os.path.exists(source_path):
            logger.warning(f"Source file not found: {source_path}")
            return False

        try:
            # Determine filename
            filename = os.path.basename(source_path)

            # Copy to source_audio/ and pad_sources/
            dest_source = os.path.join(dirs['source_audio'], filename)
            dest_pad = os.path.join(dirs['pad_sources'], filename)

            if not self.dry_run:
                shutil.copy2(source_path, dest_source)
                shutil.copy2(source_path, dest_pad)
                logger.info(f"  Copied {filename} to working directories")

            return True

        except Exception as e:
            logger.error(f"Failed to copy source files: {e}")
            return False

    def run_texture_generation(self, track_slug: str, dirs: Dict) -> Tuple[bool, Dict]:
        """
        Run make_textures.py for this track.

        Returns:
            (success, stats_dict) tuple
        """
        # Build command
        make_textures_script = os.path.join(self.repo_root, 'make_textures.py')
        config_path = self._get_config_path()

        cmd = [
            sys.executable,
            make_textures_script,
            '--all',
            '--root', dirs['work_root'],
        ]

        if config_path:
            cmd.extend(['--config', config_path])

        stats = {
            'pads': 0,
            'swells': 0,
            'clouds': 0,
            'hiss_loops': 0,
            'hiss_flickers': 0,
            'error': None,
        }

        if self.dry_run:
            logger.info(f"  [DRY RUN] Would run: {' '.join(cmd)}")
            return True, stats

        try:
            logger.info(f"  Running texture generation...")
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=300  # 5-minute timeout per track
            )

            if result.returncode != 0:
                stats['error'] = f"Process exited with code {result.returncode}"
                logger.error(f"  Texture generation failed: {stats['error']}")
                logger.debug(f"  stderr: {result.stderr}")
                return False, stats

            # Count generated files
            export_track_dir = os.path.join(dirs['work_root'], 'export', 'tr8s')
            if os.path.exists(export_track_dir):
                for subdir in ['pads', 'swells', 'clouds', 'hiss']:
                    subdir_path = os.path.join(export_track_dir, subdir)
                    if os.path.exists(subdir_path):
                        count = len([f for f in os.listdir(subdir_path) if f.endswith('.wav')])
                        if subdir == 'hiss':
                            # Split hiss into loops and flickers (simple heuristic)
                            stats['hiss_loops'] = max(1, count // 2)
                            stats['hiss_flickers'] = count - stats['hiss_loops']
                        else:
                            stats[subdir] = count

            logger.info(f"  ✓ Generated: {stats['pads']} pads, {stats['swells']} swells, "
                       f"{stats['clouds']} clouds, {stats['hiss_loops']} hiss loops")

            return True, stats

        except subprocess.TimeoutExpired:
            stats['error'] = "Process timed out (5 minutes)"
            logger.error(f"  {stats['error']}")
            return False, stats
        except Exception as e:
            stats['error'] = str(e)
            logger.error(f"  Failed to run texture generation: {e}")
            return False, stats

    def collect_outputs(self, track_slug: str, dirs: Dict) -> bool:
        """
        Copy generated textures to final export location.

        Copies from work/<slug>/export/tr8s/ to export/tr8s/by_source/<slug>/
        """
        source_dir = os.path.join(dirs['work_root'], 'export', 'tr8s')
        dest_dir = os.path.join(self.export_dir, track_slug)

        if not os.path.exists(source_dir):
            logger.warning(f"  No outputs to collect (export dir not found)")
            return False

        try:
            if not self.dry_run:
                # Remove old outputs if they exist
                if os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir)

                # Copy everything
                shutil.copytree(source_dir, dest_dir)

            logger.info(f"  Collected outputs to {dest_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect outputs: {e}")
            return False

    def cleanup_working_dir(self, dirs: Dict, keep_work: bool = False) -> None:
        """Optionally clean up working directory after successful processing."""
        if not keep_work and not self.dry_run:
            try:
                shutil.rmtree(dirs['work_root'])
                logger.info(f"  Cleaned up working directory")
            except Exception as e:
                logger.warning(f"Failed to clean up working directory: {e}")

    def _get_config_path(self) -> Optional[str]:
        """Get path to config file (profile-based or default)."""
        if self.profile:
            profile_config = os.path.join(self.repo_root, f'config_{self.profile}.yaml')
            if os.path.exists(profile_config):
                return profile_config
            logger.warning(f"Profile config not found: {profile_config}, using default")

        return None

    def process_track(self, source_record: Dict) -> Tuple[bool, Dict]:
        """
        Process a single track through the entire pipeline.

        Returns:
            (success, result_dict) tuple
        """
        track_slug = slugify(source_record['rel_path'])
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {source_record['rel_path']}")
        logger.info(f"  ID:       {source_record.get('id', 'N/A')}")
        logger.info(f"  Duration: {source_record.get('duration_sec', 'N/A')}s")
        logger.info(f"  Sample rate: {source_record.get('sample_rate', 'N/A')}Hz")
        logger.info(f"  Slug:     {track_slug}")

        result = {
            'id': source_record.get('id'),
            'rel_path': source_record['rel_path'],
            'track_slug': track_slug,
            'success': False,
            'duration_sec': source_record.get('duration_sec'),
            'stats': {},
            'error': None,
        }

        try:
            # Setup directories
            dirs = self.setup_track_directories(track_slug)

            # Prepare source files
            if not self.prepare_source_files(source_record, dirs):
                result['error'] = 'Failed to prepare source files'
                return False, result

            # Run texture generation
            success, stats = self.run_texture_generation(track_slug, dirs)
            result['stats'] = stats
            if not success:
                result['error'] = stats.get('error', 'Unknown error')
                return False, result

            # Collect outputs
            if not self.collect_outputs(track_slug, dirs):
                result['error'] = 'Failed to collect outputs'
                return False, result

            # Cleanup
            self.cleanup_working_dir(dirs, keep_work=False)

            result['success'] = True
            logger.info(f"✓ Track processed successfully")

            return True, result

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ Unexpected error: {e}")
            return False, result


def print_batch_summary(results: List[Dict]) -> None:
    """Print summary of batch processing."""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    total_pads = sum(r.get('stats', {}).get('pads', 0) for r in successful)
    total_swells = sum(r.get('stats', {}).get('swells', 0) for r in successful)
    total_clouds = sum(r.get('stats', {}).get('clouds', 0) for r in successful)
    total_hiss = sum(r.get('stats', {}).get('hiss_loops', 0) for r in successful)

    logger.info("\n" + "="*70)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("="*70)
    logger.info(f"Total tracks:      {len(results)}")
    logger.info(f"Successful:        {len(successful)}")
    logger.info(f"Failed:            {len(failed)}")
    logger.info(f"")
    logger.info(f"Total textures generated:")
    logger.info(f"  Pads:     {total_pads}")
    logger.info(f"  Swells:   {total_swells}")
    logger.info(f"  Clouds:   {total_clouds}")
    logger.info(f"  Hiss:     {total_hiss}")
    logger.info(f"")

    if failed:
        logger.info(f"Failed tracks:")
        for r in failed:
            logger.info(f"  - {r['rel_path']}: {r.get('error', 'Unknown error')}")

    logger.info("="*70 + "\n")


def save_batch_results(results: List[Dict], output_path: str) -> None:
    """Save batch results to JSON file."""
    try:
        with open(output_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': len(results),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'results': results,
            }, f, indent=2)

        logger.info(f"Saved batch results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch process multiple audio tracks for texture generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_generate_textures.py --sources selected_sources.csv
  python batch_generate_textures.py --sources selected.csv --profile bright
  python batch_generate_textures.py --sources selected.csv --dry-run
  python batch_generate_textures.py --sources selected.csv --start-index 5 --count 3

Outputs:
  - work/<track_slug>/               : Working directory for each track
  - export/tr8s/by_source/<slug>/    : Final texture outputs
  - batch_results.json               : Processing log and statistics
        """
    )

    parser.add_argument('--sources', type=str, required=True,
                        help='Path to selected sources file (from select_sources.py)')
    parser.add_argument('--profile', type=str,
                        help='Configuration profile (e.g., "bright" uses config_bright.yaml)')
    parser.add_argument('--root', type=str, default='.',
                        help='Repository root directory (default: current directory)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without processing')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Start processing from this index (0-based, default: 0)')
    parser.add_argument('--count', type=int,
                        help='Process only this many tracks (default: process all)')
    parser.add_argument('--output', type=str, default='batch_results.json',
                        help='Output file for batch results (default: batch_results.json)')

    args = parser.parse_args()

    # Load sources
    logger.info(f"Loading sources from {args.sources}...")
    sources = load_sources(args.sources)
    logger.info(f"Loaded {len(sources)} sources")

    # Filter by start/count
    if args.start_index > 0 or args.count:
        end_index = args.start_index + (args.count or len(sources))
        sources = sources[args.start_index:end_index]
        logger.info(f"Processing {len(sources)} sources (index {args.start_index}–{end_index-1})")

    if not sources:
        logger.error("No sources to process")
        sys.exit(1)

    # Confirm with user if not dry-run
    if not args.dry_run:
        response = input(f"\nProcessing {len(sources)} tracks. Continue? (y/N) ")
        if response.lower() != 'y':
            logger.info("Cancelled")
            sys.exit(0)

    # Create processor
    processor = TrackProcessor(
        repo_root=args.root,
        dry_run=args.dry_run,
        profile=args.profile
    )

    # Process each track
    results = []
    for i, source in enumerate(sources, 1):
        logger.info(f"\n[{i}/{len(sources)}]")
        success, result = processor.process_track(source)
        results.append(result)

    # Print and save summary
    print_batch_summary(results)
    save_batch_results(results, args.output)


if __name__ == '__main__':
    main()
