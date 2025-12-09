# Phase 2+ Implementation Plan

**Status**: Phase 1 Critical Fixes Complete (C2, H1, H2, H3, Config Expansion)
**Next**: High-priority robustness improvements and DSP quality enhancements

---

## Phase 2: High-Priority Robustness (Estimated: 4-6 hours)

### H5: Crest Factor Division by Zero Protection

**Priority**: HIGH
**Risk**: Can cause crashes in quality grading and audio analysis
**Locations**:
- `musiclib/audio_analyzer.py` lines ~150-200 (quality scoring)
- `curate_best.py` lines 27-71 (score_sample function)

**Implementation**:
```python
# In audio_analyzer.py and curate_best.py
rms = np.sqrt(np.mean(audio**2))
peak = np.max(np.abs(audio))

# BEFORE (vulnerable):
crest = peak / rms

# AFTER (safe):
crest = peak / rms if rms > 1e-10 else 0.0
# Or raise ValueError for truly silent audio
if rms < 1e-10:
    raise ValueError("Cannot compute crest factor for silent audio")
```

**Testing Strategy**:
- Add test in `tests/test_critical_fixes.py` with silent and near-zero audio
- Verify grading doesn't crash on edge cases

---

### H6: Unvalidated Bit Depth Handling

**Priority**: HIGH
**Risk**: Invalid bit depths can corrupt audio or cause soundfile errors
**Location**: `musiclib/io_utils.py` lines 43-98 (save_audio function)

**Current State**: Config validation rejects invalid bit depths, but io_utils doesn't double-check

**Implementation**:
```python
# In io_utils.py save_audio() function (around line 90)
def save_audio(filepath, audio, sr, bit_depth=None, target_peak_dbfs=None):
    # ... existing path security checks ...

    # Add bit depth validation before soundfile.write
    if bit_depth is not None and bit_depth not in (16, 24):
        print(f"  [!] Invalid bit depth {bit_depth}, defaulting to 24-bit")
        bit_depth = 24

    # Determine subtype
    subtype = {16: "PCM_16", 24: "PCM_24"}.get(bit_depth, "PCM_24")
```

**Testing Strategy**:
- Extend `tests/test_security.py::TestDataValidation`
- Test with bit_depth=32, 8, 0, None

---

### H7: Phase Information Loss in Stereo Conversion

**Priority**: MEDIUM-HIGH
**Risk**: Averaging stereo channels can cancel out phase-coherent signals
**Location**: `musiclib/dsp_utils.py` lines 552-603 (ensure_mono function)

**Analysis**: Current `np.mean()` implementation can cause destructive interference if L/R channels are out of phase. Better approach: sum then normalize.

**Implementation**:
```python
def ensure_mono(audio: np.ndarray, method: str = "average") -> np.ndarray:
    """
    Convert stereo to mono with selectable method.

    Args:
        audio: Input audio (any convention)
        method: "average" (default), "left", "right", or "sum"

    Returns:
        Mono audio (samples,)
    """
    if audio.ndim == 1:
        return audio
    elif audio.ndim == 2:
        if audio.shape[0] == 2:  # librosa: (2, samples)
            if method == "average":
                return np.mean(audio, axis=0)
            elif method == "sum":
                return np.sum(audio, axis=0) / np.sqrt(2)  # Preserve RMS
            elif method == "left":
                return audio[0]
            elif method == "right":
                return audio[1]
        elif audio.shape[1] == 2:  # soundfile: (samples, 2)
            if method == "average":
                return np.mean(audio, axis=1)
            elif method == "sum":
                return np.sum(audio, axis=1) / np.sqrt(2)
            elif method == "left":
                return audio[:, 0]
            elif method == "right":
                return audio[:, 1]
        else:
            raise ValueError(f"Unexpected stereo shape: {audio.shape}")
    else:
        raise ValueError(f"Cannot convert {audio.ndim}D array to mono")
```

**Testing Strategy**:
- Add phase cancellation test with out-of-phase stereo signal
- Verify sum method preserves more energy than average
- Add to `tests/test_critical_fixes.py`

---

### H8: Onset Detection User Feedback

**Priority**: MEDIUM
**Risk**: User doesn't know why pad mining rejects material
**Location**: `musiclib/segment_miner.py` lines ~80-150

**Implementation**:
```python
# In segment_miner.py mine_all_pads() function
# Add verbose flag to config
verbose = config.get("pad_miner", {}).get("verbose", False)

# When rejecting segments:
if onset_rate > max_onset_rate:
    if verbose:
        print(f"    → Rejected segment at {start:.1f}s: "
              f"onset_rate={onset_rate:.1f} > {max_onset_rate:.1f}")
    continue

if spectral_flatness > threshold:
    if verbose:
        print(f"    → Rejected segment at {start:.1f}s: "
              f"flatness={spectral_flatness:.3f} (too noisy)")
    continue
```

**Config Addition**:
```yaml
pad_miner:
  verbose: false  # Set to true for debugging rejection reasons
```

**Testing Strategy**:
- Manual testing with real audio
- Verify verbose output appears in logs

---

## Phase 3: DSP Quality & Performance (Estimated: 8-12 hours)

### DSP-1: Aliasing in Grain Pitch Shifting

**Priority**: HIGH (Quality)
**Risk**: Audible artifacts in pitched grains
**Location**: `musiclib/granular_maker.py` lines ~200-250

**Current Issue**: Using `librosa.effects.pitch_shift()` which may not use proper anti-aliasing

**Implementation**:
```python
# In granular_maker.py process_grain() function
# Replace librosa.effects.pitch_shift with resampy-based approach

import resampy

def pitch_shift_grain(grain: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """
    Pitch shift with anti-aliasing.

    Uses high-quality resampling (kaiser_best) to minimize aliasing.
    """
    if abs(semitones) < 0.01:
        return grain

    # Convert semitones to ratio
    ratio = 2 ** (semitones / 12.0)

    # Resample with anti-aliasing (kaiser_best filter)
    shifted = resampy.resample(grain, sr, int(sr * ratio), filter='kaiser_best')

    # Time-stretch back to original duration using phase vocoder
    # (This separates pitch from duration)
    # ... use librosa.effects.time_stretch or pyrubberband

    return shifted
```

**Dependency**: Add `resampy>=0.4.0` to requirements.txt

**Testing Strategy**:
- Spectral analysis test: verify no frequency content above Nyquist
- Add to `tests/test_dsp_utils.py`
- Compare output with and without anti-aliasing

---

### DSP-2: STFT Caching for Performance

**Priority**: MEDIUM (Performance)
**Benefit**: ~40% speedup in pre-analysis and cloud generation
**Location**: `musiclib/audio_analyzer.py` lines ~50-100

**Implementation**:
```python
# In audio_analyzer.py
import hashlib
from functools import lru_cache

def _audio_hash(audio: np.ndarray) -> str:
    """Generate cache key for audio data."""
    return hashlib.sha256(audio.tobytes()).hexdigest()[:16]

# Add caching decorator
@lru_cache(maxsize=32)
def _compute_stft_cached(audio_hash: str, n_fft: int, hop_length: int):
    """Cached STFT computation."""
    # Note: This requires passing audio separately
    # Real implementation needs more thought
    pass

# Alternative: Cache at higher level in analyze_stability()
def analyze_stability(audio_path: str, config: dict, cache_dir: str = None):
    """
    Analyze audio stability with optional disk caching.

    If cache_dir provided, save/load STFT from disk.
    """
    if cache_dir:
        cache_file = Path(cache_dir) / f"{Path(audio_path).stem}_stft.npy"
        if cache_file.exists():
            stft = np.load(cache_file)
        else:
            # Compute and save
            stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
            np.save(cache_file, stft)
    else:
        stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
```

**Testing Strategy**:
- Benchmark test: time pre-analysis with and without caching
- Verify cache invalidation on audio changes
- Memory profiling to ensure cache doesn't grow unbounded

---

### DSP-3: Equal-Power Crossfades

**Priority**: MEDIUM (Quality)
**Risk**: Linear crossfades cause "dip" in perceived loudness
**Location**: `musiclib/dsp_utils.py` lines ~400-450 (crossfade functions)

**Implementation**:
```python
def equal_power_crossfade(audio1: np.ndarray, audio2: np.ndarray,
                          fade_samples: int) -> np.ndarray:
    """
    Equal-power crossfade to maintain perceived loudness.

    Uses square-root law: fade_out = sqrt(1-t), fade_in = sqrt(t)
    """
    if len(audio1) < fade_samples or len(audio2) < fade_samples:
        raise ValueError("Audio segments too short for crossfade")

    # Generate equal-power fade curves
    t = np.linspace(0, 1, fade_samples)
    fade_out = np.sqrt(1 - t)  # Convex curve
    fade_in = np.sqrt(t)        # Convex curve

    # Apply crossfade
    audio1[-fade_samples:] *= fade_out
    audio2[:fade_samples] *= fade_in

    # Sum overlapping region
    result = audio1.copy()
    result[-fade_samples:] += audio2[:fade_samples]
    result = np.concatenate([result, audio2[fade_samples:]])

    return result
```

**Testing Strategy**:
- RMS energy test: verify constant RMS through crossfade region
- Perceptual test: A/B comparison of linear vs equal-power
- Add to `tests/test_dsp_utils.py`

---

## Phase 4: Testing & Documentation (Estimated: 6-8 hours)

### Golden Audio Fixtures

**Purpose**: Regression testing to detect unintended changes
**Location**: `tests/fixtures/` (new directory)

**Implementation**:
```bash
# Create fixtures directory
mkdir -p tests/fixtures/golden_outputs

# Generate known-good outputs
python make_textures.py --config tests/fixtures/test_config.yaml --all

# Store MD5 checksums
md5sum tests/fixtures/golden_outputs/*.wav > tests/fixtures/checksums.txt
```

**Test Strategy**:
```python
# In tests/test_regression.py
import hashlib

def test_pad_mining_regression(tmp_path):
    """Verify pad mining produces consistent output."""
    # Run pad mining on fixture input
    config = load_fixture_config()
    run_mine_pads(config)

    # Compare output checksums
    output_files = Path(config['paths']['export_dir']).glob("**/*.wav")
    for f in output_files:
        actual_hash = hashlib.md5(f.read_bytes()).hexdigest()
        expected_hash = load_expected_hash(f.name)
        assert actual_hash == expected_hash, f"Regression in {f.name}"
```

---

### Property-Based Testing with Hypothesis

**Purpose**: Test with random inputs to find edge cases
**Dependency**: `hypothesis>=6.0.0`

**Implementation**:
```python
# In tests/test_dsp_properties.py
from hypothesis import given, strategies as st
import hypothesis.extra.numpy as npst

@given(
    audio=npst.arrays(
        dtype=np.float32,
        shape=st.integers(min_value=1000, max_value=100000),
        elements=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)
    ),
    target_peak=st.floats(min_value=-60.0, max_value=-0.1)
)
def test_normalize_audio_properties(audio, target_peak):
    """Property: Normalized audio peak equals target within tolerance."""
    if np.max(np.abs(audio)) < 1e-8:
        return  # Skip silent audio (expected to raise)

    normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=target_peak)

    # Property 1: Output has same length
    assert len(normalized) == len(audio)

    # Property 2: Peak matches target within 0.1 dB
    actual_peak_db = 20 * np.log10(np.max(np.abs(normalized)))
    assert abs(actual_peak_db - target_peak) < 0.1

@given(
    audio=npst.arrays(
        dtype=np.float32,
        shape=(2, st.integers(min_value=1000, max_value=10000)),
        elements=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)
    )
)
def test_ensure_mono_preserves_energy(audio):
    """Property: Mono conversion preserves total energy (within bounds)."""
    mono = dsp_utils.ensure_mono(audio)

    # Energy should be similar (not exact due to averaging)
    stereo_energy = np.sum(audio**2)
    mono_energy = np.sum(mono**2)

    # Mono energy should be ~half of stereo (due to averaging)
    ratio = mono_energy / (stereo_energy / 2)
    assert 0.8 < ratio < 1.2  # Allow 20% tolerance
```

---

### Platform Compatibility Documentation

**Location**: `docs/PLATFORM_SUPPORT.md` (new file)

**Content**:
```markdown
# Platform Support Matrix

## Officially Tested Platforms

| Platform | Python | Status | Notes |
|----------|--------|--------|-------|
| macOS 12+ | 3.9-3.11 | ✅ Supported | Primary development platform |
| Ubuntu 22.04 | 3.9-3.11 | ✅ Supported | CI tested |
| Windows 10+ | 3.9-3.11 | ⚠️ Limited | Path handling differences |

## Known Platform Issues

### Windows
- **Path Separators**: Use `Path` from `pathlib` for cross-platform compatibility
- **Line Endings**: Git should be configured with `core.autocrlf=input`
- **Symlinks**: May require admin privileges (affects tests)

### macOS ARM (M1/M2)
- **librosa**: Use native ARM wheel for best performance
- **soundfile**: May need Homebrew libsndfile: `brew install libsndfile`

### Linux
- **Audio Dependencies**: Install system packages:
  ```bash
  sudo apt-get install libsndfile1 libsndfile1-dev
  ```

## Testing on Your Platform

```bash
# Run full test suite
pytest tests/ -v

# Run security tests (platform-specific)
pytest tests/test_security.py -v

# Check audio file handling
pytest tests/test_integration.py -v
```
```

---

## Summary

**Phase 2 Priorities** (Do First):
1. H5: Crest factor guard (1 hour)
2. H6: Bit depth validation (1 hour)
3. H7: Phase-aware stereo conversion (2 hours)

**Phase 3 Priorities** (Quality Wins):
1. DSP-3: Equal-power crossfades (2 hours) - Easy, big perceptual win
2. DSP-1: Anti-aliasing (4 hours) - Requires resampy integration
3. DSP-2: STFT caching (4 hours) - Performance optimization

**Phase 4** (Polish):
1. Golden fixtures (3 hours)
2. Hypothesis tests (3 hours)
3. Platform docs (2 hours)

**Total Estimated Effort**: 20-26 hours across all phases

---

## Decision Points

Before proceeding, confirm:
1. **Priority**: Should we do Phase 2 (robustness) or Phase 3 (DSP quality) first?
2. **Scope**: All of Phase 2, or just H5-H6?
3. **Testing Depth**: Property-based tests worth the complexity?
4. **Dependencies**: OK to add resampy for anti-aliasing?
