# Roadmap: The Evolution of the Machine

*Where the excavation leads.*

---

## The Vision

`afterglow-engine` is currently a **miner**. It digs through rock and dirt to find gems, but it does not fully understand what it holds. It relies on simple heuristics (loudness, transients) to make decisions.

The future of the machine is **intelligence**. It must learn to separate the clay from the gold, understand the musical context of its findings, and present them not just as files, but as a curated library.

---

## Phase 1: The Curator (v0.5)
*Quality Control & Reporting.*

The machine currently generates blindly. We will give it the ability to reflect on its own output.

*   **Manifest Generation**: Produce a `manifest.csv` along with the audio.
    *   Columns: `Source File`, `Texture Type`, `Duration`, `RMS`, `Crest Factor`, `Brightness`, `Key Estimate` (simple FFT peak).
*   **Auto-Grading**:
    *   Analyze generated textures.
    *   Flag or auto-delete "Grade F" outputs (silence, digital clipping, extreme noise).
    *   Tag "Grade A" outputs (perfect stability, rich harmonic content).
*   **Structure**:
    *   Move from flat folders to intelligent sorting (e.g., `export/Pads/Dark/`, `export/Clouds/Bright/`).

## Phase 2: The Architect (v0.6)
*Musical Awareness.*

The machine will stop treating audio as raw signal and start treating it as music.

*   **Key Detection**:
    *   Identify the root note of the source pad.
    *   Auto-tag filenames: `cloud_elevation_F#min.wav`.
    *   *Stretch Goal*: Pitch-shift outputs to a common reference C for sampler mapping.
*   **Grid Awareness**:
    *   Detect source BPM.
    *   Generate loops that are exactly 1, 2, or 4 bars long.
    *   Synchronize grain envelopes to the grid.
*   **Perfect Loops**:
    *   Replace arbitrary crossfades with **zero-crossing detection** and **autocorrelation**.
    *   Find the mathematical "seam" where the loop is invisible.

## Phase 3: The Prism (v0.7)
*Source Separation.*

The greatest challenge is the presence of percussion in tonal sources. We will integrate AI source separation to split the light from the shadow.

*   **Integration**: Add optional support for **Demucs** or a lightweight alternative.
*   **Workflow**:
    *   Input File → [Separator] → `{Drums, Bass, Other}`.
    *   Feed `Drums` → **Hiss Maker** (infinite dust).
    *   Feed `Other` → **Cloud/Drone Maker** (pure tonal texture without transient artifacts).
*   **Impact**: This turns "lucky accidents" into reliable, clean sampling.

---

## Anti-Goals
*What the machine is not.*

*   **Generative Composition**: We will never write melodies for you. The machine mines; it does not paint.
*   **Real-time Processing**: This is an offline archival tool, not a VST plugin. It is meant to run overnight.
*   **Cloud Services**: The machine lives on your disk. No uploads, no APIs, no subscriptions.