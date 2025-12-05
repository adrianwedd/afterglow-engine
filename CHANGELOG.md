# afterglow-engine CHANGELOG

*A record of excavation.*

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
