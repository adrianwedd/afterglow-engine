# Configuration Presets

This directory contains example configuration files optimized for specific use cases.

## Available Presets

### `config_impossible.yaml`
**Optimized for highly tonal, harmonically rich material**

This preset is tuned for extracting maximum material from tracks with:
- Wide dynamic range (60+ dB)
- High harmonic content (>90% tonal)
- Rich sustained sections
- Complex layered textures

**Key features:**
- Extracts 12 pads per file with 8 different durations
- Aggressive pitch/time variations (8 pitch shifts × 6 time stretches)
- Long swells (12s duration) with dramatic fades
- Strict tonality filtering (spectral flatness < 0.3)
- Dense pre-analysis for grain quality
- Fixed random seed (42) for reproducible results

**Use when:**
- Processing ambient/drone/film score material
- Source has clear sustained tones and rich harmonics
- You want maximum extraction variety from a single track

## Usage

Copy a preset to the project root as `config.yaml`:

```bash
cp examples/presets/config_impossible.yaml config.yaml
```

Or reference it directly:

```bash
python make_textures.py --config examples/presets/config_impossible.yaml --all
```

## Creating Your Own Presets

1. Start with `config.yaml` (the default)
2. Tune parameters for your source material
3. Document track characteristics in comments
4. Save as `config_[name].yaml` in this directory
5. Add description to this README
