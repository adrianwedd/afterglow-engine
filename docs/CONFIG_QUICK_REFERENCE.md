# Configuration Quick Reference (v0.8)

Quick lookup guide for the key configuration blocks. See `config.yaml` and `CHANGELOG.md` for full details.

---

## Global Settings

```yaml
global:
  sample_rate: 44100                    # Hz (TR-8S standard)
  output_bit_depth: 24                  # 16 or 24-bit
  target_peak_dbfs: -1.0                # Normalization target
```

---

## Pad Miner (Segment Extraction)

```yaml
pad_miner:
  target_durations_sec: [2.0, 3.5]      # Multiple durations (list)
  loop_crossfade_ms: 100                # Loop smoothing (ms)

  min_rms_db: -40.0                     # Min loudness threshold
  max_rms_db: -10.0                     # Max loudness threshold
  max_onset_rate_per_second: 3.0        # Max transients (onsets/sec)
  spectral_flatness_threshold: 0.5      # Tonality threshold (0-1)
  max_candidates_per_file: 3            # Pads per source
  window_hop_sec: 0.5                   # Sliding window hop
```

**Examples**:
```yaml
# Short, snappy pads (various lengths)
target_durations_sec: [1.5, 2.5, 3.5]

# Smooth, long crossfade
loop_crossfade_ms: 150

# Quick loop with minimal crossfade
loop_crossfade_ms: 50
```

---

## Drones (Pads & Swells)

```yaml
drones:
  pad_loop_duration_sec: 2.0            # Pad length
  pad_variants: [warm, airy, dark]      # Tonal variants to create

  warm_lowpass_hz: 3000                 # Warm variant: LPF cutoff
  airy_highpass_hz: 6000                # Airy variant: HPF cutoff
  dark_high_cut_hz: 1500                # Dark variant: LPF cutoff

  swell_duration_sec: 6.0               # Swell length
  fade_in_sec: 0.5                      # Swell fade-in
  fade_out_sec: 1.5                     # Swell fade-out

  pitch_shift_semitones: [0, 7, 12]     # Pitch shifts to apply
  time_stretch_factors: [1.0, 1.5, 2.0] # Time-stretch multipliers
  enable_reversal: true                 # Create reversed variants
```

**Examples**:
```yaml
# Conservative filtering
warm_lowpass_hz: 4000
airy_highpass_hz: 5000

# Aggressive variants
dark_high_cut_hz: 800

# More swell variations
swell_duration_sec: 8.0
fade_out_sec: 2.0

# Subtle time-stretch
time_stretch_factors: [1.0, 1.2]

# No reversal variants
enable_reversal: false
```

---

## Granular Clouds

```yaml
clouds:
  grain_length_min_ms: 50               # Min grain size
  grain_length_max_ms: 150              # Max grain size
  grains_per_cloud: 200                 # Grains per cloud
  cloud_duration_sec: 6.0               # Cloud length

  pitch_shift_range:                    # Min/max pitch shift
    min: -8                             # Lower bound (semitones)
    max: 8                              # Upper bound (semitones)

  overlap_ratio: 0.65                   # Grain overlap (0.5-1.0)
  lowpass_hz: 8000                      # Post-processing LPF
  clouds_per_source: 2                  # Clouds per source
  target_peak_dbfs: -3.0                # Gentler normalization to avoid saturation on dense overlaps
```

**Examples**:
```yaml
# Subtle pitch variation
pitch_shift_range:
  min: -3
  max: 3

# Wild, dissonant clouds
pitch_shift_range:
  min: -12
  max: 12

# Shorter, denser grains
grain_length_min_ms: 30
grain_length_max_ms: 80

# Tighter overlap
overlap_ratio: 0.8

# No post-filtering
lowpass_hz: 0

# Softer output with headroom
target_peak_dbfs: -3.0
```

---

## Hiss / Air Textures

```yaml
hiss:
  loop_duration_sec: 1.5                # Hiss loop length

  highpass_hz: 6000                     # HPF cutoff (if bandpass=false)
  bandpass_low_hz: 5000                 # ⭐ NEW: Band-pass low
  bandpass_high_hz: 14000               # ⭐ NEW: Band-pass high
  use_bandpass: true                    # Use band-pass filter

  tremolo_rate_hz: 3.0                  # Modulation rate
  tremolo_depth: 0.6                    # Modulation depth (0-1)
  hiss_loops_per_source: 2              # Loops per source

  flicker_min_ms: 50                    # Min flicker length
  flicker_max_ms: 300                   # Max flicker length
  flicker_count: 4                      # Flickers to generate

  use_synthetic_noise: true             # Use white noise fallback
  synthetic_noise_level_db: -10.0       # Noise level
```

**Examples**:
```yaml
# Bright air (7kHz–16kHz)
bandpass_low_hz: 7000
bandpass_high_hz: 16000

# Warm resonance (4kHz–10kHz)
bandpass_low_hz: 4000
bandpass_high_hz: 10000

# Pure high-pass (no band-pass)
use_bandpass: false
highpass_hz: 8000

# Subtle modulation
tremolo_rate_hz: 1.5
tremolo_depth: 0.3

# More aggressive flickers
flicker_max_ms: 500
flicker_count: 8
```

---

## Export Settings

```yaml
export:                                 # Stereo/mono control
  pads_stereo: false                    # Mono pads (default)
  swells_stereo: false                  # Mono swells (default)
  clouds_stereo: false                  # Mono clouds (default)
  hiss_stereo: false                    # Mono hiss (default)

reproducibility:
  random_seed: null                     # Set to an int for deterministic grain placement/runs
```

**Examples**:
```yaml
# Stereo pads & clouds
export:
  pads_stereo: true
  clouds_stereo: true

# Stereo for final master, mono for sketching
pads_stereo: false
swells_stereo: true
```

---

## Brightness Tagging

```yaml
brightness_tags:                        # Dark/mid/bright tags
  enabled: true                         # Enable tagging
  centroid_low_hz: 1500                 # Dark ↔ mid threshold
  centroid_high_hz: 3500                # Mid ↔ bright threshold
```

**Classification Logic**:
- Centroid < `centroid_low_hz` → **dark**
- Centroid between → **mid**
- Centroid > `centroid_high_hz` → **bright**

**Examples**:
```yaml
# More dark/less bright (lower thresholds)
centroid_low_hz: 1000
centroid_high_hz: 2500

# Less dark/more bright (higher thresholds)
centroid_low_hz: 2000
centroid_high_hz: 4500

# Disable tagging (numeric filenames only)
enabled: false
```

---

## Curation & Manifest (v0.5)

```yaml
curation:
  auto_delete_grade_f: false            # Delete "Fail" textures immediately?
  thresholds:
    min_rms_db: -60.0                   # Silence threshold
    clipping_tolerance: 0.01            # Peak > 0.99 = Fail
    max_crest_factor: 25.0              # Extreme transient = Fail
```

---

## Musicality (v0.6)

```yaml
musicality:
  reference_bpm: "detect"               # "detect" or a number (e.g., 120)
  snap_to_grid: false                   # If true, bar_lengths converted to seconds using BPM
  bar_lengths: [1, 2, 4]                # Bars to target when snapping
  target_key: null                      # e.g., "C maj" to auto-transpose; null to keep detected
```

## Directory Paths

```yaml
paths:
  source_audio_dir: source_audio        # Input: scan for pads
  pad_sources_dir: pad_sources          # Input: drone/cloud material
  drums_dir: drums                      # Input: hiss material
  export_dir: export                    # Output root
```

---

## Quick Tuning Recipes

### Dark, Textural (Low-End Focus)

```yaml
pad_miner:
  target_durations_sec: [2.0, 3.0]

drones:
  dark_high_cut_hz: 800

clouds:
  pitch_shift_range: { min: -5, max: 3 }
  lowpass_hz: 5000

hiss:
  bandpass_low_hz: 3000
  bandpass_high_hz: 8000

brightness_tags:
  centroid_low_hz: 1000
  centroid_high_hz: 2500
```

### Bright, Airy (Hi-Fi)

```yaml
pad_miner:
  target_durations_sec: [1.5, 2.5]
  loop_crossfade_ms: 50

drones:
  airy_highpass_hz: 8000

clouds:
  pitch_shift_range: { min: -2, max: 8 }
  lowpass_hz: 12000

hiss:
  bandpass_low_hz: 8000
  bandpass_high_hz: 16000

brightness_tags:
  centroid_low_hz: 3000
  centroid_high_hz: 6000
```

### Experimental (Maximum Variation)

```yaml
pad_miner:
  target_durations_sec: [1.0, 2.0, 3.5, 5.0]
  max_candidates_per_file: 5

clouds:
  pitch_shift_range: { min: -12, max: 12 }
  grains_per_cloud: 300
  overlap_ratio: 0.8

export:
  clouds_stereo: true
  pads_stereo: true

brightness_tags:
  enabled: true
```

### Conservative (Quick & Simple)

```yaml
pad_miner:
  target_durations_sec: [2.0]

clouds:
  pitch_shift_range: { min: -4, max: 4 }

export:
  pads_stereo: false
  clouds_stereo: false

brightness_tags:
  enabled: false
```

---

## Common Adjustments

| Goal | Change |
|------|--------|
| More pads | ↑ `max_candidates_per_file` |
| Softer loops | ↑ `loop_crossfade_ms` |
| Faster clouds | ↑ `overlap_ratio` |
| Brighter hiss | ↑ `bandpass_low_hz` |
| Richer drones | ↑ `time_stretch_factors` values |
| Tagged filenames | Set `brightness_tags.enabled: true` |
| Stereo output | Set category `_stereo: true` |
| Stable pitch | ↓ `pitch_shift_range.max` |

---

## Validation Checklist

- [ ] `global.sample_rate` is 44100 (TR-8S standard)
- [ ] All paths exist or will be created (auto-created on first run)
- [ ] All Hz values are positive (frequencies)
- [ ] `overlap_ratio` is between 0.5–1.0
- [ ] `pad_miner.target_durations_sec` is a list, e.g., `[2.0, 3.5]`
- [ ] `brightness_tags.centroid_low_hz` < `centroid_high_hz`
- [ ] YAML indentation is correct (2 spaces, not tabs)

---

## Default Values (Fallbacks)

If a config key is missing, these internal defaults apply:

```python
# Pad miner
target_durations = [2.0]
loop_crossfade_ms = 100

# Clouds
pitch_shift_range = {min: -7, max: 7}  # from max_pitch_shift_semitones

# Hiss
bandpass_low_hz = 5000
bandpass_high_hz = 14000

# Export
pads_stereo = False
clouds_stereo = False

# Brightness
centroid_low_hz = 1500
centroid_high_hz = 3500
```

---

## See Also

- `config.yaml` – Full configuration with inline comments
- `README.md` – Feature overview and workflows
- `UPGRADES.md` – Detailed upgrade documentation
- `IMPLEMENTATION_SUMMARY.md` – Technical details of changes
