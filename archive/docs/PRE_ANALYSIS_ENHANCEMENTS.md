# Cloud Quality Improvements: Pre-Analysis Enhancements (v0.3)

## Overview

This release improves granular cloud generation by implementing **per-file quality analysis** to identify and favor stable, high-quality regions before grain extraction. The changes are backward-compatible: existing workflows continue to work unchanged, while new tuning parameters enable fine-grained control.

## What's New

### 1. **Audio Analyzer Module** (`musiclib/audio_analyzer.py`)

A new lightweight analysis engine that computes **per-file statistics** on first load and caches them:

- **RMS Curve**: Windowed energy contour (in dB)
- **Onset Density**: Count of transient starts per window
- **Spectral Centroid**: Harmonic brightness per window
- **DC Offset**: Mean bias away from zero per window
- **Crest Factor**: Peak-to-RMS ratio per window (high = transient-like)

All metrics use the same window grid (configurable, default 1s windows with 0.5s hop), so analysis results are **reusable across pad mining and cloud grain extraction**.

**Key API**:
- `AudioAnalyzer(audio, sr, window_size_sec, hop_sec)`: Initialize and auto-compute all metrics
- `get_stable_regions(...)`: Boolean mask identifying usable audio windows
- `sample_from_stable_region(duration_sec, ...)`: Random sample from stable regions
- `get_stats_for_sample(start, end)`: Per-window stats for inspection

### 2. **Enhanced Grain Quality Scoring** (`granular_maker.py`)

The grain quality function now evaluates:

- **Silence Detection**: Harder penalties for RMS < 0.01 (was 0.01, now tiered)
- **DC Offset**: Catches bias from bad calibration (max 0.15 for reject, 0.08 for penalty)
- **Clipping & Crest**: Detects both hard clipping (peak > 0.95) and transient-like shapes (crest > 10)
- **Envelope Skew**: Penalizes uneven energy distribution (high skew = attack/decay mismatch)

Quality scores now range 0–1 with fine-grained penalties, improving **grain filtering accuracy**.

### 3. **Stable Region Biasing in Grain Extraction** (`granular_maker.py`)

The `extract_grains()` function now:

1. **Pre-analyzes** the source audio using `AudioAnalyzer`
2. **Identifies stable regions** (low onset density, mid-range RMS, low DC, reasonable crest)
3. **Biases grain start positions** towards stable regions (with fallback to random)
4. **Applies per-grain quality check** (existing filter enhanced with new metrics)

This avoids:
- Percussive transients (high onset density)
- Clipped regions (peaks near 1.0, extreme crest)
- DC-biased or underwater material (out-of-range RMS, large DC offset)
- Envelope mismatches (uneven skew)

Result: **grains extracted from cleaner, more sustained material** → smoother clouds with less crunchy artifacts.

### 4. **Optional Pre-Analysis in Pad Mining** (`segment_miner.py`)

The `extract_sustained_segments()` function can now use `AudioAnalyzer` to pre-filter:

- Adds `use_pre_analysis=True` parameter (default enabled)
- Stable regions computed once per file, then consulted during window-by-window analysis
- Pads extracted from windows flagged as stable by pre-analysis
- Existing RMS, onset, and spectral flatness checks still apply (layered filtering)

### 5. **New Configuration Section** (`config.yaml`)

```yaml
pre_analysis:
  enabled: true                         # Master switch
  analysis_window_sec: 1.0              # Analysis window size
  analysis_hop_sec: 0.5                 # Hop between windows

  # Stability thresholds
  max_onset_rate_hz: 3.0                # Max onsets/sec
  min_rms_db: -40.0                     # Min RMS
  max_rms_db: -10.0                     # Max RMS (clipping threshold)
  max_dc_offset: 0.1                    # Max DC bias
  max_crest_factor: 10.0                # Max peak/RMS

  # Quality scoring
  grain_quality_threshold: 0.4          # Min grain quality score
  skip_clipped_regions: true
  skip_transient_regions: true
```

**All parameters are optional** and default to sensible values. Existing `config.yaml` files without this section continue to work.

## Data Flow

```
Input audio (mono, 44.1 kHz)
    ↓
[1] AudioAnalyzer: Compute RMS, onset, DC, crest, centroid (cached)
    ↓
[2] get_stable_regions(): Boolean mask (0=junk, 1=usable)
    ↓
[3a] extract_grains() or extract_sustained_segments():
     - Bias start positions to stable windows
     - Apply per-segment quality checks
     - Extract high-quality grains/pads
    ↓
[4] Pitch-shift, window, and place grains into cloud
    ↓
Output: Cleaner, less crunchy granular textures
```

## Implementation Notes

### Performance

- **One-time cost**: AudioAnalyzer computes ~12 features per window (RMS, onset count, DC, crest, centroid)
  - For a 60s file at 44.1 kHz with 1s windows: ~60 windows, ~100ms overhead (negligible)
- **Caching**: All metrics cached in analyzer object; reused across calls
- **Fallback**: If pre-analysis disabled or fails, code falls back to random grain extraction (safe)

### Backward Compatibility

- **AudioAnalyzer is optional**: `create_cloud()` calls it internally, but `extract_grains()` accepts `analyzer=None` and works without it
- **Config is optional**: New `pre_analysis` section not required; defaults apply if missing
- **Existing files unchanged**: No changes to pad_sources/ or source_audio/ workflows; optional parameters only

### Stereo Handling

- Audio is converted to **mono for all analysis** (sum of channels)
- Exports remain stereo if configured; grains drawn from mono analysis (consistent across channels)
- Prevents channel imbalances from biasing grain selection

## Tuning Guide

### For Cleaner Clouds

**Goal**: Minimize crunchy, transient grains

```yaml
pre_analysis:
  max_crest_factor: 8.0         # Stricter (avoid transients)
  max_onset_rate_hz: 2.0        # More sustained regions only
  grain_quality_threshold: 0.5  # Reject borderline grains
```

### For More Energy / Density

**Goal**: Include more "texture" even if slightly rougher

```yaml
pre_analysis:
  max_crest_factor: 12.0        # More permissive
  max_onset_rate_hz: 4.0        # Include some transients
  grain_quality_threshold: 0.3  # Accept more grains
```

### For Specific Material

**Goal**: Fine-tune for drums, pads, or synths

- **Drums** (lots of transients): Raise `max_onset_rate_hz` to 5–6, increase `max_crest_factor` to 15
- **Pads** (sustained): Lower `max_onset_rate_hz` to 1.5, lower `max_crest_factor` to 6
- **Mixed**: Keep defaults; pre-analysis auto-detects stable regions

## Testing Recommendations

1. **Before**: Run `python make_textures.py --make-clouds` on existing source files
2. **After**: Re-run same command; compare output clouds for subjective quality
3. **Listen for**: Less crunchiness, smoother evolution, better sustain
4. **Adjust**: If too smooth, raise `max_crest_factor` or `grain_quality_threshold`; if still rough, lower thresholds

## Future Work

- **Perceptual loudness (LUFS)**: Replace simple RMS with loudness-normalized metrics
- **Harmonic/noise ratio**: Identify tonal vs. noise-based grains
- **Spectral stability**: Flag regions where harmonic content shifts rapidly
- **ML scoring**: Train a classifier on manually-labeled good/bad grain examples
