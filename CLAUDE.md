# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Context: afterglow-engine

*A machine for sonic archaeology.*

## The Philosophy

This tool is not a generator in the traditional sense. It does not compose. It does not invent. It is a **quiet machine** kept in the back of the studio.

Its purpose is to ingest existing audio archives—finished tracks, sketches, forgotten experiments—and **unweave** them. It separates pigment from gesture. It mines for:
*   **Surfaces**: Stable, textural moments (pads).
*   **Atmosphere**: Granular clouds of memory.
*   **Dust**: High-frequency hiss and transient flickers derived from percussion.

When writing code or documentation, remember: we are **distilling memories**, not just processing signals.

## Architecture Overview

### The Processing Pipeline

The engine follows a multi-stage pipeline architecture:

1. **Pre-Analysis** (`audio_analyzer.py`): Scans files for stability metrics (RMS, onset density, spectral flatness, crest factor) to identify usable regions. This gates the entire pipeline.

2. **Pad Mining** (`segment_miner.py`): Finds sustained, stable regions in full tracks and extracts loopable segments.

3. **Drone/Swell Generation** (`drone_maker.py`): Time-stretches and pitch-shifts tonal material into infinite loops (pads) and evolving one-shots (swells), with tonal variants (warm/airy/dark).

4. **Granular Synthesis** (`granular_maker.py`): Breaks audio into grains, applies quality filtering, and reassembles them into evolving cloud textures with pitch/time variation.

5. **Hiss/Dust Generation** (`hiss_maker.py`): Extracts high-frequency content from drums (or synthetic noise) to create "air" layers.

### Core Modules (`musiclib/`)

*   `io_utils.py`: File discovery, audio loading/saving, manifest management
*   `dsp_utils.py`: Filters, envelopes, normalization, windowing, random seed control
*   `audio_analyzer.py`: Pre-analysis and quality scoring (stability masks, grain quality)
*   `segment_miner.py`: Sustained segment extraction with phase-aligned loop points
*   `drone_maker.py`: Time/pitch processing with tonal filtering variants
*   `granular_maker.py`: Granular synthesis with per-grain quality gating
*   `hiss_maker.py`: High-frequency extraction and modulation
*   `music_theory.py`: Key/BPM detection, transposition utilities

### Entry Points

*   `make_textures.py`: Main CLI for single-file/directory processing
*   `process_batch.py`: Orchestrates batch processing across multiple source files
*   `validate_config.py`: Schema validation for `config.yaml`

### Batch Processing Utilities

*   `mine_drums.py`: Extract percussive segments from mixed tracks
*   `mine_silences.py`: Extract silent/ambient segments
*   `curate_best.py`: Filter and organize outputs by quality grade
*   `format_for_tr8s.py`: Format audio for TR-8S hardware (16-bit, mono/stereo conversion)
*   `make_curated_clouds.py`: Generate clouds from curated pad selections
*   `dust_pads.py`: Create dust-textured pads from existing material
*   `visualize_kit.py`: Generate visualizations of texture sets

## Configuration System

The machine is controlled by `config.yaml` (YAML format). Key sections:

*   `global`: Sample rate, bit depth, normalization target
*   `paths`: Input/output directory mappings
*   `pad_miner`: RMS thresholds, onset rate, spectral flatness, crossfade length
*   `drones`: Pitch shifts, time-stretch factors, swell envelopes, filter variants
*   `clouds`: Grain length, count, overlap, pitch range, quality thresholds
*   `hiss`: Bandpass frequencies, tremolo settings, flicker parameters
*   `pre_analysis`: Stability filters, quality scoring, region gating
*   `curation`: Quality grading thresholds, auto-deletion rules
*   `reproducibility`: Random seed for deterministic processing

**IMPORTANT**: Always run `python validate_config.py` after modifying config structure. Changes to thresholds can dramatically alter output quality and quantity.

## Development Workflow

### Environment Setup
```bash
# Create virtual environment (Python 3.11 recommended)
python -m venv venv311
source venv311/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# Single-source processing (all stages)
python make_textures.py --all

# Individual stages
python make_textures.py --mine-pads
python make_textures.py --make-drones
python make_textures.py --make-clouds
python make_textures.py --make-hiss

# Use custom config
python make_textures.py --all --config config_enhanced.yaml

# Batch processing
python process_batch.py --input_dir path/to/audio --project_name MY_PROJECT
```

### Testing

```bash
# Run full test suite
pytest

# Run specific test modules
pytest tests/test_integration.py
pytest tests/test_grading.py
pytest tests/test_batch_tools.py

# Run with verbose output
pytest -v

# Run single test
pytest tests/test_integration.py::test_full_pipeline_integration
```

Test data is synthesized on-the-fly using `create_sine_wave()` in integration tests. Tests use `tmp_path` fixtures and validate end-to-end pipeline functionality.

## Key Architectural Patterns

### Manifest System

All processing stages accumulate metadata rows in `config["_manifest"]`, which is written to `export/manifest.csv` at the end. Each row includes:
*   `filename`, `source`, `type`, `duration`
*   Quality metrics: `RMS`, `peak`, `crest`, `centroid`, `brightness`
*   Grading: `grade` (A-F based on curation thresholds)
*   Loop quality: `loop_seam_error` (for pads)

The manifest enables post-processing curation and organization.

### Quality Grading

Files are graded A-F based on:
*   **Grade F**: Silence (RMS < -60dB), clipping (peak > -0.1dB), extreme crest (>20)
*   **Grade D**: Near-silence, near-clipping, high crest
*   **Grade C**: Usable but low-quality
*   **Grade B**: Good quality
*   **Grade A**: Excellent quality

Set `curation.auto_delete_grade_f: true` to skip saving F-graded files.

### Reproducibility

Set `reproducibility.random_seed: <int>` in config for deterministic results. This seeds both NumPy and Python's stdlib random. Critical for testing and A/B comparisons.

### Pre-Analysis Gating

When `pre_analysis.enabled: true`, files are scanned for "stable" windows before processing. Grains/segments from unstable regions are rejected. This prevents wasting CPU on unusable material but can also be too aggressive—tune thresholds carefully.

### Batch Processing Flow

`process_batch.py` orchestrates:
1. Config preparation (per-project directory overrides)
2. Pad mining + drone generation
3. Per-file drum mining (`mine_drums.py`)
4. Per-file silence mining (`mine_silences.py`)
5. Curation (manual step via `curate_best.py`)
6. Final formatting (`format_for_tr8s.py`)

See `docs/BATCH_WORKFLOW.md` for detailed batch workflow documentation.

## Code Style & Conventions

*   **Type hints**: All functions should use type annotations
*   **Defensive coding**: Guard against silence, clipping, zero-length arrays
*   **Modular design**: Each module has a single responsibility
*   **Evocative naming**: Use terms like "texture," "surface," "stability," "grain" (not just "process," "data")
*   **Fail gracefully**: If optional dependencies (like librosa) are missing, skip features rather than crash

## Common Pitfalls

*   **Crossfade config migration**: Older configs use `pad_miner.crossfade_ms`; newer use `loop_crossfade_ms`. The code handles both, but validate carefully.
*   **RMS thresholds**: Too strict = no output. Too loose = noise/silence. Default range is -40dB to -10dB.
*   **Onset rate**: Lower = more sustained. Higher = allows more percussive material. Default is 3.0 onsets/sec.
*   **Pre-analysis overhead**: Enabling `pre_analysis` adds processing time. Disable for quick tests.
*   **Librosa warnings**: Short segments may trigger `n_fft` warnings. Usually harmless.
*   **Grain quality**: `grain_quality_threshold` too high = no grains. Too low = noise. Default is 0.4-0.6.

## Output Structure

```
export/
├── manifest.csv                    # Master metadata/grading sheet
└── <source_name>/
    ├── pads/                       # Loopable pad segments
    ├── swells/                     # One-shot swells with variants
    ├── clouds/                     # Granular cloud textures
    └── hiss/                       # Hiss loops + flicker bursts
```

All outputs are 44.1kHz WAV (16/24-bit), ready for TR-8S or any DAW/sampler.