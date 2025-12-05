# Batch Audio Archaeology Workflow

## Overview

This document describes the **batch texture generation workflow**, which allows you to discover, select, and process multiple audio files from your repository in a repeatable, scripted manner.

The workflow consists of three main phases:

1. **Discovery** (`discover_audio.py`) – Find all audio files in the repo
2. **Selection** (`select_sources.py`) – Filter and score candidates based on rules
3. **Batch Processing** (`batch_generate_textures.py`) – Generate textures for each selected track

Each phase is independent and can be run separately or as a complete pipeline.

---

## Quick Start

```bash
# Phase 1: Discover all audio files
python discover_audio.py --root . --output audio_catalog.csv

# Phase 2: Filter for suitable sources
python select_sources.py --catalog audio_catalog.csv --output selected_sources.csv

# Phase 3: Generate textures for all selected tracks
python batch_generate_textures.py --sources selected_sources.csv
```

When complete, textures will be in:
```
export/by_source/
  ├── 01_vainqueur_solanus_extracted_2/
  │   ├── pads/
  │   ├── swells/
  │   ├── clouds/
  │   └── hiss/
  ├── mr_cloudy_track_01/
  │   ├── pads/
  │   ├── swells/
  │   ├── clouds/
  │   └── hiss/
  └── ...
```

---

## Phase 1: Audio Discovery

### Purpose

Scan your entire repository for audio files and build a catalog with metadata (duration, sample rate, channels).

### Command

```bash
python discover_audio.py --root . --output audio_catalog.csv
```

### Arguments

| Argument | Description | Default |
|----------|---|---|
| `--root` | Directory to scan | `.` (current) |
| `--output` | Output file path | `audio_catalog.csv` |
| `--format` | Output format: `csv`, `json`, or `markdown` | Auto-detected from extension |
| `--verbose` | Enable verbose logging | Disabled |

### Output Format

**CSV** (`audio_catalog.csv`):
```
id,rel_path,duration_sec,sample_rate,channels,file_size_mb
audio_0000,VA - Dreamy Harbor [2017] [TRESOR291]/01 Vainqueur - Solanus (Extracted 2).flac,735.12,44100,2,150.5
audio_0001,Mr. Cloudy - Cloudy Tracks Flac/01 - Dreaming.flac,480.25,44100,2,98.3
...
```

**JSON** (`audio_catalog.json`):
```json
[
  {
    "id": "audio_0000",
    "rel_path": "VA - Dreamy Harbor [2017] [TRESOR291]/01 Vainqueur - Solanus (Extracted 2).flac",
    "duration_sec": 735.12,
    "sample_rate": 44100,
    "channels": 2,
    "file_size_mb": 150.5
  },
  ...
]
```

### What Gets Discovered

**Supported formats:**
- `.wav` – WAV files
- `.aiff` / `.aif` – AIFF files
- `.flac` – FLAC files
- `.mp3` – MP3 files (if librosa is installed)

**Directories skipped:**
- `venv/`, `.venv/`, `env/` – Virtual environments
- `.git/`, `.github/` – Git directories
- `__pycache__/`, `.pytest_cache/` – Python caches
- `node_modules/` – Node packages
- `export/`, `exported/`, `exports/` – Export directories
- `Thumbs.db`, `.DS_Store`, `.cache/` – OS metadata
- Any directory starting with `.`

**Order:**
Files are discovered in alphabetical order within each directory.

### Performance

For a typical repo with 50–200 audio files:
- Scanning: ~2–10 seconds (depends on I/O speed)
- Metadata extraction: ~1–5 minutes (depends on file count and sizes)

**Tip**: Run with `--verbose` to see progress.

---

## Phase 2: Source Selection

### Purpose

Read the catalog and apply filtering/scoring rules to identify which tracks are suitable for texture generation.

### Command

```bash
python select_sources.py --catalog audio_catalog.csv --output selected_sources.csv
```

### Arguments

| Argument | Description | Default |
|----------|---|---|
| `--catalog` | Path to catalog (from Phase 1) | *required* |
| `--output` | Output file path | `selected_sources.csv` |
| `--min-duration` | Minimum duration in seconds | 30 (configurable) |
| `--max-duration` | Maximum duration in seconds | 3600 (configurable) |
| `--format` | Output format: `csv` or `json` | Auto-detected |

### Configuration (Built-In)

Edit the top of `select_sources.py` to customize selection rules:

```python
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
PREFERRED_CHANNELS = None

# Sample rate preference (Hz). Set to None for no preference.
PREFERRED_SAMPLE_RATE = None
```

### Scoring System

Each track receives a score based on:
- **Preferred path patterns**: +10 points per match (e.g., "masters" → +10)
- **Preferred channels**: +5 points if channels match preference
- **Preferred sample rate**: +5 points if sample rate matches preference

Tracks are sorted by score (highest first), then by path.

### Example Customizations

**Conservative (high-quality sources only):**
```python
MIN_DURATION_SEC = 60  # Min 1 minute
MAX_DURATION_SEC = 600  # Max 10 minutes
PREFERRED_PATH_PATTERNS = ['masters', 'bounces']
SKIP_PATH_PATTERNS = ['scratch', 'draft', 'test', '_old']
```

**Experimental (discover everything):**
```python
MIN_DURATION_SEC = 10  # Min 10 seconds
MAX_DURATION_SEC = 7200  # Max 2 hours
PREFERRED_PATH_PATTERNS = []
SKIP_PATH_PATTERNS = []
```

### Output Format

Same as input catalog, plus a `selection_score` field:

```csv
id,rel_path,duration_sec,sample_rate,channels,file_size_mb,selection_score
audio_0001,masters/track_01.flac,245.3,44100,2,50.2,20
audio_0003,bounces/track_03.flac,180.5,44100,2,36.1,10
audio_0005,songs/demo.flac,120.2,44100,1,24.5,5
```

### Selection Summary

At the end of Phase 2, you'll see:

```
======================================================================
SELECTION SUMMARY
======================================================================
Input catalog:  50 files
Selected:       12 files
Rejected:       38 files

Total duration: 2.5 hours
Avg duration:   750.0 seconds

Top 5 selected (by score):
  1. [20] masters/track_01.flac (245s, 44100Hz)
  2. [20] masters/track_02.flac (198s, 44100Hz)
  3. [10] bounces/track_03.flac (180s, 44100Hz)
  4. [10] bounces/track_04.flac (156s, 44100Hz)
  5. [ 5] songs/demo.flac (120s, 44100Hz)
======================================================================
```

---

## Phase 3: Batch Texture Generation

### Purpose

For each selected track, run the complete texture generation pipeline in isolation:
1. Create a working directory
2. Copy the source track
3. Run `make_textures.py`
4. Collect outputs to organized location
5. Log results

### Command

```bash
python batch_generate_textures.py --sources selected_sources.csv
```

### Arguments

| Argument | Description | Default |
|----------|---|---|
| `--sources` | Path to selected sources (from Phase 2) | *required* |
| `--profile` | Configuration profile (e.g., "bright") | None (uses default) |
| `--root` | Repository root directory | `.` (current) |
| `--dry-run` | Show what would be done without processing | Disabled |
| `--start-index` | Start processing from this index (0-based) | 0 |
| `--count` | Process only this many tracks | All |
| `--output` | Results JSON file | `batch_results.json` |

### Workflow Per Track

For each selected track, the batch processor:

1. **Create working directory**: `work/<track_slug>/`
   - `work/<track_slug>/source_audio/` – Input for pad mining
   - `work/<track_slug>/pad_sources/` – Input for swell/drone generation
   - `work/<track_slug>/drums/` – Input for hiss generation (if available)

2. **Copy source files**: The main track is copied to both `source_audio/` and `pad_sources/`

3. **Run texture generation**: Calls `make_textures.py --all` with the track-specific working directory

4. **Collect outputs**: Copies results to `export/tr8s/by_source/<track_slug>/`

5. **Cleanup**: Removes working directory (optional, configurable)

### Example Invocations

**Process all selected tracks:**
```bash
python batch_generate_textures.py --sources selected_sources.csv
```

**Dry-run (see what would happen):**
```bash
python batch_generate_textures.py --sources selected_sources.csv --dry-run
```

**Process only first 5 tracks:**
```bash
python batch_generate_textures.py --sources selected_sources.csv --count 5
```

**Resume from track 10 (useful if interrupted):**
```bash
python batch_generate_textures.py --sources selected_sources.csv --start-index 10
```

**Use a custom configuration profile:**
```bash
python batch_generate_textures.py --sources selected_sources.csv --profile bright
```
*(Requires `config_bright.yaml` in repo root)*

### Configuration Profiles

You can create multiple configuration profiles for different texture styles:

**`config.yaml`** – Default (balanced)
**`config_bright.yaml`** – High-frequency, airy textures
**`config_dark.yaml`** – Low-frequency, dark textures
**`config_noisy.yaml`** – Aggressive, wide pitch ranges

Example `config_bright.yaml`:
```yaml
global:
  sample_rate: 44100
  output_bit_depth: 24
  target_peak_dbfs: -1.0

pad_miner:
  target_durations_sec: [1.5, 2.5]      # Shorter pads
  loop_crossfade_ms: 50                 # Quick loop

drones:
  airy_highpass_hz: 8000                # Very bright

clouds:
  pitch_shift_range:
    min: -2
    max: 8                              # More upward shift

hiss:
  bandpass_low_hz: 7000                 # Higher frequency range
  bandpass_high_hz: 16000
```

### Output Structure

After batch processing completes:

```
export/tr8s/by_source/
├── 01_vainqueur_solanus_extracted_2/
│   ├── pads/
│   │   ├── solanus_pad01.wav
│   │   ├── solanus_pad02.wav
│   │   └── ...
│   ├── swells/
│   │   ├── solanus_swell01_warm.wav
│   │   └── ...
│   ├── clouds/
│   │   ├── solanus_cloud01.wav
│   │   └── ...
│   └── hiss/
│       ├── solanus_hiss01.wav
│       └── ...
├── mr_cloudy_track_01/
│   ├── pads/
│   ├── swells/
│   ├── clouds/
│   └── hiss/
└── ...
```

Each track gets its own subdirectory, organized into texture types.

### Results Log

After batch processing, `batch_results.json` contains:

```json
{
  "timestamp": "2024-12-05T14:30:22.123456",
  "total": 12,
  "successful": 11,
  "failed": 1,
  "results": [
    {
      "id": "audio_0001",
      "rel_path": "masters/track_01.flac",
      "track_slug": "masters_track_01",
      "success": true,
      "duration_sec": 245.3,
      "stats": {
        "pads": 3,
        "swells": 6,
        "clouds": 6,
        "hiss_loops": 8,
        "hiss_flickers": 4,
        "error": null
      }
    },
    ...
  ]
}
```

### Batch Processing Summary

At the end of Phase 3, you'll see:

```
======================================================================
BATCH PROCESSING SUMMARY
======================================================================
Total tracks:      12
Successful:        11
Failed:            1

Total textures generated:
  Pads:     36
  Swells:   66
  Clouds:   66
  Hiss:     96

Failed tracks:
  - scratch/old_demo.flac: No audio files in source_audio/
======================================================================
```

---

## Complete Workflow Example

Here's a complete example from start to finish:

```bash
# Step 1: Discover all audio
python discover_audio.py --root . --output audio_catalog.csv

# Check what was found
wc -l audio_catalog.csv  # Should show count of files

# Step 2: Select suitable sources (edit select_sources.py first to customize rules)
python select_sources.py --catalog audio_catalog.csv --output selected_sources.csv

# Review selection
cat selected_sources.csv | head -20

# Step 3a: Dry-run to see what would happen
python batch_generate_textures.py --sources selected_sources.csv --dry-run

# Step 3b: Process first 3 tracks to test
python batch_generate_textures.py --sources selected_sources.csv --count 3

# Review results
ls -la export/tr8s/by_source/
cat batch_results.json | jq '.successful'

# Step 3c: If happy, process remaining tracks
python batch_generate_textures.py --sources selected_sources.csv --start-index 3

# Final check
find export/tr8s/by_source/ -name "*.wav" | wc -l
```

---

## Workflow Tips & Troubleshooting

### Tip 1: Run Discovery Periodically

If you add new audio to your repo, re-run Phase 1 to update the catalog:

```bash
python discover_audio.py --root . --output audio_catalog.csv
```

### Tip 2: Adjust Selection Rules Iteratively

Don't try to get selection rules perfect on the first try. Run Phase 2 multiple times with different rules:

```bash
# Conservative selection (long tracks only)
python select_sources.py --catalog audio.csv --min-duration 120 --output selected_conservative.csv

# Aggressive selection (all tracks)
python select_sources.py --catalog audio.csv --min-duration 10 --output selected_aggressive.csv
```

### Tip 3: Test with a Subset

Always test batch processing on a small subset first:

```bash
# Dry-run to see what would happen
python batch_generate_textures.py --sources selected.csv --dry-run

# Process just the first track
python batch_generate_textures.py --sources selected.csv --count 1

# Check results
ls export/tr8s/by_source/
```

### Tip 4: Use Profiles for Different Texture Styles

Create multiple configuration files and run batch processing multiple times:

```bash
# Generate textures with "bright" profile
python batch_generate_textures.py --sources selected.csv --profile bright

# Results go to export/tr8s/by_source/<slug>/ (same location)
# Overwrite previous results, OR...

# Alternatively, modify batch_generate_textures.py to save to different locations
# based on profile (left as exercise)
```

### Tip 5: Resume Interrupted Batches

If batch processing is interrupted, you can resume from a specific track:

```bash
# Find out which track failed
grep '"success": false' batch_results.json

# Get its index
grep -n '"rel_path": "path/to/failed/track.flac"' selected_sources.csv

# Resume from next index
python batch_generate_textures.py --sources selected.csv --start-index 42
```

### Troubleshooting: "No audio files found"

If you see this error:

```
No audio files discovered
```

Check:
1. Are there actually audio files in the directory?
2. Are they in a `SKIP_DIRS` folder (e.g., `export/`)?
3. Are they in an unsupported format (e.g., `.m4a`, `.ogg`)?
4. Are they corrupt and unreadable by librosa?

Run with `--verbose` to see details:

```bash
python discover_audio.py --root . --output audio.csv --verbose
```

### Troubleshooting: "Selection returned 0 results"

Check:
1. Are your `MIN_DURATION_SEC` / `MAX_DURATION_SEC` too strict?
2. Are your `SKIP_PATH_PATTERNS` too aggressive?
3. Try with no filters:

```python
# In select_sources.py, temporarily set:
MIN_DURATION_SEC = 1
MAX_DURATION_SEC = 99999
SKIP_PATH_PATTERNS = []
```

### Troubleshooting: "Process timed out"

Texture generation has a 5-minute timeout per track. If this happens:
1. Check the working directory: `work/<track_slug>/export/tr8s/`
2. Increase the timeout in `batch_generate_textures.py` (line ~280):

```python
timeout=300  # Increase to 600 (10 minutes) if needed
```

### Troubleshooting: "Permission denied" on macOS

If you see permission errors, try:

```bash
chmod +x discover_audio.py select_sources.py batch_generate_textures.py
python discover_audio.py ...  # Instead of just running the script
```

---

## Integration with Version Control

You may want to add these to `.gitignore`:

```
# Batch workflow artifacts
audio_catalog.csv
audio_catalog.json
selected_sources.csv
batch_results.json

# Working directories
work/

# Generated textures (or commit selectively)
export/tr8s/by_source/
```

Or, to keep generated textures in git:

```bash
# Add only final outputs
git add export/tr8s/by_source/
git commit -m "Add generated texture packs for Solanus, Cloudy Tracks, etc."

# Exclude working directories
echo "work/" >> .gitignore
```

---

## Performance Expectations

For a typical texture generation pipeline on a 5-minute 44.1kHz audio file:

| Phase | Time |
|-------|------|
| Pad mining (3 durations) | 5–10 seconds |
| Swell generation (6 variants) | 5 seconds |
| Cloud generation (6 clouds) | 10 seconds |
| Hiss generation (8 loops + 4 flickers) | 3 seconds |
| **Per-track total** | ~20–30 seconds |

For 10 tracks: ~3–5 minutes
For 50 tracks: ~15–25 minutes
For 100 tracks: ~30–50 minutes

**Optimization**: If you have multiple cores available, you could modify `batch_generate_textures.py` to use multiprocessing (see CODE_REVIEW.md for details).

---

## Next Steps

1. **Customize `select_sources.py`** to match your repo structure
2. **Create configuration profiles** (e.g., `config_bright.yaml`, `config_dark.yaml`)
3. **Run Phase 1 & 2** to identify sources
4. **Dry-run Phase 3** on a small sample
5. **Process full batch** and review outputs in `export/tr8s/by_source/`
6. **Organize textures** into sample packs for distribution or DAW use

---

## See Also

- **CODE_REVIEW.md** – Detailed code analysis and improvement suggestions
- **CONFIG_QUICK_REFERENCE.md** – Configuration options reference
- **IMPLEMENTATION_SUMMARY.md** – Technical details of v0.2 upgrade
- **README.md** – Main project documentation

