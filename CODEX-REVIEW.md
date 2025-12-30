# CODEX Review Notes

## Orientation Notes
- Entry points and orchestration live in `make_textures.py` with config validation via `validate_config.py`.
- Core DSP and mining logic sit in `musiclib/` modules (pad mining, drones, granular clouds, hiss).
- CI is GitHub Actions with a single Python 3.11 test matrix in `.github/workflows/ci.yml`.

## Code Health Notes
- `musiclib/hiss_maker.py` can return `None` for hiss outputs on silent material, but callers still append those outputs and `save_hiss()` does not guard against `None` inputs.
- There are skipped tests/TODOs in `tests/test_dsp_validation.py`.
- `musiclib/granular_maker_orig.py` appears to be an unused legacy module without references.

## Documentation Notes
- `docs/CI_CD.md` describes a Python 3.9–3.11 matrix, but the workflow only runs 3.11 now.
- `docs/CONFIG_QUICK_REFERENCE.md` references `UPGRADES.md` and `IMPLEMENTATION_SUMMARY.md`, which are missing.

---

## Executive Summary
The repository is organized and cohesive, with a clear CLI orchestration layer (`make_textures.py`) and modular DSP components in `musiclib/`. Error handling, logging, and config validation are well-developed, reflecting a mature pipeline design. There are a few sharp edges that can still trigger runtime failures (notably in hiss generation when silent material yields `None` buffers), and some documentation has drifted from the current CI setup and available files. Overall maintainability is trending positive, but a handful of consistency and robustness gaps should be addressed to keep the machine reliable at scale.

## Critical Issues
1. **Hiss generation can crash when silent or invalid audio returns `None`.**
   - `make_hiss_loop()` and `make_flicker_burst()` return `None` for silent/invalid audio (`musiclib/hiss_maker.py:L101-L106`, `L170-L176`).
   - `process_hiss_from_drums()` and `process_hiss_synthetic()` append these `None` values to outputs (`musiclib/hiss_maker.py:L223-L252`, `L295-L324`).
   - `save_hiss()` immediately computes metadata and attempts to save, which will error if `hiss_audio` is `None` (`musiclib/hiss_maker.py:L387-L413`, and metadata access in `musiclib/dsp_utils.py:L170-L221`).
   - Impact: a single silent drum file can terminate an entire batch run rather than being skipped gracefully.

## Priority Improvements
### Quick wins (< 1 hour each)
- **Filter out `None` hiss outputs before saving.**
  - Guard in `process_hiss_from_drums()` and `process_hiss_synthetic()` to skip `None` outputs, or add a `None` check in `save_hiss()` before metadata computation (`musiclib/hiss_maker.py:L223-L252`, `L295-L413`).
- **Align CI documentation with actual workflow.**
  - Update `docs/CI_CD.md` to reflect the current Python 3.11-only matrix (`docs/CI_CD.md` vs `.github/workflows/ci.yml`).
- **Document missing references or remove them.**
  - `docs/CONFIG_QUICK_REFERENCE.md` references `UPGRADES.md` and `IMPLEMENTATION_SUMMARY.md`, which do not exist; either add them or remove the references (`docs/CONFIG_QUICK_REFERENCE.md:L416-L418`).

### Medium effort (half-day to few days)
- **Add a dependency audit step.**
  - Requirements are pinned (`requirements.txt`), but there is no lockfile or automated audit for known CVEs. Add `pip-audit` or similar tooling to CI for supply-chain visibility.
- **Clarify config and env override behavior.**
  - `io_utils.save_audio()` enforces an export root from `AFTERGLOW_EXPORT_ROOT` (default `export`), while `config.yaml` defaults to `export/tr8s`; document this in README to avoid confusion for custom export paths (`musiclib/io_utils.py:L129-L155`, `README.md`).

### Substantial (requires dedicated focus)
- **Consolidate legacy and current schema paths.**
  - `validate_config.py` checks legacy keys (e.g., `hiss.burst_duration_*`, `swells.*`, `drones.target_duration_sec`) not used by current modules, which can create user confusion and drift (`validate_config.py:L151-L180`).
  - Consider a formal schema version or a deprecation layer to reduce implicit contracts.

## Latent Risks
- **Silent failure due to broad exception capture in loaders.**
  - `io_utils.load_audio()` catches all exceptions and returns `(None, None)` (`musiclib/io_utils.py:L62-L82`). This avoids crashes but can hide systemic decode errors in batch runs unless callers track counts and surface a final warning summary.
- **Config parse errors are not handled in `load_or_create_config()`.**
  - An invalid YAML file will raise and exit without a user-friendly message (`make_textures.py:L179-L189`). A guard could improve operator experience in production batch runs.
- **Heavy workloads can stress memory/CPU without explicit backpressure.**
  - Grain extraction and STFT usage scale with large audio files, and there is no explicit resource limit or streaming mode (`musiclib/granular_maker.py:L115-L504`, `musiclib/audio_analyzer.py:L94-L175`).

## Questions for the Maintainer
1. Is `musiclib/granular_maker_orig.py` still required, or is it safe to archive/remove as legacy?
2. Should the CI documentation remain forward-looking (multi-version) or reflect the current 3.11-only test matrix?
3. Are the legacy config keys in `validate_config.py` still intended to be supported, or can they be deprecated to tighten the schema?
4. Should the README explicitly document `AFTERGLOW_EXPORT_ROOT` and `AFTERGLOW_UNSAFE_IO` for users who change `paths.export_dir`?

## What's Actually Good
- **Strong defensive DSP utilities.** Normalization and filter design functions validate inputs and guard against invalid data (`musiclib/dsp_utils.py:L61-L413`).
- **Structured logging and domain-specific errors.** The logging system and custom exceptions make error handling clearer and maintain the tool’s tone (`musiclib/logger.py`, `musiclib/exceptions.py`).
- **Pre-analysis caching and stability masking.** STFT caching and stability filtering are thoughtfully implemented and documented (`musiclib/audio_analyzer.py:L94-L339`).
- **Comprehensive test suite footprint.** Tests cover DSP validation, robustness, security, and integration (`tests/`), even if a few cases are currently skipped (`tests/test_dsp_validation.py:L85-L101`).
- **Data safety guardrails.** Export-root checks and disk space validation reduce the risk of accidental destructive writes (`musiclib/io_utils.py:L129-L214`).
