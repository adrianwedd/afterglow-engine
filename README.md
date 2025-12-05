# Music Texture Tool

A Python-based tool for preparing sound-design material for electronic music workflows (specifically for the Roland TR-8S). Creates loopable pads, evolving swells, granular clouds, and high-frequency textures from your existing audio and synthesis.

## Features

- **Pad Mining**: Automatically extract short, loopable pad segments from existing audio files
- **Drone Generation**: Time-stretch, pitch-shift, and process audio into pad loops and swells with tonal variants (warm, airy, dark)
- **Granular Clouds**: Turn any audio into abstract, evolving textures using granular synthesis
- **Hiss & Air**: Generate high-frequency layers and flicker bursts from drums or synthetic noise

All outputs are optimized for TR-8S import (44.1 kHz, 24-bit or 16-bit WAV).

## Setup

### Prerequisites

- Python 3.8+
- macOS or Linux

### Installation

```bash
cd ~/repos/music
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
.
├── config.yaml                   # Configuration (auto-generated on first run)
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── make_textures.py              # Main CLI entrypoint
├── musiclib/                     # Python package
│   ├── __init__.py
│   ├── io_utils.py               # File discovery, loading, saving
│   ├── segment_miner.py          # Pad mining from sustained segments
│   ├── drone_maker.py            # Pad loops & swells with variants
│   ├── granular_maker.py         # Granular cloud generator
│   ├── hiss_maker.py             # Hiss loops & flicker bursts
│   └── dsp_utils.py              # Filters, envelopes, normalization
├── source_audio/                 # Drop your audio files here
├── pad_sources/                  # Hand-picked tonal material (optional)
├── drums/                        # Percussive material for hiss (optional)
└── export/
    └── tr8s/
        ├── pads/                 # Loopable pad outputs
        ├── swells/               # Swell one-shots
        ├── clouds/               # Granular textures
        └── hiss/                 # Hiss loops & flickers
```

## Usage

### One Command: Generate Everything

```bash
python make_textures.py --all
```

### Individual Steps

```bash
# Extract short pads from sustained regions of existing audio
python make_textures.py --mine-pads

# Generate tonal pad loops and swells with variants
python make_textures.py --make-drones

# Create granular cloud textures
python make_textures.py --make-clouds

# Generate hiss loops and flicker bursts
python make_textures.py --make-hiss
```

### View Help

```bash
python make_textures.py --help
```

## Configuration

On first run, a default `config.yaml` is created with commented values. Customize it to adjust:

- **Sample rate & bit depth** (global)
- **Pad mining thresholds** (RMS, onset rate, duration, multiple target durations, loop crossfade)
- **Drone processing** (pitch shifts, time-stretch, filter variants)
- **Cloud granular parameters** (grain length, count, pitch variation range)
- **Hiss settings** (band-pass frequency range, modulation, synthetic noise)
- **Export options** (stereo vs mono per category)
- **Brightness tagging** (spectral centroid-based dark/mid/bright classification)

See `config.yaml` for all tunable parameters with inline documentation.

### New Features (v0.2)

**Multiple Pad Durations**: `pad_miner.target_durations_sec` now accepts a list (e.g., `[2.0, 3.5]`), allowing pads of different lengths to be extracted from the same source.

**Configurable Loop Crossfade**: `pad_miner.loop_crossfade_ms` controls the crossfade length used to create seamless pad loops.

**Per-Category Stereo/Mono Export**:
- `export.pads_stereo`, `export.swells_stereo`, `export.clouds_stereo`, `export.hiss_stereo`
- Set to `true` to preserve or create stereo versions of textures

**Configurable Granular Pitch Range**: `clouds.pitch_shift_range` with `min` and `max` (in semitones) replaces the old single `max_pitch_shift_semitones`.

**Configurable Hiss Band-Pass Frequencies**:
- `hiss.bandpass_low_hz` and `hiss.bandpass_high_hz` let you adjust the high-frequency range for hiss loops and flickers.

**Brightness Tagging**: Filenames now include `_dark`, `_mid`, or `_bright` tags based on spectral centroid analysis (for pads and clouds).
- Control via `brightness_tags.enabled`, `centroid_low_hz`, `centroid_high_hz`

## Workflow

### 1. Prepare Your Audio

Place audio files in the appropriate directories:

- `source_audio/` → Material to scan for extractable pads
- `pad_sources/` → Hand-picked tonal samples for drone processing
- `drums/` → Percussive material for hiss extraction (optional; synthetic noise used as fallback)

Supported formats: WAV, AIFF, FLAC

### 2. Run the Pipeline

```bash
python make_textures.py --all
```

The tool will:
1. Mine sustained segments from `source_audio/` → `export/tr8s/pads/`
2. Process `pad_sources/` into variants → `export/tr8s/pads/` & `export/tr8s/swells/`
3. Generate granular clouds → `export/tr8s/clouds/`
4. Create hiss textures → `export/tr8s/hiss/`

### 3. Import to TR-8S

Copy files from `export/tr8s/` to your TR-8S SD card sample folder:

```bash
cp -r export/tr8s/* /Volumes/TR8S/SAMPLES/
```

(Adjust path to match your TR-8S mount point)

## Output Naming

- **Pads**: `<sourceName>_pad01.wav`, `<sourceName>_pad_warm.wav`, etc.
- **Swells**: `<sourceName>_swell01.wav`, etc.
- **Clouds**: `cloud_<sourceName>_01.wav`, etc.
- **Hiss**: `hiss_loop_01.wav`, `hiss_flicker_01.wav`, etc.

## Audio Format

All outputs:
- **Sample rate**: 44,100 Hz (TR-8S standard)
- **Bit depth**: 24-bit or 16-bit (configurable)
- **Format**: Mono or stereo WAV
- **Normalization**: Peak level ~-1 dBFS

## Tips & Tricks

- **Faster Processing**: Run individual steps (`--mine-pads`, `--make-drones`, etc.) as needed rather than `--all`
- **Adjust Sensitivity**: Tweak thresholds in `config.yaml` (RMS range, onset rate, etc.) to get better pad candidates
- **Experiment with Variants**: Time-stretch factors and pitch shifts in config multiply the output variations
- **Layer Textures**: Combine pads + clouds + hiss in your TR-8S sampler for rich, evolving soundscapes

## Troubleshooting

**"No audio files found"**: Ensure files are in the correct directories and use supported formats (WAV, AIFF, FLAC).

**"Config not found, creating default"**: Normal on first run. Customize `config.yaml` and re-run.

**"Output is too quiet/loud"**: Adjust `global.target_peak_dbfs` in `config.yaml`.

**"Pads don't loop smoothly"**: Increase `pad_miner.crossfade_ms` in config.

## Technical Details

- **Librosa**: Audio loading, time-stretching, pitch-shifting, onset detection
- **NumPy**: Windowing, signal processing, grain manipulation
- **SciPy**: IIR/FIR filters for tonal variants and DSP
- **Soundfile**: WAV output with full bit-depth control

## License

Use this tool freely for your own sound design workflows.
