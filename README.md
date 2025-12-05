![afterglow-engine logo](ascii-art-text.png)

# afterglow-engine

*A small offline tool that mines your past audio work for new textures.*

---

## What this is(n't) — a metaphor

*Imagine this:*

*In a back room of your studio, you’ve secretly built a machine.*

*It doesn’t paint.*  
*It doesn’t choose subjects.*  
*It never tells you what to do with the canvas.*

*All it does is this:*

*You slide in your old work—finished canvases, abandoned panels, primed boards with ghosts of sketches under the gesso, photos of murals that no longer exist, even quick studies on cheap paper you once did just to get your hand moving.*

*Inside, the machine:*

* *very carefully **unweaves** each piece,*
* *separates pigment from gesture,*
* *peels off glazes from underpainting,*
* *collects tiny flakes of colour from places no one ever really looked at.*

*It doesn’t keep compositions.*  
*It doesn’t remember figures or horizons.*

*It just saves **texture and colour**:*

* *a particular bruised green that only ever happened once when two paints misbehaved together,*
* *the way a translucent violet settled into the tooth of the canvas,*
* *that dry, scratchy ochre from a brush you forgot to clean,*
* *the chalky margin where gesso met raw linen.*

*Then it grinds those fragments down and re-bottles them into small, unlabelled jars:*

* *“evening wall light,”*
* *“wet concrete after a storm,”*
* *“skin in winter,”*
* *“dust on a forgotten windowsill.”*

*On your main table, nothing has changed:*  
*It’s still you, blank surface, brushes, knives, rags.*

*The only difference is your palette.*

*Now, when you reach for colour, you’re not just squeezing paint from factory tubes—you’re dipping into **distilled memories of your own work**:*

* *the atmosphere from a painting you sold years ago,*
* *the softness from a figure you painted over,*
* *the strange, accidental pink from a ruined canvas that still haunts you.*

*What we’ve built is that quiet machine:*  
*a patient studio assistant that wanders through your archives, gently steals back the colours and surfaces you’ve already invented, and lays them out again as fresh pigment.*

*So future paintings are not just new images.*  
*They’re painted with **the ground-up archaeology of everything you’ve ever touched.***

---

## The Machine

`afterglow-engine` is that idea—**sonic archaeology**—implemented in code.

It doesn’t make tracks.  
It doesn’t make creative choices.  
It doesn’t invent new sounds.

It simply walks the corridors of your archive, listening for the **afterglow** of your past work. It searches for the moments where the music stopped moving and started breathing—the stable pads, the textural grain, the dust in the air.

It isolates these moments, stabilizes them, and re-bottles them as **distilled artifacts**:

- **Pads** looped not by bars, but by phase.  
- **Clouds** formed from the grain of tonal memory.  
- **Dust** swept from the transients of forgotten drums.

It hands them back to you not as “content,” but as **pigment**.

---

## Quick Start

The short version:

```bash
# 1. Create and activate a virtualenv
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Validate config and generate textures
python validate_config.py          # optional but recommended
python make_textures.py --all
```

This will:

* create a default `config.yaml` (if it does not exist),
* read audio from the default input folders,
* write textures into `export/<Source_Name>/{pads,swells,clouds,hiss}` as 44.1 kHz WAVs.

---

## What’s New

### Latest: **v0.6 – The Architect**

* **Musical awareness**
  Detects key/BPM per source before processing.
* **Auto-transposition**
  Set `target_key` and drones/clouds conform to it.
* **Sharper loops**
  Phase-aligned seam finding to reduce clicks/wobble.

### Earlier highlights (v0.4–v0.5)

* **Granular clouds, upgraded**

  * Per-grain length variation within configured min/max
  * Grain quality analysis (RMS, DC, clipping, spectral skew)
  * Grain cycling to fully fill buffers with no accidental tail silence
  * Stereo export + dark/mid/bright tags driven by config

* **Curation & manifest (v0.5)**

  * A manifest is written to `export/manifest.csv` whenever phases run
  * Columns: filename, source, type, duration, RMS/peak/crest, centroid, rough pitch (for tonal types), loop seam error, brightness, and grade
  * Grades are based on thresholds in `curation.thresholds` (config).
    Set `curation.auto_delete_grade_f: true` to skip saving Grade F files (silence, clipping, extreme crest).

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

---

## Where Everything Lives

Top-level layout (defaults; all paths are configurable):

```text
.
├── config.yaml                   # Configuration (auto-generated on first run)
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── validate_config.py            # Config validator
├── make_textures.py              # Main CLI entrypoint
├── musiclib/                     # Python package
│   ├── __init__.py
│   ├── io_utils.py               # File discovery, loading, saving
│   ├── segment_miner.py          # Pad mining from sustained segments
│   ├── drone_maker.py            # Pad loops & swells with variants
│   ├── granular_maker.py         # Granular cloud generator
│   ├── hiss_maker.py             # Hiss loops & flicker bursts
│   └── dsp_utils.py              # Filters, envelopes, normalization, analysis
├── source_audio/                 # Drop your main audio sources here
├── pad_sources/                  # Hand-picked tonal material (optional)
├── drums/                        # Percussive/noisy material for hiss (optional)
└── export/
    ├── manifest.csv              # Optional manifest/curation data
    └── <Source_Name>/
        ├── pads/                 # Loopable pad outputs
        ├── swells/               # Swell one-shots
        ├── clouds/               # Granular textures
        └── hiss/                 # Hiss loops & flickers
```

Docs (if present) live under `docs/` (e.g. `CONFIG_QUICK_REFERENCE.md`, `BATCH_WORKFLOW.md`).

---

## Setup

### Prerequisites

* **Python:** recommended 3.11 (3.8+ may work, but 3.11 is tested)
* **OS:** macOS or Linux
* Enough disk space for temporary and exported WAVs

### Installation

```bash
git clone <your-repo-url> afterglow-engine
cd afterglow-engine

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then:

```bash
# Optional but recommended
python validate_config.py

# See available flags
python make_textures.py --help
```

---

## Features

* **Pad mining**

  * Automatically extract short, loopable pad segments from existing audio
  * Uses onset/RMS/spectral measures to find stable regions
  * Supports multiple target durations and configurable loop crossfade
  * Brightness tags (dark/mid/bright) via spectral centroid

* **Drone generation**

  * Time-stretch + pitch-shift tonal sources into pads and swells
  * Filter variants (warm, airy, dark) using band-sculpting filters
  * Key-aware processing (with `target_key` set in v0.6)
  * Per-category stereo/mono control

* **Granular clouds**

  * Turn any audio into evolving textures using granular synthesis
  * Per-grain randomised length and pitch (within configured ranges)
  * Grain quality filtering (RMS/DC/clipping/skew) to avoid junk grains
  * Grain cycling to fully fill the target duration
  * Stereo clouds with brightness tags

* **Hiss & air**

  * High-frequency loops and flicker bursts built from drums or synthetic noise
  * Configurable band-pass and tremolo settings
  * Designed to sit as “air” above pads, not as obvious rhythmic layers

* **Curation & manifest**

  * Manifest at `export/manifest.csv` capturing metadata and grades
  * Simple threshold-based grading (A–F) for quick triage
  * Optional auto-delete for Grade F results

All outputs are standard WAVs (44.1 kHz, 24-bit or 16-bit), ready for samplers and DAWs. Defaults are friendly to the Roland TR-8S, but nothing is tied to that specific device.

---

## Usage

### One command: generate everything

```bash
python make_textures.py --all
```

This will:

1. Mine sustained pads from `source_audio/` → `export/<source>/pads/`
2. Turn `pad_sources/` (+ mined pads) into loops and swells → `pads/` & `swells/`
3. Build granular clouds → `clouds/`
4. Generate hiss textures → `hiss/`
5. Update/add `export/manifest.csv` with metadata and grades

### Run individual phases

```bash
# 1) Mine sustained pads from source_audio/
python make_textures.py --mine-pads

# 2) Turn pad_sources/ into loops + swells
python make_textures.py --make-drones

# 3) Build granular clouds from pad_sources/
python make_textures.py --make-clouds

# 4) Generate hiss/flickers from drums/ (or synthetic fallback)
python make_textures.py --make-hiss
```

Common flags:

* `--config <path>` – use a non-default YAML config
* `--root <path>` – override the working directory (if supported)
* Set `reproducibility.random_seed` in `config.yaml` for deterministic runs

See:

```bash
python make_textures.py --help
```

for the authoritative CLI options.

---

## Configuration

On first run, a default `config.yaml` is created with inline comments.

You can tweak:

* **Global**

  * Sample rate, bit depth, normalization target (`global.target_peak_dbfs`)

* **Pad mining (`pad_miner`)**

  * RMS and onset thresholds
  * Minimum/maximum durations and target durations (list)
  * `loop_crossfade_ms` (or legacy `crossfade_ms`) for smoothing seams

* **Drones/swells (`drone_maker`)**

  * Time-stretch factors
  * Pitch-shift sets (e.g. `[-12, 0, 7]`)
  * Envelope rise/decay for swells
  * Filter variants (warm/airy/dark) and their parameters

* **Clouds (`clouds`)**

  * Grain length min/max
  * Grains per cloud and overlap
  * Pitch-shift range (min/max semitones)
  * Quality thresholds (RMS/DC/clipping/skew)
  * Stereo vs mono export

* **Hiss (`hiss`)**

  * Band-pass / high-pass ranges
  * Tremolo depth/rate
  * Flicker durations and count

* **Curation (`curation`)**

  * Thresholds for A–F grading
  * `auto_delete_grade_f` to drop clearly unusable output

* **Brightness tags (`brightness_tags`)**

  * Centroid thresholds for dark/mid/bright

Validate after editing:

```bash
python validate_config.py
```

The validator will catch obvious issues (negative durations, inverted frequency ranges, overlaps outside (0, 1], unsupported bit depths, etc.) before you hit them at runtime.

---

## Workflow

### 1. Prepare your audio

Place audio files in:

* `source_audio/` – full tracks, stems, or bounces you want mined for pads
* `pad_sources/` – tonal material you consider “ingredient” for pads/swells/clouds
* `drums/` – percussive or noisy content for hiss (optional; synthetic noise used as fallback)

Supported: WAV, AIFF, FLAC.

If you’re using the batch scripts (`discover_audio.py`, `select_sources.py`, `batch_generate_textures.py`), you can drive this from an existing archive and let the engine spin up per-track work dirs automatically.

### 2. Run the engine

Start with:

```bash
python validate_config.py
python make_textures.py --all
```

Or drive a single source via a wrapper (if you have e.g. `mine_textures_from_file.py`):

```bash
python mine_textures_from_file.py --input /path/to/track.flac --slug my_track
```

### 3. Import into your sampler / DAW

Copy from `export/` into your sampler’s sample directory:

```bash
cp -r export/* /Volumes/SAMPLER/
```

On a TR-8S, for example:

```bash
cp -r export/* /Volumes/TR8S/SAMPLES/
```

Then build kits/programs using:

* pads as sustained voices,
* clouds as evolving beds,
* swells as occasional accents,
* hiss as low-level air.

---

## Testing (smoke & verification)

There are two layers of testing:

* **Unit-style tests**

  * Focused on `musiclib/dsp_utils.py` and other math-heavy pieces
  * Guard against regressions in crossfades, filters, brightness classification, etc.

* **Integration / smoke test**

  * `python test_review_fixes.py` (or `pytest`, depending on how you wired it)
  * Runs the pipeline on small fixtures to ensure CLI wiring and stability masks are correct and that pitch-shift guards & logging toggles behave as expected.

Determinism:

```yaml
reproducibility:
  random_seed: 42
```

in `config.yaml` makes most randomised parts repeatable, which helps when chasing subtle differences.

---

## Tips & tricks

* **Start tiny**

  * Run `--all` on a single short track, audition results, then scale up.

* **Tune thresholds, don’t chase magic numbers**

  * If pad mining returns too few candidates, lower onset/RMS gates a bit.
  * If clouds feel too busy, reduce overlap or pitch range.

* **Curate ruthlessly**

  * Use the manifest and grades as a guide, but trust your ears.
  * Build small, memorable kits (10–20 files) instead of dumping everything into a single instrument.

* **Layer intentionally**

  * One pad + one cloud + one hiss bed, thoughtfully chosen, is often enough.

---

## Troubleshooting

* **“No audio files found”**

  * Check that `source_audio/`, `pad_sources/`, and/or `drums/` contain supported formats.
  * Confirm paths match your `config.yaml`.

* **“Config not found, creating default”**

  * Normal on first run. Edit `config.yaml` and re-run `validate_config.py`.

* **“Output is too quiet / too loud”**

  * Adjust `global.target_peak_dbfs` in `config.yaml`.

* **“Pads don’t loop smoothly”**

  * Increase `pad_miner.loop_crossfade_ms`
    (or legacy `pad_miner.crossfade_ms`, which is still honoured for older configs).

* **Librosa complaints about `n_fft` and short buffers**

  * On very short signals, librosa may warn that `n_fft` is large.
  * Usually harmless; to reduce warnings, use longer inputs or, if exposed, reduce `n_fft` in analysis settings.

---

## Dependencies & notes

Core dependencies:

* **librosa** – audio analysis (key/BPM, onset, spectral features), time-stretching, pitch-shifting
* **NumPy** – array operations, windowing, grain synthesis
* **SciPy** – filters and windows
* **SoundFile** – WAV/FLAC I/O with explicit bit-depth control

If some optional dependencies are missing, certain features (e.g. pitch-shifted clouds) may be disabled, but the engine will try to degrade gracefully.

Exports are 44.1 kHz WAVs, suitable for:

* Roland TR-8S / TR-6S,
* other hardware samplers,
* DAWs and software samplers.

---

## License

See `LICENSE` in this repository for full terms.

In short: you’re free to use `afterglow-engine` in your own workflows and projects. There is no warranty; you are responsible for how you deploy it and for any third-party audio you process with it.
