# Comprehensive Code Review: Audio Texture Generation Toolchain

## Executive Summary

The audio texture generation toolchain is **well-structured and functionally sound**. The modular design cleanly separates concerns (discovery, analysis, DSP, I/O), and the v0.2 upgrade demonstrates good backwards compatibility practices. Most improvements are incremental refinements to robustness, performance, and clarity rather than fundamental architectural issues.

**Overall Assessment**: Production-ready for small to medium projects (~100-500 tracks). Well-documented. Good stability.

**Key Strengths**:
- Clean module separation with clear responsibilities
- Thoughtful handling of edge cases (already done in v0.2)
- Good use of librosa for audio analysis
- Configuration-driven design supports flexibility
- Graceful fallbacks for backwards compatibility

**Key Areas for Improvement**:
1. Config parsing needs stricter validation and centralized defaults
2. Some DSP functions could be more robust at boundaries
3. Opportunity to reduce file I/O by batching operations
4. CLI could accept config overrides for batch workflows
5. Logging/error handling could be more sophisticated

---

## 1. Architecture & Design

### 1.1 Module Layout (GOOD)

**Current structure is sound:**

```
musiclib/
├── io_utils.py       → File I/O, discovery, logging
├── dsp_utils.py      → Filters, envelopes, normalization
├── segment_miner.py  → Pad extraction with analysis
├── drone_maker.py    → Time-stretch, pitch-shift, swell generation
├── granular_maker.py → Grain extraction, cloud synthesis
└── hiss_maker.py     → Noise/hiss processing
```

**Assessment**: Excellent cohesion. Each module has a single, clear purpose. Coupling is minimal (all modules depend on `dsp_utils` and `io_utils`, which is appropriate).

### 1.2 Suggested Refactorings (Minor)

**Issue 1: Config Defaults Are Scattered**

Currently, defaults live in:
- `make_textures.py` (DEFAULT_CONFIG_YAML)
- Each function signature (e.g., `centroid_low_hz=1500` in `classify_brightness()`)
- Fallback logic in segment_miner, granular_maker, hiss_maker

**Recommendation**: Create a `config_defaults.py` module:

```python
# musiclib/config_defaults.py
"""Default configuration values and schema."""

DEFAULTS = {
    'global': {
        'sample_rate': 44100,
        'output_bit_depth': 24,
        'target_peak_dbfs': -1.0,
    },
    'paths': {
        'source_audio_dir': 'source_audio',
        'pad_sources_dir': 'pad_sources',
        'drums_dir': 'drums',
        'export_dir': 'export/tr8s',
    },
    'pad_miner': {
        'target_durations_sec': [2.0],
        'loop_crossfade_ms': 100,
        'min_rms_db': -40.0,
        'max_rms_db': -10.0,
        'max_onset_rate_per_second': 3.0,
        'spectral_flatness_threshold': 0.5,
        'max_candidates_per_file': 3,
        'window_hop_sec': 0.5,
    },
    # ... rest of config
}

def get_config_with_defaults(user_config: dict) -> dict:
    """Merge user config with defaults, with type checking."""
    # Implementation
```

**Benefit**: Single source of truth. Easier to document. Can add validation.

---

**Issue 2: Config Merging Logic is Ad-Hoc**

Each module reads config keys like:
```python
loop_crossfade_ms = cfg['pad_miner'].get('loop_crossfade_ms', cfg['pad_miner'].get('crossfade_ms', 100))
```

**Recommendation**: Create a helper function in `config_defaults.py`:

```python
def get_config_key(config: dict, *keys, default=None):
    """Get first available key from config, with fallback chain."""
    for key_path in keys:
        parts = key_path.split('.')
        value = config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                break
        if value is not None:
            return value
    return default
```

Use as: `loop_crossfade_ms = get_config_key(config, 'pad_miner.loop_crossfade_ms', 'pad_miner.crossfade_ms', default=100)`

---

**Issue 3: Error Logging is Inconsistent**

- `io_utils.py` prints errors directly with `print(f"[!] Failed...")`
- Some modules return `None` on failure, others raise
- No centralized logging configuration

**Recommendation**: Add a simple logging wrapper in `io_utils.py`:

```python
import logging

logger = logging.getLogger('musiclib')

def configure_logging(verbose: bool = True):
    """Set up logging for the library."""
    level = logging.DEBUG if verbose else logging.WARNING
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

# Usage: logger.warning(), logger.error(), etc.
```

---

## 2. Correctness & Edge Cases

### 2.1 Critical Issues

**None identified**. The code is generally well-protected against crashes.

### 2.2 Robust Edge Cases (Already Handled)

✅ `segment_miner.py:40-41`: Checks if audio is shorter than window
✅ `io_utils.py:51-56`: Graceful failure on corrupt audio files
✅ `dsp_utils.py:25-26`: Checks for zero peak to avoid division errors
✅ `granular_maker.py:30-43`: Pads grains if they fall short

### 2.3 Potential Improvements

**Issue 1: Boundary Check in `crossfade()` is Fragile**

```python
def crossfade(audio1: np.ndarray, audio2: np.ndarray, fade_length: int) -> np.ndarray:
    # ...
    result = np.concatenate([audio1[:-fade_length], audio2[fade_length:]])
    overlap_region = (audio1[-fade_length:] * fade_out + audio2[:fade_length] * fade_in)
    result = np.concatenate([audio1[:-fade_length], overlap_region, audio2[fade_length:]])
```

**Problem**:
- If `fade_length >= len(audio1)` or `fade_length >= len(audio2)`, slicing will fail or produce unexpected results
- The crossfade is always symmetric; should support asymmetric fades

**Recommendation**:

```python
def crossfade(audio1: np.ndarray, audio2: np.ndarray, fade_length: int) -> np.ndarray:
    """
    Crossfade between two audio signals.

    Args:
        audio1: First audio signal
        audio2: Second audio signal
        fade_length: Length of fade in samples (must be < len(audio1) and < len(audio2))

    Returns:
        Crossfaded audio

    Raises:
        ValueError: If fade_length is too long
    """
    if fade_length > len(audio1) or fade_length > len(audio2):
        raise ValueError(
            f"fade_length ({fade_length}) exceeds audio length. "
            f"audio1={len(audio1)}, audio2={len(audio2)}"
        )

    fade_out = np.linspace(1, 0, fade_length)
    fade_in = np.linspace(0, 1, fade_length)

    overlap_region = (audio1[-fade_length:] * fade_out +
                      audio2[:fade_length] * fade_in)
    result = np.concatenate([
        audio1[:-fade_length],
        overlap_region,
        audio2[fade_length:]
    ])
    return result
```

---

**Issue 2: Mono/Stereo Handling Not Enforced**

`io_utils.load_audio()` has `mono=True` by default, so files are loaded as mono. But:
- No assertion that output is mono
- Some modules assume mono, but it's not documented
- If someone loads stereo audio and passes it to a mono-expecting function, it silently processes channel 0

**Recommendation**: Add type hints and assertions:

```python
def load_audio(filepath: str, sr: int = 44100, mono: bool = True) -> Tuple[np.ndarray, int]:
    """
    Load audio file.

    Returns:
        (audio, sr) where audio shape is (samples,) if mono, (channels, samples) if stereo
    """
    y, sr_orig = librosa.load(filepath, sr=sr, mono=mono)
    if mono:
        assert y.ndim == 1, f"Expected 1D mono, got {y.ndim}D"
    else:
        assert y.ndim <= 2, f"Expected 1D or 2D, got {y.ndim}D"
    return y, sr
```

---

**Issue 3: Sample Rate Mismatch Risk**

- `load_audio()` forces `sr=44100` by default
- If a file is already 44.1kHz, librosa will pass through the original
- If a file is 48kHz or 96kHz, librosa resamples automatically
- But there's no logging of resampling—it's silent

**Recommendation**: Log when resampling occurs:

```python
def load_audio(filepath: str, sr: int = 44100, mono: bool = True) -> Tuple[np.ndarray, int]:
    y, sr_orig = librosa.load(filepath, sr=sr, mono=mono)
    if sr_orig != sr and sr_orig is not None:
        logger.info(f"Resampled {filepath}: {sr_orig}Hz → {sr}Hz")
    return y, sr
```

---

**Issue 4: Onset Detection Can Fail on Silent Audio**

```python
# segment_miner.py:46-48
onset_strength = librosa.onset.onset_strength(y=audio, sr=sr)
onset_frames = librosa.onset.onset_detect(
    onset_strength=onset_strength, sr=sr, units='samples'
)
```

If `audio` is completely silent or has very low energy, `onset_strength` will be all zeros, and `onset_detect` might return an empty array. The code handles this (line 62 will just set `onsets_in_window=0`), but it's worth documenting.

---

**Issue 5: RMS Calculation Doesn't Avoid DC Offset**

```python
def rms_energy(audio: np.ndarray) -> float:
    return np.sqrt(np.mean(audio ** 2))
```

This includes DC offset. For audio, this is fine (files are usually AC-coupled), but for synthesis, DC can skew the result.

**Recommendation**: Add optional DC removal:

```python
def rms_energy(audio: np.ndarray, remove_dc: bool = True) -> float:
    """Calculate RMS energy, optionally removing DC offset."""
    if remove_dc:
        audio = audio - np.mean(audio)
    return np.sqrt(np.mean(audio ** 2))
```

---

## 3. Performance & Scalability

### 3.1 Current Performance (Good for Small Libraries)

**Benchmarks (estimated for a 5-minute 44.1kHz mono file):**
- Load & analysis: ~2–5 seconds (librosa onset detection is the bottleneck)
- Pad mining (3 candidates): ~3–10 seconds
- Swell generation (6 variants): ~5 seconds
- Cloud generation (6 clouds): ~10 seconds
- Hiss generation (8 loops + 4 flickers): ~3 seconds
- **Total per track**: ~20–30 seconds

**Scaling to 100 tracks**: ~30–50 minutes, which is acceptable.

### 3.2 Performance Bottlenecks & Improvements

**Issue 1: Repeated Analysis Across Modules**

Currently, each module independently:
- Loads the audio file
- Computes onset strength / spectral properties

If you run all four pipelines on the same source file, librosa.onset_strength is computed 2–3 times.

**Recommendation**: Cache analysis results:

```python
# In make_textures.py
class AudioAnalysisCache:
    def __init__(self):
        self.cache = {}

    def get_onset_strength(self, filepath: str, sr: int):
        key = (filepath, sr)
        if key not in self.cache:
            audio, sr = io_utils.load_audio(filepath, sr=sr, mono=True)
            onset_strength = librosa.onset.onset_strength(y=audio, sr=sr)
            self.cache[key] = (audio, onset_strength)
        return self.cache[key]

# Usage:
cache = AudioAnalysisCache()
audio, onset_strength = cache.get_onset_strength(filepath, 44100)
```

**Benefit**: Reusing analysis avoids recomputation. For 4 texture types on the same source, saves ~2 seconds.

---

**Issue 2: Synthetic Noise Is Regenerated Each Time**

```python
# hiss_maker.py
if len(audio) > target_samples:
    # use audio chunk
else:
    # use synthetic noise (no caching)
```

If no drum files are available, synthetic noise is created from scratch each time. This is fast (~10ms) but could be cached.

**Recommendation**: Not urgent, but if scaling to many tracks, consider:

```python
# In hiss_maker.py
def make_hiss_loop(..., noise_cache=None):
    if noise_cache and 'synthetic_white' in noise_cache:
        audio = noise_cache['synthetic_white']
    else:
        audio = create_synthetic_noise(...)
```

---

**Issue 3: Librosa Pitch Shifting is Per-Grain**

```python
# granular_maker.py:76
return librosa.effects.pitch_shift(grain, sr=sr, n_steps=shift)
```

For a cloud with 200 grains × 6 clouds × 3 pitch shifts = 3,600 pitch-shift operations. `librosa.effects.pitch_shift` uses STFT internally, which is relatively slow (~50ms per call).

**For now**: This is acceptable. 200 grains × 50ms = 10 seconds per source file is manageable.

**Future optimization** (if needed): Use a faster pitch-shift library like `pyrubberband` or batch pitch-shift operations via STFT reuse.

---

**Issue 4: No Parallel Processing**

The batch script will be single-threaded. For 100 tracks, this is fine (~50 min runtime). If scaling to 1000+ tracks, consider:

```python
# batch_generate_textures.py (future enhancement)
from multiprocessing import Pool

with Pool(processes=4) as pool:
    pool.map(process_track, selected_tracks)
```

**For now**: Not necessary. Single-threaded is simpler and sufficient.

---

## 4. Configuration & UX

### 4.1 Current Config Handling

**Strengths**:
- YAML is human-friendly
- v0.2 added backwards compatibility with fallback logic
- Default embedded in `make_textures.py` for quick starts

**Weaknesses**:
- No schema validation (typos in config.yaml silently use defaults)
- Fallback logic is scattered across modules
- No way to override config at CLI (e.g., `--pitch-range 8 12`)

### 4.2 Suggested Improvements

**Issue 1: Config Validation**

Add a validation function:

```python
# musiclib/config_validation.py
from typing import Dict, Any, List, Tuple

VALIDATORS = {
    'global.sample_rate': lambda x: isinstance(x, int) and x > 0,
    'global.output_bit_depth': lambda x: x in (16, 24, 32),
    'pad_miner.target_durations_sec': lambda x: isinstance(x, list) and all(v > 0 for v in x),
    'clouds.pitch_shift_range.min': lambda x: isinstance(x, (int, float)),
    'clouds.pitch_shift_range.max': lambda x: isinstance(x, (int, float)),
    'hiss.bandpass_low_hz': lambda x: x > 0,
    'hiss.bandpass_high_hz': lambda x: x > 0,
}

WARNINGS = {
    'hiss.bandpass_high_hz': lambda x: x <= 20000 or "WARNING: Bandpass high > 20kHz (above audible range)",
    'pad_miner.target_durations_sec': lambda x: all(d >= 1.0 for d in x) or "WARNING: Some pads < 1s (very short)",
}

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate config against schema.

    Returns:
        (is_valid, errors_and_warnings)
    """
    errors = []

    # Check for obvious anomalies
    if 'hiss' in config:
        if config['hiss'].get('bandpass_low_hz', 5000) >= config['hiss'].get('bandpass_high_hz', 14000):
            errors.append("ERROR: hiss.bandpass_low_hz >= bandpass_high_hz")

    # Run validators
    for key, validator in VALIDATORS.items():
        value = get_nested(config, key)
        if value is not None and not validator(value):
            errors.append(f"INVALID: {key} = {value}")

    return len(errors) == 0, errors

# In make_textures.py
config = load_yaml_config(config_file)
is_valid, issues = validate_config(config)
if not is_valid:
    for issue in issues:
        logger.error(issue)
    sys.exit(1)
```

---

**Issue 2: CLI Config Overrides**

Current: `make_textures.py --all` only uses `config.yaml`.

**Recommendation**: Add simple override flags:

```python
# In make_textures.py main()
parser.add_argument('--pitch-range', nargs=2, type=float, metavar=('MIN', 'MAX'),
                    help='Override clouds.pitch_shift_range (e.g., --pitch-range -5 5)')
parser.add_argument('--stereo', action='store_true',
                    help='Export all categories as stereo')
parser.add_argument('--config', type=str,
                    help='Path to custom config.yaml')

args = parser.parse_args()

# Load config from file or use default
if args.config:
    config = load_yaml_config(args.config)
else:
    config = yaml.safe_load(DEFAULT_CONFIG_YAML)

# Apply CLI overrides
if args.pitch_range:
    config['clouds']['pitch_shift_range'] = {
        'min': args.pitch_range[0],
        'max': args.pitch_range[1]
    }

if args.stereo:
    for key in ['pads_stereo', 'swells_stereo', 'clouds_stereo', 'hiss_stereo']:
        config['export'][key] = True
```

**Benefit**: Makes batch workflows simpler (one script, multiple profiles via flags).

---

## 5. DSP Quality

### 5.1 Current DSP (Good)

**Strengths**:
- ✅ Hann windowing for grains (reduces spectral leakage)
- ✅ Band-pass filtering in hiss (well-chosen frequency range)
- ✅ Tremolo modulation (adds movement)
- ✅ Sensible defaults (pads 2.0s, clouds 6.0s, hiss 1.5s)

### 5.2 Potential Improvements

**Issue 1: No Anti-Aliasing Check**

When pitch-shifting grains up by large amounts (e.g., +12 semitones), the frequency content doubles. If the grain is 50ms and contains frequencies up to 22kHz, shifting up can create aliasing.

**Current**: Not an issue in practice because:
- Grains are short (50–150ms), so they're mostly low/mid frequencies
- Hann windowing attenuates spectral splatter
- Output is normalized to -1 dBFS, which prevents clipping

**Recommendation**: Add a note in docstring:

```python
def apply_pitch_shift_grain(grain, sr, min_shift_semitones, max_shift_semitones):
    """
    Apply random pitch shift to a grain.

    Note: For large upward shifts (> +12 semitones), consider applying
    a post-processing low-pass filter to avoid aliasing. Current default
    (max ±8 semitones) is safe.
    """
```

---

**Issue 2: Tremolo Modulation Doesn't Fade In/Out**

```python
# hiss_maker.py
tremolo = np.sin(2 * np.pi * tremolo_rate_hz * t) * 0.5 + 0.5
```

The sine wave oscillates from 0 to 1 immediately, which can create a click at the start/end of the hiss loop.

**Recommendation**: Add a short fade in/out:

```python
tremolo = np.sin(2 * np.pi * tremolo_rate_hz * t) * 0.5 + 0.5

# Fade in/out over 50ms
fade_length = min(int(sr * 0.05), len(tremolo) // 4)
if fade_length > 0:
    tremolo[:fade_length] *= np.linspace(0, 1, fade_length)
    tremolo[-fade_length:] *= np.linspace(1, 0, fade_length)
```

---

**Issue 3: Normalization Doesn't Check for DC Offset**

```python
def normalize_audio(audio, target_peak_dbfs=-1.0):
    peak = np.max(np.abs(audio))
    target_linear = 10 ** (target_peak_dbfs / 20.0)
    return audio * (target_linear / peak)
```

If audio has a large DC offset (e.g., mean = 0.1), the peak might be 0.5, and normalization will scale based on that, potentially leaving DC in the output.

**Recommendation**: Optional DC removal:

```python
def normalize_audio(audio, target_peak_dbfs=-1.0, remove_dc=True):
    """Normalize and optionally remove DC offset."""
    if remove_dc:
        audio = audio - np.mean(audio)

    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio

    target_linear = 10 ** (target_peak_dbfs / 20.0)
    return audio * (target_linear / peak)
```

---

**Issue 4: Loop Crossfade Doesn't Address Phase Discontinuity**

Currently, crossfading the loop point assumes that the two sides have compatible phase. But extracting a random segment of audio might have a phase mismatch, causing a subtle click even with crossfade.

**Current workaround**: Crossfade length of 100ms (~4.4k samples at 44.1kHz) is usually enough to mask clicks.

**Recommendation**: Document this and suggest increasing crossfade if clicks are audible:

```python
# In config.yaml comments:
loop_crossfade_ms: 100  # Increase to 150–200ms if loop clicks are audible
```

---

## 6. API & CLI

### 6.1 Current CLI (Functional)

**Current usage:**
```bash
python make_textures.py --all
python make_textures.py --mine-pads
python make_textures.py --make-drones
python make_textures.py --make-clouds
python make_textures.py --make-hiss
```

**Strengths**:
- Simple, easy to understand
- Each phase can run independently
- Works with hardcoded `config.yaml` in repo root

### 6.2 Suggested Enhancements

**Issue 1: No Way to Specify Root Directory**

For batch workflows, want to run:
```bash
cd work/track_slug/
python ../../make_textures.py --all
```

But this assumes `config.yaml` is in the current directory or `../..`.

**Recommendation**: Add `--root` argument:

```python
parser.add_argument('--root', type=str, default='.',
                    help='Root directory (for input config.yaml and relative paths)')
parser.add_argument('--config', type=str,
                    help='Path to config.yaml (overrides default)')

args = parser.parse_args()

# Resolve config path
if args.config:
    config_path = args.config
else:
    config_path = os.path.join(args.root, 'config.yaml')
    if not os.path.exists(config_path):
        config_path = 'config.yaml'  # Fallback to current dir

config = load_yaml_config(config_path)
```

**Usage in batch script:**
```bash
python make_textures.py --root work/track_slug/ --all
```

---

**Issue 2: No Return Status or Summary**

Currently, `make_textures.py` prints progress but doesn't indicate:
- How many files were generated
- Which phases failed
- Whether to continue to the next track

**Recommendation**: Add JSON output mode:

```python
parser.add_argument('--json-output', type=str,
                    help='Write summary to JSON file')

# At end of main():
if args.json_output:
    summary = {
        'status': 'success' if all_ok else 'failed',
        'pads_count': len(glob('export/tr8s/pads/*.wav')),
        'swells_count': len(glob('export/tr8s/swells/*.wav')),
        'clouds_count': len(glob('export/tr8s/clouds/*.wav')),
        'hiss_count': len(glob('export/tr8s/hiss/*.wav')),
        'errors': error_list,
    }
    with open(args.json_output, 'w') as f:
        json.dump(summary, f, indent=2)
```

---

**Issue 3: No Dry-Run Mode**

For batch workflows, useful to preview what would be generated without running the full pipeline.

**Recommendation**: Add `--dry-run`:

```python
parser.add_argument('--dry-run', action='store_true',
                    help='Show what would be done without processing')

# In each phase, wrap with:
if args.dry_run:
    print(f"[DRY RUN] Would generate {N} files in {output_dir}")
    return
```

---

## 7. Testing & Reliability

### 7.1 Suggested Testing Strategy

The current project has no automated tests. For a production workflow, suggest:

#### Minimal Test Suite

```
tests/
├── __init__.py
├── conftest.py                    # pytest fixtures
├── test_io_utils.py               # File I/O
├── test_dsp_utils.py              # DSP operations
├── test_segment_miner.py          # Pad extraction
├── test_granular_maker.py         # Grain synthesis
└── test_integration.py            # End-to-end
```

**Test fixtures** (synthetic test signals):
```python
# tests/conftest.py
import pytest
import numpy as np

@pytest.fixture
def sine_wave():
    """1-second 440Hz sine at 44.1kHz."""
    sr = 44100
    t = np.arange(sr) / sr
    return np.sin(2 * np.pi * 440 * t), sr

@pytest.fixture
def silent_audio():
    """1-second silence."""
    return np.zeros(44100), 44100

@pytest.fixture
def short_audio():
    """100ms audio (edge case)."""
    return np.random.randn(int(44100 * 0.1)), 44100

@pytest.fixture
def multichannel_audio():
    """Stereo audio (2 channels)."""
    return np.random.randn(2, 44100), 44100
```

#### Unit Tests (Priority 1)

```python
# tests/test_dsp_utils.py
def test_normalize_zero_peak(silent_audio):
    """Normalize should handle zero peak."""
    audio, sr = silent_audio
    result = dsp_utils.normalize_audio(audio)
    assert np.allclose(result, audio)

def test_normalize_range(sine_wave):
    """Normalized audio should have correct peak."""
    audio, sr = sine_wave
    result = dsp_utils.normalize_audio(audio, target_peak_dbfs=-1.0)
    peak = np.max(np.abs(result))
    target = 10 ** (-1.0 / 20.0)
    assert np.isclose(peak, target, atol=1e-6)

def test_crossfade_boundary(sine_wave):
    """Crossfade should fail gracefully if fade_length is too long."""
    audio, sr = sine_wave
    with pytest.raises(ValueError):
        dsp_utils.crossfade(audio, audio, fade_length=len(audio))

def test_rms_nonzero(sine_wave):
    """RMS of sine wave should be > 0."""
    audio, sr = sine_wave
    rms = dsp_utils.rms_energy(audio)
    assert rms > 0

def test_rms_silence(silent_audio):
    """RMS of silence should be 0."""
    audio, sr = silent_audio
    rms = dsp_utils.rms_energy(audio)
    assert rms == 0
```

#### Integration Tests (Priority 2)

```python
# tests/test_integration.py
def test_full_pipeline_short_audio(short_audio):
    """Full pipeline on 100ms audio should complete without error."""
    audio, sr = short_audio
    # Save to temp file
    temp_file = '/tmp/test_audio.wav'
    io_utils.save_audio(temp_file, audio, sr)

    # Run segment mining
    config = yaml.safe_load(DEFAULT_CONFIG_YAML)
    candidates = segment_miner.extract_sustained_segments(
        audio, sr, **config['pad_miner']
    )
    # Should return empty list (audio too short)
    assert candidates == []

def test_config_validation():
    """Config validation should catch errors."""
    bad_config = {
        'hiss': {
            'bandpass_low_hz': 10000,
            'bandpass_high_hz': 5000  # Inverted!
        }
    }
    is_valid, errors = validate_config(bad_config)
    assert not is_valid
    assert any('bandpass' in e for e in errors)
```

---

### 7.2 Regression Testing Strategy

For each new feature, save a "golden" test file and compare output:

```bash
# tests/regression/
├── test_sine_440hz.wav          # Known sine input
├── test_sine_expected_pad.wav   # Expected pad output
└── test_regression.py            # Compare outputs

def test_pad_extraction_consistent():
    """Pad extraction from known input should be deterministic."""
    input_file = 'tests/regression/test_sine_440hz.wav'
    audio, sr = io_utils.load_audio(input_file)

    # Extract pads (deterministic seed)
    np.random.seed(42)
    pads = segment_miner.mine_pads_from_file(input_file, config)

    # Should match golden output (or be very close)
    expected = io_utils.load_audio('tests/regression/test_sine_expected_pad.wav')
    # Use correlation instead of exact match (allows for minor variations)
    correlation = np.corrcoef(pads[0].flatten(), expected[0].flatten())[0, 1]
    assert correlation > 0.99
```

---

## Summary of Recommended Changes

| Priority | Issue | Effort | Impact | File |
|----------|-------|--------|--------|------|
| P1 | Add config validation | Small | High | Create `config_validation.py` |
| P1 | CLI support for `--root`, `--config` | Small | High | Update `make_textures.py` |
| P2 | Centralize config defaults | Medium | Medium | Create `config_defaults.py` |
| P2 | Better error logging | Small | Medium | Update `io_utils.py` |
| P2 | Boundary checks in `crossfade()` | Small | Medium | Update `dsp_utils.py` |
| P3 | Audio analysis caching | Medium | Low* | Update `make_textures.py` |
| P3 | DC removal in RMS/normalize | Small | Low | Update `dsp_utils.py` |
| P3 | Basic unit tests | Medium | Medium | Create `tests/` |

*Low impact for current use case, but important for batch workflows with repeated analysis.

---

## Conclusion

The codebase is **well-engineered and production-ready**. The suggested improvements are incremental refinements that would increase robustness, maintainability, and usability for batch workflows. None are blockers for immediate use.

**Recommended immediate actions**:
1. Add CLI support for `--root` and `--config` (enables batch scripts)
2. Add basic config validation (catches user errors early)
3. Fix boundary checks in `crossfade()` (prevents rare crashes)

**Nice to have** (for scaling beyond 100 tracks):
- Caching for repeated analysis
- Parallel processing support
- Logging framework

