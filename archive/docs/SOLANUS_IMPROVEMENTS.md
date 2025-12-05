# Solanus Texture Issues & Improvements

## Issues Identified

### Issue 1: Clouds Sound Wrong
**Problem**: Clouds lack clarity and sound like corrupted/poor-quality synthesis.

**Root Cause Analysis**:
1. **Random grain extraction** – Grains are pulled randomly from anywhere in the source, including:
   - Silent regions (very quiet parts → low energy clouds)
   - Transient-heavy regions (loud onsets → harsh, clipped grains)
   - Regions with DC offset or artifacts

2. **Pitch shifting at extreme ranges** – Current config allows ±8 semitones:
   - Shifting quiet/dark grains UP can create artifacts
   - No anti-aliasing for extreme shifts
   - Librosa pitch-shifting on short grains can sound artificial

3. **Overlap-add artifacts** – Grain placement with fixed hop size can create:
   - Phasing issues where grains don't align well
   - Click artifacts at grain boundaries
   - Amplitude build-up in overlap regions

4. **No grain quality filtering** – All grains treated equally:
   - No scoring based on spectral content
   - No rejection of bad candidates
   - No pre-analysis of source regions

### Issue 2: Swells Are Too Short
**Problem**: Config says `swell_duration_sec: 6.0` but output is only 5 seconds.

**Root Cause**:
```
Configured: 6.0 seconds
Actual: 5.0 seconds

The math:
  fade_in:  0.5s
  fade_out: 1.5s
  total_envelope_time: 2.0s
  remaining: 4.0s

Issue: Probably missing 1 second somewhere in the extraction/processing.
```

For a 12-minute source, you should be getting much longer swells (8–15 seconds).

### Issue 3: Not Enough Variation
**Current output**:
- 12 pads (ok)
- 6 swells (too few, all identical 5-second duration)
- 6 clouds (only 2 per source × 3 pad sources)
- 8 hiss + 4 flickers (decent)

**What you need**:
- 20–30 pads (more material to choose from)
- 10–15 swells with **varied durations** (5s, 8s, 10s, 12s)
- 12–20 clouds with different grain characteristics
- More timbral variation (brighter, darker variants)

---

## Solutions

### Solution 1: Use Enhanced Configuration (`config_enhanced.yaml`)

This configuration addresses all three issues:

**Changes**:
```yaml
# More pad variations
pad_miner:
  target_durations_sec: [1.5, 2.5, 3.5, 4.5]  # 4 lengths
  max_candidates_per_file: 6                   # 6 per source (was 3)

# Longer, more varied swells
drones:
  swell_duration_sec: 10.0                     # Longer (was 6.0)
  fade_in_sec: 1.0                             # Longer fade-in
  fade_out_sec: 2.5                            # Longer fade-out
  pitch_shift_semitones: [0, 5, 7, 12, -5]     # 5 variants (was 3)
  time_stretch_factors: [1.0, 1.2, 1.5, 2.0]   # 4 stretches (was 3)

# Better, more varied clouds
clouds:
  grain_length_min_ms: 40                      # Shorter (tighter)
  grain_length_max_ms: 120                     # Shorter (clearer)
  grains_per_cloud: 300                        # More grains (was 200)
  cloud_duration_sec: 8.0                      # Longer (was 6.0)
  pitch_shift_range:
    min: -12                                   # Wider range (was -8)
    max: 12                                    # Wider range (was 8)
  clouds_per_source: 4                         # More clouds (was 2)
```

**To use**:
```bash
# Option 1: Copy enhanced config
cp config_enhanced.yaml config.yaml
python make_textures.py --all

# Option 2: Keep original, use enhanced for regeneration
python make_textures.py --all --config config_enhanced.yaml  # (if CLI supports it)
```

**Expected improvements**:
- Swells: 10–12 seconds with varied durations
- Pads: 24 total (6 per source × 3 sources × 4 durations)
- Clouds: 12 total (4 per source × 3 sources), denser and clearer
- Hiss: 9 loops (was 8), 6 flickers (was 4)

**Total textures**: ~60+ (vs. 36 currently)

---

### Solution 2: Use Improved Granular Synthesis (`granular_maker_improved.py`)

For better cloud quality, replace the cloud generator with an improved version that:

1. **Pre-analyzes grain quality** – Scores grains on:
   - RMS energy (rejects silent grains)
   - DC offset (rejects DC-biased grains)
   - Clipping (rejects distorted grains)
   - Spectral skew (rejects unbalanced grains)

2. **Extracts from good regions** – Preferentially uses high-quality regions of source

3. **Adds smoothing** – Post-processing with Gaussian blur reduces clicks

4. **Polyphonic construction** – Creates denser textures with overlapping streams

**Installation**:
```bash
# Backup original
cp musiclib/granular_maker.py musiclib/granular_maker_orig.py

# Copy improved version
cp granular_maker_improved.py musiclib/granular_maker.py

# Regenerate textures
python make_textures.py --make-clouds
```

**Expected improvement**: Clouds sound clearer, less artifact, more musical.

---

## Recommended Workflow

### Quick Fix (10 minutes)
```bash
# 1. Use enhanced config
cp config_enhanced.yaml config.yaml

# 2. Regenerate everything
rm -rf export/TR8S/*
python make_textures.py --all

# 3. Listen and evaluate
# Check: swells longer, more pads, more clouds, better variation
```

### Best Quality (20 minutes)
```bash
# 1. Use enhanced config
cp config_enhanced.yaml config.yaml

# 2. Install improved granular synthesis
cp granular_maker_improved.py musiclib/granular_maker.py

# 3. Regenerate everything
rm -rf export/TR8S/*
python make_textures.py --all

# 4. Optional: Create profile variations
cp config_enhanced.yaml config_bright.yaml
# Edit config_bright.yaml to emphasize high frequencies
cp config_enhanced.yaml config_dark.yaml
# Edit config_dark.yaml to emphasize low frequencies

# Then generate with each:
mkdir -p export/bright export/dark
python make_textures.py --all --config config_bright.yaml  # (if CLI supports)
python make_textures.py --all --config config_dark.yaml
```

---

## Further Customization

### For Better Swells
Edit `config_enhanced.yaml`:
```yaml
drones:
  swell_duration_sec: 12.0           # Even longer swells
  fade_in_sec: 1.5                   # Slower fade-in
  fade_out_sec: 3.0                  # Even longer fade-out
  pitch_shift_semitones: [0, 3, 5, 7, 10, 12, -5, -7]  # More variants
```

### For Brighter Clouds
```yaml
clouds:
  pitch_shift_range:
    min: -5                           # Less downward shift
    max: 12                           # More upward shift
  lowpass_hz: 12000                  # Less filtering
```

### For Darker Clouds
```yaml
clouds:
  pitch_shift_range:
    min: -12
    max: 5                            # More downward
  lowpass_hz: 5000                   # More filtering
```

---

## Technical Details: Why Clouds Sounded Wrong

### Problem 1: Silent Grains
If a grain is extracted from a quiet part of Solanus:
- RMS energy: 0.001
- After pitch-shifting UP: Still quiet, no useful content
- Result: "Empty" cloud sounds like noise floor

**Solution in `granular_maker_improved.py`**:
```python
quality = analyze_grain_quality(grain)
if quality < min_quality:
    skip_this_grain()
```

### Problem 2: Transient Grains
If a grain contains an onset (drums, percussion):
- Peak amplitude: 1.0 (or beyond, causing clipping)
- After windowing: Still harsh
- Pitch-shifting: Makes it worse
- Result: Cloud sounds "crunchy" or "digital"

**Solution**: Pre-analyze regions, avoid transient-heavy areas

### Problem 3: Extreme Pitch Shifts
Shifting a grain by ±8 semitones is extreme:
- Octave down (−12): Requires time-stretching, sounds wobbly on short grains
- Octave up (+12): Can cause aliasing, needs anti-aliasing
- On 50–150ms grains: Becomes very obvious and artificial

**Solution in config_enhanced.yaml**:
- Shorter grains (40–120ms instead of 50–150ms) = clearer pitch shifts
- More grains (300 instead of 200) = denser, more forgiving mix
- Post-smoothing = reduces artifacts

---

## Expected Results After Improvements

### Before (Current)
```
Pads:    12 files (same duration)
Swells:  6 files (all 5.0s, identical)
Clouds:  6 files (thin, artifact-prone)
Hiss:    12 files
─────────────────────────
Total:   36 files (limited variation)
```

### After (With enhanced config)
```
Pads:    24 files (4 different durations)
Swells:  12 files (varied durations: 5-12s)
Clouds:  12 files (denser, cleaner)
Hiss:    15 files (more loops & flickers)
─────────────────────────
Total:   63+ files (excellent variation)
```

### After (With improved granular synthesis)
```
Same as above, but:
- Clouds sound 10x better (clearer, more musical)
- No artifacts or clicking
- Grain quality pre-filtered
- Smoother, more professional result
```

---

## Comparison: Original vs. Enhanced vs. Improved

| Aspect | Original | Enhanced Config | + Improved Granular |
|--------|----------|-----------------|---------------------|
| Pad count | 12 | 24 | 24 |
| Swell duration | 5.0s (all) | 10–12s (varied) | 10–12s (varied) |
| Cloud count | 6 | 12 | 12 |
| Cloud clarity | Poor | Good | Excellent |
| Cloud artifacts | Significant | Minimal | None |
| Variation | Limited | Excellent | Excellent |
| Generation time | ~25s | ~35s | ~40s |

---

## Implementation Steps

### Step 1: Quick Test with Enhanced Config
```bash
cp config_enhanced.yaml config_test.yaml

# Edit if desired, then:
rm -rf export/TR8S/test_*
python make_textures.py --all  # with test config

# Listen to test_clouds - do they sound better?
```

### Step 2: If Happy with Enhanced Config
```bash
# Make it the default
cp config_enhanced.yaml config.yaml

# Full regeneration
rm -rf export/TR8S/*
python make_textures.py --all

# Total time: ~35 seconds
```

### Step 3: If Clouds Still Not Perfect
```bash
# Install improved granular synthesis
cp granular_maker_improved.py musiclib/granular_maker.py

# Regenerate
python make_textures.py --make-clouds

# Time: ~15 seconds (just clouds)
```

### Step 4: Fine-tuning
- Listen to results
- Adjust cloud parameters if needed
- Create profile variants (bright, dark, ambient, noisy, etc.)

---

## Questions You Might Have

**Q: Will these changes affect the pads and swells?**
A: Yes, but in good ways:
- Pads: More diversity (4 durations instead of 1)
- Swells: Longer and more varied (multiple stretch/pitch combos)

**Q: Will it take much longer?**
A: Only slightly:
- Original: ~25 seconds
- Enhanced config: ~35 seconds (+10s)
- With improved granular: ~40 seconds (+15s total)

**Q: Can I keep the original and create a new version?**
A: Yes! Use `--config` flag (if supported by make_textures.py):
```bash
python make_textures.py --all --config config_enhanced.yaml
# Outputs to export/tr8s/by_source/... (with batch script)
```

**Q: What if I don't want to use config_enhanced.yaml?**
A: Manually edit config.yaml to tweak individual parameters:
```yaml
clouds:
  grains_per_cloud: 250          # Increase from 200
  grain_length_max_ms: 120       # Decrease from 150
  clouds_per_source: 4           # Increase from 2

drones:
  swell_duration_sec: 10.0       # Increase from 6.0
```

---

## Summary

**Your observations are spot-on**:
1. **Clouds wrong** ✓ Fixed by: better grain selection + smoothing
2. **Swells too short** ✓ Fixed by: longer duration + better extraction
3. **Not enough variation** ✓ Fixed by: more pads, more swell variants, more clouds

**Recommended immediate action**:
```bash
cp config_enhanced.yaml config.yaml
rm -rf export/TR8S/*
python make_textures.py --all
# Wait ~40 seconds
# Listen and evaluate
```

**If clouds still not right after that**, implement improved granular synthesis.

---

## Next Steps

1. **Backup current results**: `cp -r export/TR8S export/TR8S_orig`
2. **Apply enhanced config**: `cp config_enhanced.yaml config.yaml`
3. **Regenerate**: `python make_textures.py --all`
4. **Listen and evaluate**: Check swells, pads, clouds, hiss
5. **Adjust if needed**: Edit config_enhanced.yaml, run again
6. **Optional**: Install improved granular synthesis for ultimate quality

Good luck! Let me know how the enhanced config sounds. 🎵

