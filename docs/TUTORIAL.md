# Getting Started: Your First Extraction

*A 15-minute guide to mining textures from your audio archive.*

---

## Prerequisites

You'll need:
- Python 3.11+ installed
- A source audio file (any format: WAV, MP3, FLAC)
- 10-15 minutes

---

## Part 1: Installation (3 minutes)

### 1. Clone and Setup

```bash
git clone https://github.com/adrianwedd/afterglow-engine.git
cd afterglow-engine

# Create virtual environment
python -m venv venv311
source venv311/bin/activate  # Windows: venv311\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python make_textures.py --help
```

You should see the usage guide. If you get errors, check that Python 3.11+ is active.

---

## Part 2: First Extraction (5 minutes)

### 1. Add Source Material

Place an audio file in `source_audio/`:

```bash
# Example: copy a track from your music library
cp ~/Music/ambient_track.wav source_audio/
```

**What to use:**
- ✅ Ambient/drone tracks with sustained sections
- ✅ Film scores with long tones
- ✅ Synthesizer pads or organ chords
- ❌ Percussion-only tracks (no sustained material)
- ❌ Spoken word (too transient)

### 2. Preview What Will Be Generated

```bash
python make_textures.py --mine-pads --dry-run
```

Output shows estimated file count:
```
[MINE PADS]
  Source directory: source_audio
  Audio files found: 1
  Max candidates per file: 3
  → Estimated pads: ~3
```

### 3. Run Your First Extraction

```bash
python make_textures.py --mine-pads
```

Watch the progress bar as the engine mines:
```
[PAD MINER] Processing 1 file(s)...
Mining pads: 100%|███████████████████| 1/1 [00:08<00:00]
  Processing: ambient_track
    → Found 3 pad candidate(s)
    ✓ ambient_track_pad01_mid.wav
    ✓ ambient_track_pad02_bright.wav
    ✓ ambient_track_pad03_dark.wav
```

### 4. Find Your Textures

```bash
ls export/tr8s/ambient_track/pads/
```

Output:
```
ambient_track_pad01_mid.wav
ambient_track_pad02_bright.wav
ambient_track_pad03_dark.wav
```

**🎉 You've extracted your first textures!**

Load them into your sampler or DAW and explore.

---

## Part 3: Understanding What Happened (3 minutes)

### The Mining Process

1. **Scanning**: The engine slides a 2.5s window across your audio
2. **Filtering**: Rejects regions that are:
   - Too quiet (< -40 dB)
   - Too loud (> -10 dB, likely clipping)
   - Too percussive (> 3 onsets/second)
   - Too noisy (spectral flatness > 0.5)
3. **Ranking**: Scores candidates by stability and tonality
4. **Extraction**: Takes top 3 and makes them loop-ready
5. **Tagging**: Classifies brightness (dark/mid/bright)

### The Files

Each pad is:
- **2.5 seconds** long (configurable)
- **Loopable** (smooth 100ms crossfade)
- **Normalized** to -1.0 dBFS
- **Tagged** by brightness (centroid-based)
- **44.1kHz, 24-bit** (TR-8S compatible)

---

## Part 4: Next Steps (4 minutes)

### Generate Clouds

Clouds are evolving granular textures built from your pads.

```bash
# Add a pad to pad_sources/
cp export/tr8s/ambient_track/pads/ambient_track_pad01_mid.wav pad_sources/

# Generate clouds
python make_textures.py --make-clouds
```

Output: 2 clouds per source, 6 seconds each, 200 grains with random pitch shifts.

Find them in: `export/tr8s/ambient_track_pad01_mid/clouds/`

### Try Different Presets

Want faster iteration? Use the **fast_sketch** preset:

```bash
python make_textures.py --config examples/presets/config_fast_sketch.yaml --mine-pads
```

Want dense, cinematic textures? Try **dense_clouds**:

```bash
python make_textures.py --config examples/presets/config_dense_clouds.yaml --make-clouds
```

See `examples/presets/README.md` for all 4 presets.

### Customize Your Extraction

Edit `config.yaml` to tune the process:

```yaml
pad_miner:
  target_durations_sec: [1.5, 2.5, 3.5]  # Extract multiple lengths
  max_candidates_per_file: 6            # Get more pads
  spectral_flatness_threshold: 0.3      # Stricter tonality

clouds:
  grains_per_cloud: 400                 # Denser clouds
  pitch_shift_range:
    min: -12                            # Wider pitch variation
    max: 12
```

---

## Common Issues

### "No audio files found"

Make sure your files are in the right directory:
```bash
ls source_audio/  # Should show your .wav/.mp3/.flac files
```

### "No sustained segments found"

Your source might be too percussive. Try:
1. Use a different track with longer tones
2. Relax the filters in `config.yaml`:
   ```yaml
   pad_miner:
     max_onset_rate_per_second: 5.0    # Allow more transients
     spectral_flatness_threshold: 0.7  # Accept less tonal material
   ```

### Processing is slow

Use the fast preset or disable pre-analysis:
```yaml
pre_analysis:
  enabled: false
```

Or reduce grain count:
```yaml
clouds:
  grains_per_cloud: 100
```

---

## What to Try Next

1. **Explore the presets**: `examples/presets/` has 4 optimized workflows
2. **Read the config guide**: `docs/CONFIG_QUICK_REFERENCE.md` explains every parameter
3. **Check performance**: `python tests/profile_performance.py` to see benchmarks
4. **Generate drones**: `--make-drones` creates pitch-shifted pad variations
5. **Generate hiss**: `--make-hiss` extracts high-frequency textures from drums

---

## Tips for Better Results

### Source Material Selection

**Great sources:**
- Reverb tails and room tone
- Synthesizer pad layers
- String sections (held notes)
- Organ drones
- Guitar feedback
- Field recordings (ocean, wind, machinery)

**Poor sources:**
- Solo drums (too transient)
- Spoken voice (no sustained tones)
- Heavily compressed EDM (flatness filters reject it)

### Workflow Tips

1. **Start with dry-run**: Always preview before generating
2. **Use presets for exploration**: Try different workflows quickly
3. **Listen before processing further**: Not all pads make good clouds
4. **Keep source files organized**: One album per `source_audio/` run
5. **Archive your configs**: Save `config.yaml` with each batch

### Musical Integration

- **Pads**: Use as looping layers, bed textures, transitions
- **Clouds**: Evolving atmospheres, risers, textural movement
- **Drones**: Bass foundations, harmonic beds, pad stacks
- **Hiss**: Air, breath, high-frequency glue

---

## Next: Deep Dive

Ready to go deeper? Read:
- `CONFIG_QUICK_REFERENCE.md` - Parameter reference
- `PERFORMANCE.md` - Optimization guide
- `CHANGELOG.md` - Feature history
- `examples/presets/README.md` - Preset workflows

The machine is yours. Begin your archaeology.
