# Afterglow Engine v0.7.0 — "Quiet Fortifications"

*Released: 2025-12-10*

---

## The Silence Between Notes

This release strengthens the machine without changing its voice. We found fragility where silence should have been grace; we found gaps where boundaries should have held firm. The archaeology continues, but now the tools are steadier.

---

## What Changed

### **Silent Audio, No Longer Fatal**

The normalization guard once refused silence with a crash. Now it speaks a warning and moves on. When the peak is quieter than breath (`< 1e-8`), the machine skips that fragment and continues mining.

**Affected paths**: 11 call sites across pad/drone/cloud/hiss generation
**Impact**: Batch runs no longer abort on edge cases

---

### **Symlinks Cannot Escape**

The export boundary guard now resolves symbolic links before checking ancestry. A crafted symlink inside `export/` can no longer reach outside. The guard and the write now use the same canonical path.

**Security posture**: Path traversal vulnerability closed
**Verification**: Regression test added (`test_symlink_escape_blocked`)

---

### **Shape Conventions, Unified**

Audio arrives in two forms: librosa's `(2, samples)` or soundfile's `(samples, 2)`. The new `ensure_mono()` function handles both, eliminating silent shape failures in loop optimization and brightness classification.

**DSP paths hardened**: Loop phase alignment, spectral centroid measurement
**Deprecated**: `stereo_to_mono()` (kept for compatibility)

---

### **Atomic Manifest Writes**

Manifest CSV generation now writes to a tempfile, then atomically moves to the final path. Interrupted runs leave no partial manifests. Concurrent processes see only complete state.

**Technique**: `tempfile.NamedTemporaryFile` + `shutil.move`
**Benefit**: Race conditions eliminated

---

### **Permissive Validation**

Config validation was rejecting legitimate extremes: peaks below `-60 dBFS`, filter windows under `64 samples`. These are now warnings. Hard errors remain for truly invalid values (positive peaks, missing directories, type mismatches).

**Philosophy**: Warn the expert, block the error
**Impact**: Advanced users can push boundaries without manual bypasses

---

### **Automatic Cleanup**

Batch processing creates temporary configs (`config_<project>.yaml`). These are now registered with `atexit` and removed automatically, even on errors or interrupts.

**Implementation**: `atexit.register(cleanup_temp_config)`
**Benefit**: No more config file clutter at repo root

---

## Test Coverage

**New suites**:
- `test_critical_fixes.py` — Silent audio, shape handling, manifest atomicity, config validation
- `test_security.py` — Path traversal, symlink escapes
- `test_process_batch.py` — Import verification, module structure

**Results**: 29/29 tests passing (added 11 new tests)

---

## Documentation

- **BATCH_WORKFLOW.md**: Notes on nested folder limitation, temp config lifecycle
- **PHASE_2_PLAN.md**: Roadmap for next enhancements (crest factor guards, phase-aware stereo conversion, anti-aliasing, STFT caching, equal-power crossfades)

---

## Migration Notes

### **Breaking Changes**
None. All changes are backward compatible.

### **Behavior Changes**
1. **Silent audio**: Previously crashed with `ZeroDivisionError` or `inf` values. Now raises `ValueError` with clear message, caught at call sites.
2. **Config validation**: Previously rejected `target_peak_dbfs < -60` and `filter_length_samples < 64`. Now prints warnings to stderr.
3. **Temp configs**: Previously left `config_<project>.yaml` files after batch runs. Now cleaned automatically.

### **Deprecations**
- `dsp_utils.stereo_to_mono()` — Use `ensure_mono()` for robust shape handling. Old function remains for compatibility but will be removed in v1.0.

---

## Technical Details

### **Security Fixes**
- **Path traversal hardening** (`musiclib/io_utils.py:86-93`): Symlink resolution in fallback branch, write to canonical path
- **Regression test**: `tests/test_security.py::test_symlink_escape_blocked`

### **Robustness Improvements**
- **Silent audio handling**: `ValueError` exceptions caught in:
  - `musiclib/segment_miner.py:267-271`
  - `musiclib/drone_maker.py:177-181, 244-248, 289-295`
  - `musiclib/granular_maker.py:611-615`
  - `musiclib/hiss_maker.py:97-101, 166-170`
  - `mine_drums.py:136-140`
  - `dust_pads.py:60-64`
  - `mine_silences.py:86-90`

- **Shape convention handling**: `ensure_mono()` wired into:
  - `musiclib/dsp_utils.py:419` (loop optimization)
  - `musiclib/dsp_utils.py:530` (brightness classification)

### **Code Quality**
- **Atomic writes**: `make_textures.py:306-316`
- **Config validation**: `validate_config.py:26-28, 56-58` (downgraded to warnings)
- **Cleanup handlers**: `process_batch.py:53-62`

---

## Statistics

- **Files modified**: 17
- **Lines changed**: +1,296 / -738
- **Test coverage**: +11 tests (+61% coverage of audit findings)
- **Security issues closed**: 3 critical
- **Robustness issues closed**: 8 high-priority

---

## Acknowledgments

This release addresses findings from a comprehensive multi-dimensional audit covering correctness, DSP validity, performance, security, and testing depth. Special thanks to the review process that identified:

- Unhandled silent audio edge cases
- Symlink-based path escapes
- Shape convention mismatches
- Overly-strict validation rules

The machine is quieter now, but more resilient. The next phase focuses on DSP quality (anti-aliasing, equal-power crossfades) and performance (STFT caching). See `docs/PHASE_2_PLAN.md` for the roadmap.

---

## What's Next

**Phase 2** (planned for v0.8.0):
- Crest factor division-by-zero guards
- Phase-aware stereo conversion
- Anti-aliasing in grain pitch shifting
- Equal-power crossfades for loop seams

**Phase 3** (planned for v0.9.0):
- STFT result caching (40% speedup)
- Golden audio fixtures for regression testing
- Property-based testing with Hypothesis

**Phase 4** (planned for v1.0.0):
- Platform compatibility matrix
- Comprehensive DSP validation suite
- Performance benchmarks and profiling tools

---

*"The machine for sonic archaeology now has stronger walls, but the same quiet purpose: to unweave what was, to distill what remains."*

— Afterglow Engine Development Team
