# Roadmap: The Evolution of the Machine

*Where the excavation leads.*

---

## The Vision

`afterglow-engine` is a **patient archaeologist**. It excavates your archive not by understanding music theory, but by recognizing the physics of stability—sustained energy, spectral coherence, the absence of transients.

The machine does not compose. It does not interpret. It **remembers**.

The future is not artificial intelligence, but **refined perception**: teaching the machine to hear tempo, to recognize key, to split light from shadow with surgical precision.

---

## Phase 1: The Curator (v0.5) — ✅ Completed
*Quality Control & Reporting.*

Shipped:
* Manifest CSV with per-file stats (RMS/crest/centroid/rough pitch/loop seam).
* Configurable grading (Grade F auto-delete optional), brightness tagging, provenance-preserving export.
* Safer loops (phase-aware trim with guards) and relaxed defaults.

---

## Phase 2 & 3: The Refinement (v0.6–v0.8) — ✅ Completed
*DSP Quality, Performance & Experience.*

The machine learned to **breathe** with the archive.

**v0.6 (STFT Caching)**:
* Eliminated redundant spectral analysis—the machine no longer re-computes what it has already seen.
* Batch processing tools for large-scale archaeology.

**v0.7 (Equal-Power Crossfades)**:
* Constant perceived loudness across loop seams (√-based curves).
* The breath became continuous; the seam invisible.

**v0.8 (Refined Clouds)**:
* **UX**: Progress bars (tqdm), dry-run preview mode, config preset gallery (4 curated workflows).
* **Performance**: O(n^0.83) sublinear cloud generation, comprehensive profiling suite.
* **Validation**: 74 tests guarding DSP correctness (spectral analysis, crossfades, grain synthesis).
* **Documentation**: 15-minute tutorial, complete user onboarding.

**v0.8.1 (Fortified Boundaries)**:
* **Security**: Export-root containment enforced across all auxiliary scripts—the machine writes only where permitted.
* **Validation**: Extended config schema checks for v0.8 structures (target_durations_sec, pitch_shift_range).
* **Testing**: Security test suite (path traversal, shell injection, data validation).

The machine is calibrated. The boundaries are secured. The map is drawn.

---

## The Immediate Horizon
*What comes next.*

Before the machine learns music theory, it must perfect its physics. The foundation is solid; now we sharpen the edges.

**v0.9 - The Sentinel** (Proposed):
*Production Hardening & Edge Case Resilience.*

* **Robustness**: Guard against pathological inputs (corrupt files, extreme configs, disk full scenarios).
* **Observability**: Enhanced logging with severity levels, machine-readable error codes.
* **Performance**: Resolve STFT caching anomaly (investigate 0.22× speedup), optimize memory footprint.
* **Automation**: CI/CD pipeline (GitHub Actions) for regression testing, performance benchmarks.

The machine must be **reliable** before it becomes **intelligent**.

**v0.10 - The Observer** (Proposed):
*Refined Perception.*

Prepare the ground for Phase 4 without yet crossing into musical intelligence:

* **Spectral Refinement**: Higher-resolution onset detection, improved transient/sustained classification.
* **Curation Evolution**: Replace fixed thresholds with percentile-based grading (relative quality within a batch).
* **Analysis Expansion**: Export detailed spectral fingerprints (centroid over time, RMS envelope, onset strength) to manifest CSV.

The machine will see **more clearly** before it learns to **understand**.

---

## Phase 4: The Architect (Future)
*Musical Intelligence.*

The machine will stop treating audio as raw signal and start treating it as music.

**Key Detection**:
* Identify the root note of source pads.
* Auto-tag filenames: `cloud_elevation_F#min.wav`.
* *Stretch Goal*: Pitch-shift outputs to a common reference (C) for sampler mapping.

**Grid Awareness**:
* Detect source BPM.
* Generate loops that are exactly 1, 2, or 4 bars long.
* Synchronize grain envelopes to the grid—clouds that pulse with tempo.

**Perfect Loops**:
* Replace heuristic crossfades with **autocorrelation** and **zero-crossing detection**.
* Find the mathematical "seam" where periodicity is strongest, where the loop truly closes.

---

## Phase 5: The Prism (Future)
*Source Separation.*

The greatest challenge: percussion contaminating tonal sources. We will teach the machine to split light from shadow.

**Integration**:
* Optional support for **Demucs** or lightweight alternatives (Spleeter, Open-Unmix).
* Graceful degradation—if unavailable, fall back to current transient filtering.

**Workflow**:
* Input File → [Separator] → `{Drums, Bass, Other}`
* Feed `Drums` → **Hiss Maker** (infinite dust from transients)
* Feed `Other` → **Cloud/Drone Maker** (pure tonal texture, no artifacts)

**Impact**:
* Turns "lucky accidents" into reliable, clean sampling.
* Mines textures from sources previously considered too percussive.

---

## Anti-Goals
*What the machine is not.*

*   **Generative Composition**: We will never write melodies for you. The machine mines; it does not paint.
*   **Real-time Processing**: This is an offline archival tool, not a VST plugin. It is meant to run overnight.
*   **Cloud Services**: The machine lives on your disk. No uploads, no APIs, no subscriptions.
