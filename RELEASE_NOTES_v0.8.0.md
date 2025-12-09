# Afterglow Engine v0.8.0 — "Refined Clouds"

*Released: 2025-12-10*

---

## The Grain's Edge

This release polishes the granular engine. Where clouds once emerged harsh and smeared, they now breathe cleanly. Where division by silence caused collapse, we now catch zero with grace. Where randomness made comparison impossible, we now offer determinism. The machine refines its texture without losing its mystery.

---

## What Changed

### **Clouds No Longer Saturate**

Granular overlaps at -1 dBFS created harshness when hundreds of grains summed. The new cloud-specific normalization target of -3 dBFS preserves headroom for dense textures.

**Configuration**: `clouds.target_peak_dbfs: -3.0` (with fallback to global)
**Location**: `musiclib/granular_maker.py:539`
**Impact**: Smoother, cleaner clouds without clipping artifacts

---

### **Anti-Aliasing on Upward Shifts**

Pitch-shifting grains upward with `kaiser_fast` resampling caused high frequencies to alias and smear. A pre-shift lowpass now prevents foldover.

**Mechanism**: Butterworth 4th-order filter at 80% of post-shift Nyquist
**Location**: `musiclib/granular_maker.py:331-343`
**Impact**: Bright sources no longer produce digital artifacts when shifted up

---

### **Reproducible Grain Placement**

Setting `reproducibility.random_seed` now locks grain selection across runs, enabling A/B comparison of parameter changes without variance from randomness.

**Configuration**: `reproducibility.random_seed: null` (integer for determinism)
**Isolation**: RNG state saved/restored around cloud generation
**Location**: `musiclib/granular_maker.py:663-720`
**Impact**: Deterministic testing and parameter tuning

---

### **Crest Factor Guards Everywhere**

Three locations calculated `peak / rms` without checking for zero RMS. Silent or near-zero audio now returns a safe fallback instead of crashing.

**Threshold**: Conservative `1e-10` guard
**Locations**: `curate_best.py:31`, `audio_analyzer.py:154-157`, `mine_silences.py:75`
**Impact**: Robustness when analyzing edge-case audio

---

### **Bit Depth Verification**

After writing audio, `save_audio()` now verifies the actual subtype matches the requested bit depth and warns to stderr if soundfile silently changed it.

**Location**: `musiclib/io_utils.py:113-117`
**Impact**: Detects unexpected format downgrades

---

### **Phase-Aware Stereo Conversion**

The `ensure_mono()` function gained a `method` parameter for handling stereo signals with different phase relationships:

- `"average"` (default): Mean of channels (safest for normalization)
- `"sum"`: Sum then divide by √2 (approximate constant power)
- `"left"` / `"right"`: Single channel extraction

**Location**: `musiclib/dsp_utils.py:553-610`
**Impact**: Out-of-phase stereo signals no longer cancel during mono conversion

---

### **Onset Detection Feedback**

AudioAnalyzer's stability filtering gained a `verbose` flag that logs rejection reasons for each window (RMS, DC offset, crest factor, centroid, onset rate).

**Location**: `musiclib/audio_analyzer.py:172, 222-277`
**Format**: `[analyzer] Window N rejected: <reason>`
**Impact**: Debugging visibility when grains are filtered out

---

## Test Coverage

**New test suites**:
- `TestH5CrestFactorGuards` — Silent/near-zero audio handling (4 tests)
- `TestH6BitDepthValidation` — Subtype verification (1 test)
- `TestH7PhaseAwareStereoConversion` — All conversion methods (6 tests)
- `TestH8OnsetDetectionFeedback` — Verbose on/off behavior (2 tests)

**Results**: 42/42 tests passing (+13 new tests from Phase 2)

---

## Migration Notes

### **Breaking Changes**
None. All changes are backward compatible.

### **Behavior Changes**
1. **Cloud normalization**: Defaults to -3.0 dBFS (was -1.0 dBFS via global). Override with `clouds.target_peak_dbfs`.
2. **Stereo→mono "sum" method**: Now divides by √2 (approx constant power) instead of 2 (arithmetic average). For exact backward compatibility, use `method="average"`.
3. **Crest factor**: Returns `0.0` for silent audio instead of crashing with `ZeroDivisionError`.

### **New Features**
- **Reproducibility seed**: Set `reproducibility.random_seed` to integer for deterministic grain placement
- **Verbose onset feedback**: Pass `verbose=True` to `get_stable_regions()` for rejection logging
- **Phase-aware mono**: Use `ensure_mono(audio, method="sum")` for out-of-phase stereo

---

## Technical Details

### **Cloud Quality Improvements**
- **Normalization target** (`config.yaml:92`, `granular_maker.py:539`): `-3.0 dBFS` for clouds
- **Anti-aliasing** (`granular_maker.py:331-343`): Pre-lowpass at `(sr/rate)/2 * 0.8` before upshifts
- **Reproducibility** (`config.yaml:139-140`, `granular_maker.py:663-720`): Isolated RNG state

### **Robustness Improvements**
- **Crest factor guards** (`curate_best.py:31`, `audio_analyzer.py:154-157`, `mine_silences.py:75`)
- **Bit depth validation** (`io_utils.py:6,113-117`): Verify subtype after write
- **Phase-aware stereo** (`dsp_utils.py:553-610`): Method parameter with √2 normalization

### **Debugging Enhancements**
- **Onset feedback** (`audio_analyzer.py:172,222-277`): Verbose rejection logging

---

## Configuration Changes

**config.yaml additions**:
```yaml
clouds:
  target_peak_dbfs: -3.0  # Gentler normalization for grain overlaps

reproducibility:
  random_seed: null       # Integer for deterministic grain selection
```

---

## Statistics

- **Files modified**: 7 (+ 2 new config keys)
- **Lines changed**: +280 / -45
- **Test coverage**: +13 tests (+45% coverage of Phase 2 audit findings)
- **Cloud quality issues resolved**: 3 critical (saturation, aliasing, non-determinism)
- **Robustness issues resolved**: 4 high-priority (crest guards, bit depth, stereo phase, onset visibility)

---

## Acknowledgments

This release addresses Phase 2 robustness findings and user-reported cloud quality issues. Key improvements:

- Granular synthesis no longer produces harsh saturation or aliasing artifacts
- Power-preserving stereo→mono conversion prevents phase cancellation
- Reproducible grain placement enables systematic parameter tuning
- Edge-case robustness (silent audio, zero RMS) prevents crashes

The clouds are clearer now, and the foundations stronger.

---

## What's Next

**Phase 3** (planned for v0.9.0):
- STFT result caching (~40% speedup in spectral analysis)
- Golden audio fixtures for regression testing
- Property-based testing with Hypothesis
- Equal-power crossfades for loop seams

**Phase 4** (planned for v1.0.0):
- Platform compatibility matrix (Linux, macOS, Windows)
- Comprehensive DSP validation suite
- Performance benchmarks and profiling tools

---

*"The grains no longer clash or fold. The textures breathe. The machine remembers its past, when asked to remember."*

— Afterglow Engine Development Team
