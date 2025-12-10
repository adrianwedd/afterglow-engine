# Configuration Presets Gallery

This directory contains example configuration files optimized for specific use cases and workflows. Each preset is tuned for different source material characteristics and output goals.

---

## Quick Reference

| Preset | Best For | Speed | Output Volume | Key Features |
|--------|----------|-------|---------------|--------------|
| `config_minimal.yaml` | Learning, customization | Normal | Low | Conservative defaults, single variants |
| `config_fast_sketch.yaml` | Quick testing, iteration | ⚡ Fast | Low | Minimal processing, 16-bit output |
| `config_dense_clouds.yaml` | Granular textures | Slow | High | 600 grains/cloud, wide pitch range |
| `config_impossible.yaml` | Tonal/harmonic material | Very Slow | Very High | 12 pads/file, 8 durations, fixed seed |

---

## Detailed Preset Descriptions

### `config_minimal.yaml`
**🎯 Perfect for: First-time users, learning the system, starting point for customization**

A bare-bones configuration with conservative defaults:
- Single duration pads (2.5s)
- No pitch shifting or time stretching
- Basic cloud settings (200 grains, 6s duration)
- Pre-analysis disabled
- No stereo or brightness tagging

**Use when:**
- Learning how the engine works
- Creating a custom configuration from scratch
- Processing unknown source material
- Want predictable, minimal output

**Output:** ~5-10 files per source (pads + basic clouds)

---

### `config_fast_sketch.yaml`
**⚡ Perfect for: Rapid prototyping, testing source material, quick iteration**

Optimized for speed (~60% faster than default):
- 16-bit output for faster I/O
- Only 2 pads per file
- Single pad variant (warm)
- No pitch shifting in clouds (major speedup)
- Pre-analysis disabled
- Minimal variations (2 pitch shifts × 2 stretches)

**Use when:**
- Testing if source material is suitable
- Exploring multiple sources quickly
- Sketching ideas without waiting
- Need immediate feedback

**Output:** ~6-8 files per source
**Speed improvement:** ~60% faster than default config

---

### `config_dense_clouds.yaml`
**🌌 Perfect for: Cinematic textures, ambient beds, immersive soundscapes**

Optimized for rich, evolving granular clouds:
- **600 grains per cloud** (2× typical density)
- 12-second clouds for long evolution
- Wide pitch range (-12 to +12 semitones)
- High grain quality filtering (threshold 0.65)
- 6 clouds per source for variety
- Stereo clouds for spatial width
- Conservative normalization (-6dB) to prevent saturation

**Use when:**
- Creating lush ambient textures
- Processing pad sources with rich harmonic content
- Need long, evolving soundscapes
- Want maximum granular variation

**Output:** ~8-12 files per source (focus on clouds)
**Processing time:** Slow (high grain count)

---

### `config_impossible.yaml`
**🎼 Perfect for: Highly tonal/harmonic material, maximum extraction variety**

Tuned for extracting maximum material from rich, sustained sources:
- **12 pads per file** with **8 different durations** (1.5s to 8s)
- Aggressive pitch/time variations (8 shifts × 6 stretches = 48 drone variants)
- Long swells (12s duration) with dramatic fades
- Strict tonality filtering (spectral flatness < 0.3)
- Dense pre-analysis for grain quality
- **Fixed random seed (42)** for reproducible results

**Use when:**
- Processing ambient/drone/film score material
- Source has clear sustained tones and rich harmonics
- Want maximum extraction variety from a single track
- Need reproducible grain placement

**Characteristics suited for:**
- Wide dynamic range (60+ dB)
- High harmonic content (>90% tonal)
- Rich sustained sections
- Complex layered textures

**Output:** 100+ files per source
**Processing time:** Very slow (exhaustive extraction)

---

## Usage

### Option 1: Copy to Project Root

```bash
# Copy a preset to become your active config
cp examples/presets/config_fast_sketch.yaml config.yaml
```

### Option 2: Reference Directly

```bash
# Use a preset without overwriting config.yaml
python make_textures.py --config examples/presets/config_dense_clouds.yaml --all
```

### Option 3: Preview Before Running

```bash
# Dry-run to see what would be generated
python make_textures.py --config examples/presets/config_impossible.yaml --all --dry-run
```

---

## Creating Your Own Presets

1. **Start with a base:**
   ```bash
   cp examples/presets/config_minimal.yaml my_preset.yaml
   ```

2. **Tune parameters:**
   - Adjust `grains_per_cloud` for density
   - Change `pitch_shift_range` for harmonic variation
   - Set `target_durations_sec` for different pad lengths
   - Enable/disable `pre_analysis` for quality vs speed

3. **Document your settings:**
   - Add comments explaining why each parameter was chosen
   - Note the source material characteristics it's optimized for
   - Include expected output counts and processing time

4. **Save and share:**
   ```bash
   mv my_preset.yaml examples/presets/config_my_preset.yaml
   ```

5. **Add to this README** with a description

---

## Parameter Decision Guide

### When to Enable Pre-Analysis

✅ **Enable** (`enabled: true`) when:
- Source has mixed quiet/loud regions
- Want highest grain quality
- Processing precious/limited source material
- Don't mind slower processing

❌ **Disable** (`enabled: false`) when:
- Source is already clean and consistent
- Need fast iteration
- Processing many files in batch
- Source is synthetic/generated

### Grain Count Guidelines

- **150-200 grains:** Sparse, pointillistic textures
- **200-400 grains:** Standard, balanced density
- **400-600 grains:** Dense, evolving clouds
- **600+ grains:** Maximum density (slow, saturated)

### Pitch Shift Range Trade-offs

- **0 to 0:** No shifting (fastest, preserves original tonality)
- **-5 to 5:** Subtle variation (natural, stays close to source)
- **-7 to 7:** Moderate variation (default, good balance)
- **-12 to 12:** Wide variation (harmonic richness, longer processing)

---

## Preset Compatibility

All presets are compatible with **afterglow-engine v0.8.0+** and support:
- Multiple target durations
- Pre-analysis filtering
- Equal-power crossfades
- Brightness tagging
- Musical key detection/transposition
- Batch curation with auto-delete

Older versions may not support all features.

---

## Troubleshooting

**"No candidates found" errors:**
- Try `config_minimal.yaml` with relaxed filters
- Check that source material has sustained regions
- Reduce `spectral_flatness_threshold` to accept less tonal material

**Processing too slow:**
- Use `config_fast_sketch.yaml` for speed
- Disable pre-analysis
- Reduce `grains_per_cloud`
- Set `pitch_shift_range` to 0

**Not enough output:**
- Increase `max_candidates_per_file`
- Add more `target_durations_sec`
- Increase `clouds_per_source`
- Lower quality thresholds

**Too much output:**
- Reduce `max_candidates_per_file`
- Use single `target_durations_sec`
- Enable `auto_delete_grade_f: true`
- Reduce drone/cloud variations
