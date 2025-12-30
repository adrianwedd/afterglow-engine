# Remediation Plan: afterglow-engine v0.9 → v1.0

**Based On**: REVIEW.md (2025-12-30)
**Target Release**: v1.0.0
**Approach**: Phased remediation with backward compatibility

---

## Overview

This document provides a structured approach to address all issues identified in the comprehensive repository review. Issues are organized into **4 phases** based on severity, effort, and dependencies.

**Guiding Principles**:
1. **Fix critical bugs first** (data integrity, crashes)
2. **Maintain backward compatibility** where possible
3. **Test-driven remediation** (write tests before fixing)
4. **Document all breaking changes**
5. **Incremental releases** (v0.9.1 → v0.9.2 → v1.0.0)

---

## Phase 0: Immediate Hotfixes (v0.9.1)

**Timeline**: 1-2 days
**Scope**: Critical bugs that could cause crashes or data loss

### Issue 1: None-Handling Bug in hiss_maker.py 🔴 CRITICAL
**File**: `musiclib/hiss_maker.py`
**Lines**: 236, 249
**Risk**: Crash when processing silent/low-energy drum sources

**Current Code**:
```python
# Line 229-236
hiss_loop = make_hiss_loop(audio, sr=sr, ...)
filename = f"hiss_loop_{stem}_{i + 1:02d}.wav"
outputs.append((hiss_loop, filename))  # ⚠️ hiss_loop can be None
```

**Remediation**:
```python
# Line 229-237 (updated)
hiss_loop = make_hiss_loop(audio, sr=sr, ...)
if hiss_loop is not None:
    filename = f"hiss_loop_{stem}_{i + 1:02d}.wav"
    outputs.append((hiss_loop, filename))
else:
    logger.debug(f"Skipping hiss loop {i+1}: source too quiet")
```

**Testing**:
```python
# Add to tests/test_robustness.py
def test_hiss_generation_handles_silent_audio():
    """Ensure hiss generation doesn't crash on silent sources."""
    silent_audio = np.zeros(44100)
    config = load_default_config()

    # Should not raise, should return empty list
    outputs = generate_hiss(silent_audio, 44100, config, "silent_source")
    assert isinstance(outputs, list)
    # May be empty or contain synthetic noise fallbacks
```

**Verification**:
- [ ] Test passes with silent audio input
- [ ] Test passes with near-silent audio (RMS < -60dB)
- [ ] Manual verification with `--verbose` logging shows skip messages

**Effort**: 30 minutes (code + test)

---

### Issue 2: Version Number Synchronization 🔴 CRITICAL
**File**: `musiclib/__init__.py`
**Line**: 13
**Risk**: Confusion for users, packaging failures

**Current Code**:
```python
__version__ = "0.1.0"
```

**Remediation**:
```python
__version__ = "0.9.0"
```

**Add Version Check to CI**:
Create `.github/workflows/version-check.yml`:
```yaml
name: Version Consistency Check

on: [push, pull_request]

jobs:
  check-version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Extract versions
        run: |
          MODULE_VERSION=$(grep '__version__' musiclib/__init__.py | cut -d'"' -f2)
          if git describe --tags 2>/dev/null; then
            GIT_VERSION=$(git describe --tags --abbrev=0 | sed 's/^v//')
            if [ "$MODULE_VERSION" != "$GIT_VERSION" ]; then
              echo "❌ Version mismatch: __init__.py=$MODULE_VERSION, git tag=$GIT_VERSION"
              exit 1
            fi
          fi
          echo "✅ Version check passed: $MODULE_VERSION"
```

**Alternative: Single-Source Versioning**
For future releases, consider automated version management:
```python
# musiclib/__init__.py
import importlib.metadata
try:
    __version__ = importlib.metadata.version("afterglow-engine")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"
```

**Verification**:
- [ ] `python -c "import musiclib; print(musiclib.__version__)"` outputs `0.9.0`
- [ ] Version check CI job passes
- [ ] Update CHANGELOG.md to note version sync

**Effort**: 20 minutes (manual) or 2 hours (automated single-source)

---

### Issue 3: Archive Legacy Code 🟡 MEDIUM
**File**: `musiclib/granular_maker_orig.py`
**Risk**: Confusion for new developers, maintenance burden

**Remediation Steps**:
1. Create archive directory structure:
   ```bash
   mkdir -p archive/legacy/v0.1
   ```

2. Move file with git history preservation:
   ```bash
   git mv musiclib/granular_maker_orig.py archive/legacy/v0.1/granular_maker.py
   ```

3. Add README to archive:
   ```bash
   cat > archive/legacy/v0.1/README.md <<EOF
   # Legacy Code Archive (v0.1)

   This directory contains the original granular synthesis implementation
   from afterglow-engine v0.1 (circa 2025-12-06).

   ## Files

   - \`granular_maker.py\` - Original grain extraction and cloud generation
     - Replaced by: \`musiclib/granular_maker.py\` (v0.2+ architecture)
     - Key differences: No quality filtering, simpler grain selection

   ## Why Archived

   Per CLAUDE.md safety protocol: "The machine does not destroy. It archives."

   Preserved for:
   - Reference during debugging
   - Historical context for design decisions
   - Potential future A/B comparisons

   ## Do Not Use

   This code is **not maintained** and should not be imported in production.
   EOF
   ```

4. Update CHANGELOG.md:
   ```markdown
   ### Changed
   - Archived legacy granular_maker_orig.py to archive/legacy/v0.1/
   ```

**Verification**:
- [ ] File moved with git history intact (`git log archive/legacy/v0.1/granular_maker.py`)
- [ ] No imports of `granular_maker_orig` in codebase (`grep -r "granular_maker_orig"`)
- [ ] Archive README clearly explains preservation

**Effort**: 30 minutes

---

### Issue 4: Update PyYAML Dependency 🟡 MEDIUM
**File**: `requirements.txt`
**Risk**: Potential security vulnerabilities in 6.0.1

**Current**:
```
PyYAML==6.0.1
```

**Remediation**:
```
PyYAML==6.0.2
```

**Testing Plan**:
1. Update locally: `pip install PyYAML==6.0.2`
2. Run full test suite: `pytest tests/ -v`
3. Test config loading: `python validate_config.py`
4. Verify no deprecation warnings

**Verification**:
- [ ] All tests pass with PyYAML 6.0.2
- [ ] Config validation works correctly
- [ ] No new warnings in CI logs

**Effort**: 15 minutes + CI verification

---

## Phase 1: Quick Wins (v0.9.2)

**Timeline**: 1 week
**Scope**: Low-hanging fruit that improves usability without breaking changes

### Issue 5: Document Environment Variables
**File**: `README.md`
**Impact**: Users unaware of configuration options

**Remediation**:
Add new section after "Configuration" section (~line 375):

```markdown
## Environment Variables

afterglow-engine respects the following environment variables for advanced configuration:

### Logging

**`AFTERGLOW_LOG_LEVEL`** - Control logging verbosity

- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default**: `INFO`
- **Usage**:
  ```bash
  export AFTERGLOW_LOG_LEVEL=DEBUG
  python make_textures.py --all
  ```
- **Equivalent**: `--verbose` flag sets this to `DEBUG`

### Path Configuration

**`AFTERGLOW_EXPORT_ROOT`** - Override export path validation root (advanced users only)

- **Default**: Project directory
- **Usage**: Set to allow exports outside default directory
- **⚠️ Security**: Only use if you understand path traversal risks

**`AFTERGLOW_UNSAFE_IO`** - Bypass path safety checks (testing only)

- **Values**: `0` (disabled), `1` (enabled)
- **Default**: `0`
- **Usage**: Required for running test suite
- **⚠️ WARNING**: NEVER enable in production. This disables critical security checks.
  ```bash
  AFTERGLOW_UNSAFE_IO=1 pytest tests/  # Testing only
  ```

See [SECURITY.md](SECURITY.md) for details on path validation.
```

**Also Update**:
- `docs/TUTORIAL.md` - Add environment variable section
- `SECURITY.md` - Cross-reference environment variables

**Verification**:
- [ ] README includes environment variables section
- [ ] Tutorial mentions logging configuration
- [ ] SECURITY.md cross-references path safety environment variables

**Effort**: 1 hour

---

### Issue 6: Remove Unused Imports
**Files**: Multiple

**Remediation**:

**File 1: `mine_drums.py:20`**
```python
# REMOVE:
from musiclib import audio_analyzer  # ❌ Unused

# Verify with:
grep -n "audio_analyzer" mine_drums.py
# Should only show the import line
```

**File 2: `musiclib/dsp_utils.py:7-8`**
```python
# CURRENT:
import math
# ... later at line 191:
return math.inf

# REPLACE WITH:
return float('inf')

# Then remove:
import math
```

**Automated Detection**:
Add to CI (optional):
```yaml
# .github/workflows/ci.yml - add to code-quality job
- name: Check for unused imports
  run: |
    pip install autoflake
    autoflake --check --remove-all-unused-imports -r musiclib/
```

**Verification**:
- [ ] Run `autoflake --check --remove-all-unused-imports musiclib/` (exit 0)
- [ ] All tests still pass
- [ ] No import errors

**Effort**: 30 minutes

---

### Issue 7: Add Deprecation Warnings for Legacy Config Keys
**Files**: `musiclib/segment_miner.py`, `musiclib/hiss_maker.py`

**Remediation**:

**Add Helper Function in `musiclib/compat.py`**:
```python
import warnings
from typing import Any, Dict, Optional

def get_config_with_deprecation(
    config: dict,
    new_key: str,
    old_key: str,
    default: Any,
    deprecated_in: str = "v0.9",
    removed_in: str = "v1.0"
) -> Any:
    """
    Get config value with deprecation warning for legacy keys.

    Args:
        config: Configuration dictionary
        new_key: New/current config key name
        old_key: Deprecated/legacy config key name
        default: Default value if neither key present
        deprecated_in: Version where old key was deprecated
        removed_in: Version where old key will be removed

    Returns:
        Config value (preferring new_key over old_key)
    """
    if new_key in config:
        return config[new_key]
    elif old_key in config:
        warnings.warn(
            f"Config key '{old_key}' is deprecated since {deprecated_in} "
            f"and will be removed in {removed_in}. "
            f"Use '{new_key}' instead.",
            DeprecationWarning,
            stacklevel=3
        )
        return config[old_key]
    else:
        return default
```

**Update `segment_miner.py:236`**:
```python
# CURRENT:
crossfade_ms = pad_miner_config.get(
    'loop_crossfade_ms',
    pad_miner_config.get('crossfade_ms', 50)
)

# REPLACE WITH:
from musiclib.compat import get_config_with_deprecation

crossfade_ms = get_config_with_deprecation(
    pad_miner_config,
    new_key='loop_crossfade_ms',
    old_key='crossfade_ms',
    default=50,
    deprecated_in='v0.8',
    removed_in='v1.0'
)
```

**Update `hiss_maker.py:229, 246`**:
```python
# Similar pattern for bandpass_low_hz/band_low_hz
low_hz = get_config_with_deprecation(
    hiss_config,
    new_key='bandpass_low_hz',
    old_key='band_low_hz',
    default=5000
)

high_hz = get_config_with_deprecation(
    hiss_config,
    new_key='bandpass_high_hz',
    old_key='band_high_hz',
    default=14000
)
```

**Add Migration Guide**:
Create `docs/MIGRATION_V1.0.md`:
```markdown
# Migration Guide: v0.9 → v1.0

## Configuration Key Changes

### Deprecated Keys (Removed in v1.0)

| Old Key (v0.7) | New Key (v0.8+) | Location |
|----------------|-----------------|----------|
| `crossfade_ms` | `loop_crossfade_ms` | `pad_miner.*` |
| `band_low_hz` | `bandpass_low_hz` | `hiss.*` |
| `band_high_hz` | `bandpass_high_hz` | `hiss.*` |

### Action Required

Update your `config.yaml`:

```yaml
# OLD (v0.7):
pad_miner:
  crossfade_ms: 50

hiss:
  band_low_hz: 5000
  band_high_hz: 14000

# NEW (v0.8+):
pad_miner:
  loop_crossfade_ms: 50

hiss:
  bandpass_low_hz: 5000
  bandpass_high_hz: 14000
```

Running with old keys in v0.9 will show warnings but continue working.
In v1.0, old keys will be removed and configs will fail validation.
```

**Testing**:
```python
# Add to tests/test_compat.py
import warnings

def test_deprecated_config_key_warning():
    """Verify deprecation warnings for legacy config keys."""
    config = {'crossfade_ms': 100}  # Old key

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        value = get_config_with_deprecation(
            config, 'loop_crossfade_ms', 'crossfade_ms', 50
        )

        assert value == 100  # Got value from old key
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert 'crossfade_ms' in str(w[0].message)
        assert 'loop_crossfade_ms' in str(w[0].message)
```

**Verification**:
- [ ] Test with old config shows deprecation warnings
- [ ] Test with new config shows no warnings
- [ ] Test with missing keys uses defaults
- [ ] Migration guide clearly documents changes

**Effort**: 3 hours

---

## Phase 2: Structural Improvements (v0.10)

**Timeline**: 2-3 weeks
**Scope**: Refactoring complex functions, standardizing patterns

### Issue 8: Refactor Complex Functions

#### 8a. Refactor `extract_grains()` (granular_maker.py:115-283)

**Current Complexity**: 168 lines, cyclomatic complexity ~15+

**Approach**: Split into 4 focused functions

**New Structure**:
```python
def extract_grains(
    audio: np.ndarray,
    grain_length_samples: int,
    num_grains: int,
    sr: int,
    config: dict = None,
    # ... other params
) -> List[np.ndarray]:
    """
    Extract grains from audio with quality filtering.

    Orchestrates grain extraction pipeline:
    1. Analyze stability (if pre-analysis enabled)
    2. Sample grain positions (stable regions or random)
    3. Extract and window grains
    4. Apply quality filters

    Returns:
        List of grain arrays that passed quality checks
    """
    grains = []

    # 1. Setup stability analysis
    stable_mask, analyzer = _setup_grain_stability_analysis(
        audio, sr, config
    )

    # 2. Extract grains
    for i in range(num_grains):
        # 2a. Sample position
        start_pos = _sample_grain_position(
            audio, grain_length_samples, stable_mask, analyzer
        )

        # 2b. Extract and window
        grain = _extract_single_grain(
            audio, start_pos, grain_length_samples
        )

        # 2c. Apply quality filters
        if _grain_passes_quality_checks(grain, sr, config):
            grains.append(grain)

    return grains


def _setup_grain_stability_analysis(
    audio: np.ndarray,
    sr: int,
    config: dict
) -> Tuple[Optional[np.ndarray], Optional[AudioAnalyzer]]:
    """
    Setup pre-analysis for stable region detection.

    Returns:
        (stable_mask, analyzer) if pre-analysis enabled,
        (None, None) otherwise
    """
    if not config or not config.get('pre_analysis', {}).get('enabled', False):
        return None, None

    # ... existing pre-analysis setup code ...


def _sample_grain_position(
    audio: np.ndarray,
    grain_length: int,
    stable_mask: Optional[np.ndarray],
    analyzer: Optional[AudioAnalyzer]
) -> int:
    """
    Sample a grain start position.

    Uses stable regions if available, otherwise random sampling.
    Includes fallback to least-onset regions if no stable windows found.

    Returns:
        Start sample index for grain extraction
    """
    if stable_mask is not None and np.any(stable_mask):
        # ... existing stable region sampling code ...
        pass
    else:
        # Random sampling
        max_start = max(0, len(audio) - grain_length)
        return np.random.randint(0, max_start) if max_start > 0 else 0


def _extract_single_grain(
    audio: np.ndarray,
    start_pos: int,
    grain_length: int
) -> np.ndarray:
    """
    Extract and window a single grain.

    Handles edge cases:
    - Grain extends beyond audio end (padding)
    - Zero-length audio (returns zeros)

    Returns:
        Windowed grain audio
    """
    end_pos = min(start_pos + grain_length, len(audio))
    grain = audio[start_pos:end_pos]

    # Pad if necessary
    if len(grain) < grain_length:
        grain = np.pad(grain, (0, grain_length - len(grain)))

    # Apply window
    window = dsp_utils.hann_window(grain_length)
    return grain * window


def _grain_passes_quality_checks(
    grain: np.ndarray,
    sr: int,
    config: dict
) -> bool:
    """
    Apply quality filters to grain.

    Checks (configurable):
    - Minimum RMS level
    - Maximum DC offset
    - Maximum crest factor
    - Spectral centroid range
    - Clipping detection

    Returns:
        True if grain passes all enabled checks
    """
    if config is None:
        return True

    quality_config = config.get('clouds', {})

    # RMS check
    min_rms_db = quality_config.get('grain_min_rms_db', -60)
    # ... existing quality check logic ...

    return True  # Passed all checks
```

**Testing Strategy**:
1. Extract existing `extract_grains()` tests
2. Add unit tests for each new helper function
3. Integration test ensuring behavior unchanged
4. Property-based test for stability

```python
# tests/test_granular_refactor.py
def test_extract_grains_backward_compatibility():
    """Ensure refactored version produces same results."""
    audio = create_test_audio()
    config = load_test_config()

    # Set random seed for reproducibility
    np.random.seed(42)
    grains_old = extract_grains_original(audio, ...)

    np.random.seed(42)
    grains_new = extract_grains(audio, ...)

    assert len(grains_old) == len(grains_new)
    for g_old, g_new in zip(grains_old, grains_new):
        np.testing.assert_array_almost_equal(g_old, g_new)
```

**Effort**: 8 hours (refactor + comprehensive testing)

---

#### 8b. Refactor `get_stable_regions()` (audio_analyzer.py:225-339)

**Approach**: Extract per-metric filter functions

**New Structure**:
```python
class AudioAnalyzer:
    def get_stable_regions(self, ...params...) -> np.ndarray:
        """
        Identify stable (non-transient) windows in audio.

        Returns boolean mask where True = stable window.
        """
        # Initialize mask (all True initially)
        stable_mask = np.ones(num_windows, dtype=bool)

        # Compute all metrics once
        metrics = self._compute_stability_metrics(...)

        # Apply filters
        stable_mask &= self._filter_by_rms(metrics['rms'], min_rms_db, max_rms_db)
        stable_mask &= self._filter_by_dc_offset(metrics['dc'], max_dc_offset)
        stable_mask &= self._filter_by_crest_factor(metrics['crest'], max_crest)

        if centroid_low_hz is not None or centroid_high_hz is not None:
            stable_mask &= self._filter_by_spectral_centroid(
                metrics['centroid'], centroid_low_hz, centroid_high_hz
            )

        if max_onset_rate is not None:
            stable_mask &= self._filter_by_onset_rate(
                metrics['onsets'], max_onset_rate
            )

        return stable_mask

    def _compute_stability_metrics(self, ...) -> Dict[str, np.ndarray]:
        """Compute all stability metrics in one pass."""
        # ... existing metric computation ...
        return {
            'rms': rms,
            'dc': dc_offset,
            'crest': crest_factor,
            'centroid': centroid,
            'onsets': onset_times
        }

    def _filter_by_rms(
        self,
        rms: np.ndarray,
        min_db: float,
        max_db: float,
        verbose: bool = False
    ) -> np.ndarray:
        """
        Filter by RMS energy range.

        Returns boolean mask where True = passes RMS check.
        """
        mask = (rms >= min_db) & (rms <= max_db)
        if verbose:
            rejected = np.where(~mask)[0]
            for idx in rejected:
                logger.debug(
                    f"  [analyzer] Window {idx} rejected: "
                    f"RMS {rms[idx]:.1f} dB outside [{min_db}, {max_db}]"
                )
        return mask

    # Similar for _filter_by_dc_offset, _filter_by_crest_factor, etc.
```

**Effort**: 6 hours

---

### Issue 9: Standardize Return Value Patterns

**Problem**: Inconsistent tuple returns for brightness tagging

**Current State**:
- `granular_maker.py`: Returns `(audio, brightness_tag, filename)` (3-tuple)
- `segment_miner.py`: Returns `(audio, brightness_tag)` (2-tuple)
- `drone_maker.py`: Mixed patterns

**Approach**: Use dataclasses for type safety

**Remediation**:

**Create `musiclib/artifacts.py`**:
```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class AudioArtifact:
    """
    Represents a generated audio artifact with metadata.

    Attributes:
        audio: Audio data (samples,) or (channels, samples)
        filename: Suggested filename (without extension)
        brightness_tag: Classification (dark/mid/bright)
        artifact_type: Type identifier (pad/swell/cloud/hiss)
        source_name: Original source file stem
        metadata: Optional additional metadata
    """
    audio: np.ndarray
    filename: str
    brightness_tag: str
    artifact_type: str
    source_name: str
    metadata: Optional[dict] = None

    def save(self, output_dir: str, sr: int, config: dict):
        """Save artifact with automatic metadata generation."""
        from musiclib.io_utils import save_with_metadata

        filepath = Path(output_dir) / f"{self.filename}.wav"
        save_with_metadata(
            self.audio,
            filepath,
            sr,
            self.artifact_type,
            self.source_name,
            config,
            additional_metadata=self.metadata
        )
```

**Update Generators**:
```python
# granular_maker.py (updated)
def make_cloud(...) -> AudioArtifact:
    cloud_audio = ...
    brightness_tag = ...

    return AudioArtifact(
        audio=cloud_audio,
        filename=f"cloud_{source_stem}_{idx:02d}",
        brightness_tag=brightness_tag,
        artifact_type="cloud",
        source_name=source_stem,
        metadata={'grain_count': len(grains)}
    )

# segment_miner.py (updated)
def extract_sustained_segments(...) -> List[AudioArtifact]:
    artifacts = []
    for segment in segments:
        pad_audio = ...
        brightness = ...

        artifacts.append(AudioArtifact(
            audio=pad_audio,
            filename=f"{source_stem}_pad_{idx:02d}",
            brightness_tag=brightness,
            artifact_type="pad",
            source_name=source_stem
        ))
    return artifacts
```

**Migration Path**:
1. v0.10: Introduce `AudioArtifact`, keep old tuple returns for backward compat
2. v0.11: Deprecation warnings when tuple unpacking detected
3. v1.0: Remove tuple returns entirely

**Effort**: 10 hours (create dataclass, update all generators, update tests)

---

### Issue 10: Create Missing Test Coverage

#### 10a. Create `tests/test_compat.py`

**Coverage Target**: `musiclib/compat.py` (163 lines, 0% covered)

**Test Plan**:
```python
# tests/test_compat.py
import logging
from musiclib.compat import (
    get_config_with_deprecation,
    migrate_legacy_prefix,
    detect_log_level
)

class TestConfigMigration:
    def test_new_key_preferred_over_old(self):
        config = {'new_key': 100, 'old_key': 50}
        value = get_config_with_deprecation(config, 'new_key', 'old_key', 10)
        assert value == 100

    def test_old_key_fallback_with_warning(self):
        # ... (from Phase 1, Issue 7)

    def test_default_when_no_keys_present(self):
        config = {}
        value = get_config_with_deprecation(config, 'new_key', 'old_key', 42)
        assert value == 42

class TestLogMigration:
    def test_migrate_prefix_info(self):
        assert migrate_legacy_prefix("[INFO] message") == "[✓] message"

    def test_detect_log_level_from_prefix(self):
        assert detect_log_level("[✓] message") == "INFO"
        assert detect_log_level("[·] message") == "DEBUG"

# ... 15+ more tests for full compat.py coverage
```

**Effort**: 4 hours

---

#### 10b. Create `tests/test_validate_config.py`

**Coverage Target**: `validate_config.py` (252 lines, 0% covered)

**Test Plan**:
```python
# tests/test_validate_config.py
import pytest
from validate_config import (
    validate_config_schema,
    check_boolean_fields,
    check_range_constraints,
    ValidationError
)

class TestConfigValidation:
    def test_valid_config_passes(self):
        config = load_valid_config()
        errors = validate_config_schema(config)
        assert len(errors) == 0

    def test_missing_required_section_fails(self):
        config = {'global': {}}  # Missing paths, pad_miner, etc.
        errors = validate_config_schema(config)
        assert any('paths' in err for err in errors)

    def test_invalid_boolean_fields(self):
        config = load_valid_config()
        config['export']['pads_stereo'] = 'yes'  # Should be bool

        errors = check_boolean_fields(config)
        assert len(errors) > 0
        assert 'pads_stereo' in errors[0]

    def test_brightness_centroid_range_validation(self):
        config = load_valid_config()
        config['brightness_tags']['centroid_low_hz'] = 5000
        config['brightness_tags']['centroid_high_hz'] = 3000  # Invalid: low > high

        errors = check_range_constraints(config)
        assert any('centroid' in err for err in errors)

    def test_tremolo_depth_range(self):
        config = load_valid_config()
        config['hiss']['tremolo_depth'] = 1.5  # Invalid: > 1.0

        errors = check_range_constraints(config)
        assert any('tremolo_depth' in err and '0.0-1.0' in err for err in errors)

# ... 20+ more tests for comprehensive validation coverage
```

**Add to `validate_config.py`**:
```python
def check_boolean_fields(config: dict) -> List[str]:
    """Validate boolean-typed config fields."""
    errors = []
    boolean_fields = [
        ('export', 'pads_stereo'),
        ('export', 'swells_stereo'),
        ('export', 'clouds_stereo'),
        ('export', 'hiss_stereo'),
        ('curation', 'auto_delete_grade_f'),
        ('pre_analysis', 'enabled'),
    ]

    for section, field in boolean_fields:
        if section in config and field in config[section]:
            value = config[section][field]
            if not isinstance(value, bool):
                errors.append(
                    f"{section}.{field} must be boolean (true/false), "
                    f"got {type(value).__name__}: {value}"
                )

    return errors

def check_range_constraints(config: dict) -> List[str]:
    """Validate range constraints (min < max, 0-1 bounds, etc.)."""
    errors = []

    # Brightness centroid range
    if 'brightness_tags' in config:
        low = config['brightness_tags'].get('centroid_low_hz')
        high = config['brightness_tags'].get('centroid_high_hz')
        if low is not None and high is not None and low >= high:
            errors.append(
                f"brightness_tags.centroid_low_hz ({low}) must be < "
                f"centroid_high_hz ({high})"
            )

    # Tremolo depth 0-1
    if 'hiss' in config:
        depth = config['hiss'].get('tremolo_depth')
        if depth is not None and not (0.0 <= depth <= 1.0):
            errors.append(
                f"hiss.tremolo_depth must be in range [0.0, 1.0], got {depth}"
            )

    # ... more constraint checks ...

    return errors
```

**Effort**: 6 hours

---

## Phase 3: Technical Debt Reduction (v0.11)

**Timeline**: 2-3 weeks
**Scope**: Extract duplicated code, expose hardcoded parameters

### Issue 11: Extract Duplicated Metadata+Grading Pattern

**Problem**: 40+ lines of identical code in 4 modules

**Current Duplication**:
- `granular_maker.py:785-812`
- `segment_miner.py:367-391`
- `drone_maker.py:444-473`
- `hiss_maker.py:390-416`

**Remediation**:

**Create `musiclib/io_utils.py::save_with_metadata()`**:
```python
def save_with_metadata(
    audio: np.ndarray,
    filepath: str,
    sr: int,
    artifact_type: str,
    source_name: str,
    config: dict,
    additional_metadata: dict = None
) -> Optional[dict]:
    """
    Save audio with automatic metadata computation, grading, and manifest integration.

    Pipeline:
    1. Compute standard metrics (RMS, peak, crest, centroid, brightness)
    2. Grade artifact based on curation thresholds
    3. Auto-delete if grade F and auto_delete enabled
    4. Save audio file
    5. Return manifest row dict

    Args:
        audio: Audio data to save
        filepath: Full path including .wav extension
        sr: Sample rate
        artifact_type: Type identifier (pad/swell/cloud/hiss)
        source_name: Original source file stem
        config: Full configuration dict
        additional_metadata: Optional extra fields for manifest

    Returns:
        Manifest row dict if saved, None if auto-deleted
    """
    from musiclib.audio_analyzer import compute_audio_metrics
    from musiclib.io_utils import grade_artifact, save_audio

    # 1. Compute metrics
    metrics = compute_audio_metrics(audio, sr)

    # 2. Grade
    grade = grade_artifact(metrics, config.get('curation', {}))

    # 3. Check auto-delete
    if grade == 'F' and config.get('curation', {}).get('auto_delete_grade_f', False):
        logger.info(f"Skipping Grade F artifact: {Path(filepath).name}")
        return None

    # 4. Save
    save_audio(
        audio,
        filepath,
        sr,
        bit_depth=config.get('global', {}).get('bit_depth', 24)
    )

    # 5. Build manifest row
    manifest_row = {
        'filename': Path(filepath).name,
        'source': source_name,
        'type': artifact_type,
        'duration': len(audio) / sr,
        'grade': grade,
        **metrics,  # RMS, peak, crest, centroid, brightness, etc.
    }

    if additional_metadata:
        manifest_row.update(additional_metadata)

    return manifest_row

def compute_audio_metrics(audio: np.ndarray, sr: int) -> dict:
    """
    Compute standard audio metrics for grading and manifest.

    Returns dict with keys:
        rms_db, peak_db, crest_factor, spectral_centroid_hz, brightness_tag
    """
    # Existing metric computation logic extracted here
    pass

def grade_artifact(metrics: dict, curation_config: dict) -> str:
    """
    Grade artifact A-F based on metrics and thresholds.

    Grading criteria:
    - F: Silence, clipping, extreme crest
    - D: Near-silence, near-clipping, high crest
    - C: Usable but low quality
    - B: Good quality
    - A: Excellent quality

    Returns:
        Grade letter: 'A', 'B', 'C', 'D', or 'F'
    """
    # Existing grading logic extracted here
    pass
```

**Update All Generators**:
```python
# granular_maker.py (updated)
def make_cloud(...) -> Optional[dict]:
    cloud_audio = ...
    filename = ...

    manifest_row = save_with_metadata(
        cloud_audio,
        filepath=output_dir / filename,
        sr=sr,
        artifact_type='cloud',
        source_name=source_stem,
        config=config,
        additional_metadata={'grain_count': len(grains)}
    )

    return manifest_row  # None if auto-deleted

# Similar updates for segment_miner, drone_maker, hiss_maker
```

**Testing**:
```python
def test_save_with_metadata_creates_file_and_manifest():
    audio = create_test_audio()
    config = load_test_config()

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_artifact.wav"

        manifest_row = save_with_metadata(
            audio, filepath, 44100, 'test', 'source', config
        )

        assert filepath.exists()
        assert manifest_row is not None
        assert manifest_row['filename'] == 'test_artifact.wav'
        assert 'grade' in manifest_row
        assert 'rms_db' in manifest_row

def test_save_with_metadata_auto_delete_grade_f():
    silent_audio = np.zeros(44100)
    config = load_test_config()
    config['curation']['auto_delete_grade_f'] = True

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "silent.wav"

        manifest_row = save_with_metadata(
            silent_audio, filepath, 44100, 'test', 'source', config
        )

        assert manifest_row is None  # Auto-deleted
        assert not filepath.exists()  # File not created
```

**Effort**: 12 hours (extract, refactor all generators, comprehensive testing)

---

### Issue 12: Expose Hardcoded DSP Parameters

**Problem**: Critical parameters not configurable without code edits

**Remediation**:

**Update `config.yaml` Schema**:
```yaml
# Add new section after `clouds:`
clouds:
  # ... existing settings ...

  # Advanced grain extraction parameters
  min_grain_length_samples: 256      # Minimum grain size (safety limit)
  max_pitch_shift_rate: 2.0          # Maximum pitch shift factor
  edge_fade_ms: 10                   # Fade at cloud start/end

  # Grain quality thresholds (existing)
  grain_min_rms_db: -60.0
  # ...

hiss:
  # ... existing settings ...

  # Loop generation
  loop_crossfade_ms: 50              # Crossfade duration for seamless loops

  # Flicker burst envelopes
  flicker_fade_in_ms: 10             # Attack time
  flicker_fade_out_ms: 50            # Release time

  # Synthetic noise generation
  synthetic_noise_buffer_sec: 30.0   # Pre-generated noise duration

global:
  # ... existing settings ...

  # DSP safety thresholds
  silence_threshold_linear: 1.0e-8   # Minimum energy for normalization
```

**Update Code to Use Config**:
```python
# granular_maker.py (updated)
def extract_grains(...):
    clouds_config = config.get('clouds', {})

    # Line 291-292 (updated)
    min_grain_length = clouds_config.get('min_grain_length_samples', 256)
    max_pitch_rate = clouds_config.get('max_pitch_shift_rate', 2.0)

    # Line 498 (updated)
    fade_ms = clouds_config.get('edge_fade_ms', 10)
    fade_samples = int(fade_ms / 1000.0 * sr)

# hiss_maker.py (updated)
def make_hiss_loop(...):
    hiss_config = config.get('hiss', {})

    # Line 97 (updated)
    crossfade_ms = hiss_config.get('loop_crossfade_ms', 50)

def make_flicker_burst(...):
    hiss_config = config.get('hiss', {})

    # Lines 164-165 (updated)
    fade_in_ms = hiss_config.get('flicker_fade_in_ms', 10)
    fade_out_ms = hiss_config.get('flicker_fade_out_ms', 50)

    fade_in_samples = int(fade_in_ms / 1000.0 * sr)
    fade_out_samples = int(fade_out_ms / 1000.0 * sr)

# dsp_utils.py (updated)
def normalize_audio(audio, target_peak_dbfs=-1.0, config=None):
    global_config = config.get('global', {}) if config else {}

    # Line 103 (updated)
    silence_threshold = global_config.get('silence_threshold_linear', 1e-8)

    peak = np.abs(audio).max()
    if peak < silence_threshold:
        raise SilentArtifact(...)
```

**Update `validate_config.py`**:
```python
def validate_advanced_dsp_params(config: dict) -> List[str]:
    """Validate advanced DSP parameter ranges."""
    errors = []

    # Clouds
    if 'clouds' in config:
        min_grain = config['clouds'].get('min_grain_length_samples')
        if min_grain is not None and min_grain < 64:
            errors.append(
                f"clouds.min_grain_length_samples must be >= 64, got {min_grain}"
            )

        max_rate = config['clouds'].get('max_pitch_shift_rate')
        if max_rate is not None and (max_rate < 0.5 or max_rate > 4.0):
            errors.append(
                f"clouds.max_pitch_shift_rate should be in [0.5, 4.0], got {max_rate}"
            )

    # Hiss
    if 'hiss' in config:
        fade_in = config['hiss'].get('flicker_fade_in_ms')
        fade_out = config['hiss'].get('flicker_fade_out_ms')
        if fade_in is not None and fade_in < 0:
            errors.append("hiss.flicker_fade_in_ms cannot be negative")
        if fade_out is not None and fade_out < 0:
            errors.append("hiss.flicker_fade_out_ms cannot be negative")

    return errors
```

**Documentation**:
Update `docs/CONFIG_QUICK_REFERENCE.md` with new parameters and warnings about changing defaults.

**Effort**: 8 hours

---

## Phase 4: Future-Proofing (v1.0)

**Timeline**: 1-2 weeks
**Scope**: Dependency updates, packaging, final polish

### Issue 13: Dependency Updates

**Current vs Latest**:
```
librosa==0.10.0      → 0.10.2.post1
numpy==1.24.3        → 1.26.4 (or 2.x with breaking changes)
scipy==1.11.4        → 1.14.1
soundfile==0.12.1    → (already latest)
PyYAML==6.0.1        → 6.0.2 (done in Phase 0)
pytest==9.0.1        → 8.3.4 (typo in requirements.txt?)
hypothesis==6.100.0  → 6.122.3
tqdm==4.66.3         → 4.67.1
```

**Approach**:

**Step 1: Safe Updates (No Breaking Changes)**
```
librosa==0.10.2.post1
scipy==1.14.1
hypothesis==6.122.3
tqdm==4.67.1
```

**Testing**:
1. Update dependencies in isolated venv
2. Run full test suite
3. Profile performance benchmarks
4. Manual validation with diverse audio sources

**Step 2: NumPy Migration Planning**

**Option A: Stay on 1.x until EOL (Sept 2025)**
```
numpy>=1.24.3,<2.0.0  # Pin to 1.x series
```

**Option B: Migrate to 2.x Now (Recommended for v1.0)**

**Breaking Changes in NumPy 2.x**:
- Default dtypes changed for some operations
- Stricter type checking
- Some deprecated functions removed

**Migration Steps**:
1. Install `numpy==2.0.0`
2. Run tests, fix failures
3. Update type hints if needed
4. Benchmark performance (2.x may be faster)

**Testing Matrix**:
```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    numpy-version: ['1.26.4', '2.0.0']
```

**Effort**: 16 hours (safe updates 2h, NumPy 2.x migration 14h)

---

### Issue 14: Packaging for Distribution (Optional)

**Only if PyPI distribution desired**

**Create `pyproject.toml`**:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "afterglow-engine"
version = "1.0.0"
description = "A machine for sonic archaeology - extract textures from audio archives"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Adrian Wedd", email = "adrian@adrianwedd.com"}
]
keywords = ["audio", "dsp", "texture", "granular", "sampler", "tr8s"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Multimedia :: Sound/Audio",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

requires-python = ">=3.11"
dependencies = [
    "librosa>=0.10.2",
    "numpy>=1.26.4,<3.0",
    "scipy>=1.14.1",
    "soundfile>=0.12.1",
    "PyYAML>=6.0.2",
    "tqdm>=4.67.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.4",
    "hypothesis>=6.122.3",
    "pytest-cov>=4.1.0",
    "flake8>=6.0.0",
    "black>=23.0.0",
    "mypy>=1.5.0",
]

[project.scripts]
afterglow = "make_textures:main"
afterglow-validate = "validate_config:main"

[project.urls]
Homepage = "https://github.com/adrianwedd/afterglow-engine"
Documentation = "https://github.com/adrianwedd/afterglow-engine/tree/main/docs"
Repository = "https://github.com/adrianwedd/afterglow-engine"
"Bug Tracker" = "https://github.com/adrianwedd/afterglow-engine/issues"

[tool.setuptools]
packages = ["musiclib"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=musiclib --cov-report=term --cov-report=xml"
```

**Update Scripts for Entry Points**:
```python
# make_textures.py (add at end)
def main():
    """Entry point for CLI."""
    # Existing argparse logic
    ...

if __name__ == "__main__":
    main()
```

**Build and Test**:
```bash
# Build distribution
python -m build

# Test installation
pip install dist/afterglow_engine-1.0.0-py3-none-any.whl

# Verify CLI works
afterglow --help
afterglow-validate config.yaml
```

**Effort**: 6 hours (if pursuing PyPI distribution)

---

## Issue 15: Enforce Code Quality in CI

**Current State**: All quality checks set to `continue-on-error: true`

**Decision Point**: Should these become hard failures for v1.0?

**Recommendation**: **Yes** - Enforce for v1.0 production quality

**Remediation**:

**Update `.github/workflows/ci.yml`**:
```yaml
- name: Lint with flake8
  continue-on-error: false  # Changed from true
  run: |
    # Stop the build if there are Python syntax errors or undefined names
    flake8 musiclib --count --select=E9,F63,F7,F82 --show-source --statistics
    # Treat complexity/style warnings as errors
    flake8 musiclib --count --max-complexity=12 --max-line-length=100 --statistics

- name: Check formatting with black
  continue-on-error: false  # Changed from true
  run: |
    black --check --line-length 100 musiclib make_textures.py validate_config.py

- name: Type check with mypy
  continue-on-error: false  # Changed from true
  run: |
    mypy musiclib --ignore-missing-imports --warn-return-any
```

**Pre-Enforcement Cleanup**:
1. Run `black musiclib/ --line-length 100` to auto-format
2. Fix all flake8 errors: `flake8 musiclib --max-complexity=12`
3. Fix mypy errors: `mypy musiclib --ignore-missing-imports`

**Effort**: 8 hours (cleanup + CI update + verification)

---

## Summary Timeline

| Phase | Duration | Deliverable | Tests Pass | Backward Compatible |
|-------|----------|-------------|------------|---------------------|
| **Phase 0** | 1-2 days | v0.9.1 hotfix | ✅ | ✅ |
| **Phase 1** | 1 week | v0.9.2 quick wins | ✅ | ✅ (deprecation warnings) |
| **Phase 2** | 2-3 weeks | v0.10 structural | ✅ | ⚠️ (API changes) |
| **Phase 3** | 2-3 weeks | v0.11 tech debt | ✅ | ✅ |
| **Phase 4** | 1-2 weeks | v1.0.0 production | ✅ | ⚠️ (remove deprecated) |

**Total Timeline**: 6-9 weeks to v1.0.0

---

## Testing Strategy

### Regression Testing
- Golden fixtures must pass bit-for-bit after each phase
- Performance benchmarks must not regress >20%
- All 156 existing tests must continue passing

### New Test Requirements
- Phase 0: +3 tests (None-handling, version check)
- Phase 1: +20 tests (compat.py, deprecation warnings)
- Phase 2: +30 tests (refactored functions, validate_config.py)
- Phase 3: +15 tests (save_with_metadata, config params)
- Phase 4: +10 tests (NumPy 2.x compatibility, packaging)

**Target for v1.0**: 234 tests (current 156 + 78 new)

---

## Risk Mitigation

### Backward Compatibility Breaks
**Risk**: Users' configs and scripts break
**Mitigation**:
- Deprecation warnings in v0.9-v0.11
- Comprehensive migration guide (`docs/MIGRATION_V1.0.md`)
- Support both old and new patterns for 2 releases minimum

### Performance Regression
**Risk**: Refactoring introduces slowdowns
**Mitigation**:
- Benchmark before/after each phase
- CI performance regression detection (already in place)
- Profile memory usage for large batches

### NumPy 2.x Migration
**Risk**: Breaking changes, compatibility issues
**Mitigation**:
- Test matrix with both NumPy 1.x and 2.x
- Isolated migration branch for testing
- Document all NumPy-related changes

---

## Decision Points for Maintainer

Before proceeding, please decide:

1. **Phase 0 Immediate?** Should we ship v0.9.1 immediately with critical fixes?
2. **PyPI Distribution?** Is packaging (Issue 14) needed, or skip?
3. **NumPy 2.x Timing?** Migrate in v1.0, or defer to v1.1?
4. **API Breaking Changes?** Accept in v1.0 (with migration guide), or maintain full backward compat?
5. **Code Quality Enforcement?** Make CI checks hard failures, or keep warnings-only?
6. **Return Value Standardization?** Use dataclasses (Issue 9), or keep tuples with documentation?

Please provide guidance on these decisions to finalize the remediation roadmap.

---

**Document Version**: 1.0
**Author**: Claude (Sonnet 4.5)
**Date**: 2025-12-30
**Status**: Pending maintainer review
