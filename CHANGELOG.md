# afterglow-engine CHANGELOG

*A record of excavation.*

---

## v0.9 (The Sentinel)
*The machine becomes production-ready.*

The prototype awakens into watchfulness. Where once failures crashed in silence, they now speak with clarity. Where errors hid in shadows, exceptions now carry context. The machine remembers its actions, logs its thoughts, tests itself relentlessly.

No longer merely functional—it is now *hardened*. The sentinel guards against corruption, watches for performance regression, validates at every boundary. It knows when disk runs dry, when audio contains infinity, when paths escape their bounds.

The archaeology continues, but now with safeguards.

**Technical Details:**

*   **Observability & Error Handling:**
    *   Structured logging system (`musiclib.logger`) with module-level tagging and configurable verbosity via `AFTERGLOW_LOG_LEVEL`.
    *   Custom exception hierarchy: `SilentArtifact`, `ClippedArtifact`, `FilesystemError`, `DiskFullError`, `AfterglowPermissionError`.
    *   All custom exceptions carry rich debugging context (peak values, RMS, paths, available disk space).
    *   Graceful degradation: `load_audio()` returns `(None, None)` instead of raising exceptions, enabling batch processing to continue.
    *   Visual style preserved: log messages use `[*]`, `[!]`, `[✓]`, `[✗]` prefixes for CLI feel.

*   **CI/CD & Quality Gates:**
    *   GitHub Actions workflows for automated testing across Python 3.9, 3.10, 3.11.
    *   Performance regression detection: fails builds if >20% slower than baseline.
    *   Code quality checks: Flake8, Black, MyPy integration (continue-on-error for gradual adoption).
    *   Automated release workflow on version tags.
    *   Coverage reporting to Codecov (Python 3.11).

*   **Robustness:**
    *   26 new edge case tests: corrupt audio (zero-byte, truncated WAV, non-audio files), extreme configurations (inverted RMS ranges, zero sample rates), filesystem issues (disk full, read-only directories, path traversal).
    *   Input validation across all DSP functions: NaN/Inf detection, parameter range checking, empty array guards.
    *   Path traversal security: writes outside export root blocked unless `AFTERGLOW_UNSAFE_IO=1` (testing only).
    *   Test suite expanded: 159 passed, 4 skipped (up from 73 in v0.8).

*   **Performance:**
    *   Corrected STFT caching benchmark methodology (previous 0.22× result was measuring all feature caching, not just STFT).
    *   Verified >100,000× speedup on subsequent STFT calls (essentially free after first computation).
    *   Single-pass overhead reduction: ~66% (1 STFT call vs 3 calls for multiple features).
    *   Documented grain quality filtering as intentional bottleneck (60-70% of time, necessary for quality).

*   **Documentation:**
    *   `docs/LOGGING.md` - Structured logging guide (260 lines): log levels, environment variables, migration from print().
    *   `docs/ERROR_HANDLING.md` - Exception hierarchy and patterns (326 lines): custom exceptions, error recovery strategies, exit codes.
    *   `docs/CI_CD.md` - GitHub Actions workflow documentation (291 lines): workflow descriptions, baseline management, local testing.
    *   `docs/MIGRATION_V0.9.md` - Migration guide from v0.8 (376 lines): breaking changes, recommended upgrades, rollback instructions.
    *   Updated README.md with v0.9 features, CI badges, and usage flags (`--verbose`, `--strict`).

*   **Breaking Changes (Minimal):**
    *   `io_utils.load_audio()` returns `(None, None)` on error instead of raising exceptions (requires None checks).
    *   Exception types changed from generic `ValueError`/`Exception` to specific custom types (`SilentArtifact`, `FilesystemError`).
    *   `dsp_utils.normalize_audio()` now clips to [-1, 1] range to prevent overflow.

*   **New Environment Variables:**
    *   `AFTERGLOW_LOG_LEVEL` - Control log verbosity (DEBUG/INFO/WARNING/ERROR/CRITICAL).
    *   `AFTERGLOW_EXPORT_ROOT` - Set export directory (default: `export`).
    *   `AFTERGLOW_UNSAFE_IO` - Allow writes outside export root (testing only, default: disabled).

*   **New CLI Flags:**
    *   `--verbose` - Enable debug logging (equivalent to `AFTERGLOW_LOG_LEVEL=DEBUG`).
    *   `--strict` - Fail on first error (useful for CI/CD validation).

---

## v0.8 (Refined Clouds)
*The machine polishes its textures.*

The clouds emerge cleaner now. Where grains once clashed and folded, they breathe with headroom. The machine remembers its randomness when asked, making comparison possible. Division by silence no longer breaks the spell.

**Technical Details:**
*   **Cloud Quality:**
    *   Gentler normalization target (`-3.0 dBFS`) prevents saturation on dense grain overlaps.
    *   Anti-aliasing filter on upward pitch shifts eliminates foldover artifacts.
    *   Reproducible grain placement via `random_seed` config for deterministic A/B testing.
*   **Equal-Power Crossfades:**
    *   New `equal_power` parameter (default `True`) uses sqrt-based fade curves for constant perceived loudness.
    *   Applied to both `crossfade()` and `time_domain_crossfade_loop()` functions.
*   **Phase 3 Optimizations:**
    *   STFT result caching in `AudioAnalyzer` and `segment_miner` (eliminates redundant computation).
    *   Golden audio fixtures for regression testing (9 deterministic reference files).
    *   Property-based testing with Hypothesis (8 active tests; 3 commented where properties don't hold for pathological inputs).
*   **Robustness:**
    *   Crest factor guards prevent division by zero on silent audio (3 locations).
    *   Phase-aware stereo→mono conversion with `method` parameter (`average`, `sum`, `left`, `right`).
    *   Bit depth verification after save operations.
    *   Verbose onset detection feedback for debugging grain filtering.

---

## v0.7 (Quiet Fortifications)
*Stronger walls, same quiet purpose.*

The machine found fragility where silence should have been grace. It found gaps where boundaries should have held firm. Now the tools are steadier, the walls stronger, but the voice unchanged.

**Technical Details:**
*   **Robustness:**
    *   Silent audio no longer crashes normalization (11 call sites hardened with proper `ValueError` handling).
    *   Shape convention handling unified via `ensure_mono()` supporting both `(2, samples)` and `(samples, 2)` formats.
    *   Atomic manifest writes using tempfile + move to prevent partial CSV corruption.
*   **Security:**
    *   Path traversal vulnerability closed via symlink resolution in export boundary checks.
    *   Canonical path comparison prevents crafted symlink escapes.
*   **Batch Processing:**
    *   Automatic cleanup of temporary configs via `atexit` handlers.
    *   Permissive validation (extremes become warnings, not errors).
*   **Test Coverage:**
    *   Added 11 new tests covering silent audio, shape handling, security, batch processing.
    *   Results: 29/29 passing.

---

## v0.6 (The Architect)
*The machine understands context.*

Instead of treating audio as raw signal, the engine now listens for key and tempo. It aligns the excavation to the musical grid.

**Technical Details:**
*   **The Ear (Analysis):**
    *   Added `musiclib/music_theory.py` for chroma-based Key detection and beat-tracking BPM detection.
    *   Pre-flight analysis runs on every source file before processing; results (Key, BPM) are passed to all modules.
*   **The Transposer:**
    *   New `target_key` config option allows auto-transposing entire archives to a single root (e.g., "C maj").
    *   Implemented relative pitch-shifting in Drones and resampling-based shifting in Clouds to maintain fidelity.
*   **The Seamstress (Looping):**
    *   New `find_best_loop_trim` function uses cross-correlation to find the optimal phase-aligned cut point.
    *   Pads and Drones now loop seamlessly with significantly reduced artifacts.
*   **Manifest:**
    *   `manifest.csv` now includes `Detected Key`, `Detected BPM`, and `Transposition` columns.

---

## v0.5 (The Curator)
*The machine learns to judge.*

The engine now audits its own work. It no longer blindly saves everything; it measures, grades, and reports.

**Technical Details:**
*   **In-Memory Analysis:** New `compute_audio_metadata` function calculates RMS, Peak, Crest Factor, Spectral Centroid, and Loop Seam Error for every generated buffer *before* saving.
*   **Auto-Grading:**
    *   `grade_audio` assigns a letter grade (A/B/F) based on configurable thresholds (`min_rms_db`, `clipping_tolerance`, `max_crest_factor`).
    *   Optional `auto_delete_grade_f` to keep the output clean.
*   **Manifest Generation:** All runs now produce a `manifest.csv` in the export folder, logging stats and grades for every file created.
*   **Cloud Fallback:** Refined soft fallback logic for granular synthesis now logs when it happens and chooses the least-chaotic windows.
*   **Loop Optimization:** Added `find_best_loop_trim` (cross-correlation) to automatically align loop points for minimal phase error.

---

## v0.4 (The Frame)
*Stability, not drift.*

Clouds now stay tonal even when the archive is noisy. The machine prefers the least chaotic windows, and only falls back when it must.

**Technical Details:**
*   **Stable Regions, Keyed:** Stability masks cache per-threshold set; different onset/RMS/centroid gates recompute correctly.
*   **Quality-Aware Fallback:** When no windows pass the strict mask, grains come from the top ~20% lowest-onset windows that also pass RMS/DC/crest gates; grain offsets/lengths are clamped to window bounds.
*   **Safer Clouds:** Guarded fades on final clouds; resample-based pitch shift stays within reasonable rates.
*   **Defaults & Validation:** Relaxed pre-analysis defaults (usable out-of-box); validation now checks analysis window/hop and overlap ratios.
*   **Tests:** Added analyzer cache/fallback/fade tests; integration updated to find hiss exports.

---

## v0.3 (The Eye)
*The machine learns to see.*

Previously, the engine grabbed blindly. Now, it looks first. It finds the stable places, the moments of low movement, and avoids the transients and the noise.

**Technical Details:**
*   **Pre-Analysis Framework (`AudioAnalyzer`):**
    *   Implemented a windowed analysis pass that scans source audio before processing.
    *   Identifies "stable regions" based on RMS amplitude, onset density, DC offset, and crest factor.
*   **Intelligent Granular Synthesis:**
    *   `granular_maker` now uses the stability mask to source grains only from high-quality regions.
    *   Implemented "smart" grain extraction that avoids silence and clicks.
    *   Added quality scoring for individual grains.
*   **Spectral Tagging:**
    *   Added brightness classification (`dark`, `mid`, `bright`) based on spectral centroid.
    *   Output filenames now include these tags for easier sorting.
*   **Configurable Stability:**
    *   New `pre_analysis` section in `config.yaml` to tune thresholds for stability detection.
*   **Consecutive Window Enforcement:**
    *   Ensured that stability is not just a single lucky window, but a sustained region (run-length encoding on stability masks).

---

## v0.2 (The Canvas)
*Broader strokes.*

Expanding the palette. The machine can now paint in stereo, and understands that not all time is equal.

**Technical Details:**
*   **Variable Pad Durations:**
    *   `pad_miner` supports a list of `target_durations_sec` (e.g., `[1.5, 3.0, 5.0]`), allowing extraction of both short loops and long atmospheres from the same source.
*   **Stereo Export:**
    *   Added configuration to export Clouds, Hiss, and Pads in true stereo.
    *   Preserves spatial width of granular textures.
*   **Hiss & Flicker Improvements:**
    *   Added band-pass filtering options to the Hiss generator for more controlled noise floors.
    *   Added "Flicker" generator for short, randomized burst interference.
*   **Granular Refinements:**
    *   Configurable pitch shift range (min/max semitones).
    *   Polyphonic cloud construction (overlapping grain streams) implied by improved density settings.
    *   Loop crossfade length is now configurable.

---

## v0.1 (The Origin)
*First digging.*

The initial proof of concept. A simple tool to automate the extraction of textures for the TR-8S.

**Technical Details:**
*   **Core Modules:**
    *   `pad_miner`: Basic RMS and onset-based extraction of sustained segments.
    *   `drone_maker`: Simple pitch-shifting and time-stretching for tonal variants.
    *   `granular_maker`: Random grain extraction and overlap-add synthesis.
    *   `hiss_maker`: High-pass filtered noise generation.
*   **Architecture:**
    *   CLI entry point (`make_textures.py`).
    *   YAML-based configuration.
    *   Basic `dsp_utils` for normalization and windowing.
    *   `librosa`-based audio analysis.
