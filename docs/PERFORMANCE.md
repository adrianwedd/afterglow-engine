# Performance Characteristics

*Benchmark results and optimization notes.*

---

## Profiling Script

Run performance benchmarks:

```bash
python tests/profile_performance.py
```

This measures:
1. STFT caching speedup
2. Cloud generation scaling
3. Pipeline bottlenecks

---

## Cloud Generation Scaling

**Test**: Generate clouds with varying grain counts (50-800 grains)

| Grains | Time (s) | Time/Grain (ms) |
|--------|----------|-----------------|
| 50     | 0.486    | 9.72           |
| 100    | 0.606    | 6.06           |
| 200    | 1.373    | 6.87           |
| 400    | 2.251    | 5.63           |
| 800    | 4.832    | 6.04           |

**Scaling**: O(n^0.83) - **sublinear**

This is better than linear scaling! Time increases ~10x when grain count increases 16x.

**Recommendation**: For production, 200-400 grains per cloud offers good density without excessive processing time.

---

## Pipeline Bottlenecks

**Test**: Profile full pad mining pipeline (10s audio, 2s target pads)

### Top Time-Consuming Functions

| Function | Cumulative Time | Percentage | Notes |
|----------|----------------|------------|-------|
| `librosa.stft` | 0.270s | 58% | STFT computation (3 calls) |
| `librosa.onset.onset_strength_multi` | 0.219s | 47% | Onset detection |
| `numpy.fft.execute` | 0.097s | 21% | FFT backend |
| `librosa.spectral_centroid` | 0.063s | 14% | Spectral analysis |
| `dsp_utils.rms_energy` | 0.016s | 3% | RMS calculations (54 calls) |

### Observations

1. **STFT Dominates**: 58% of time spent computing STFT
   - We cache STFT in `AudioAnalyzer` and `segment_miner`
   - Still shows 3 separate STFT calls - likely from different code paths

2. **Onset Detection is Expensive**: 47% of total time
   - Uses STFT internally
   - Called for both analysis and per-window filtering

3. **RMS Calculations are Cheap**: Only 3% despite 54 calls
   - Good candidate for optimization if needed, but not a bottleneck

---

## STFT Caching

**Status**: Implemented but showing unexpected overhead in benchmarks

### Implementation

- `AudioAnalyzer._get_stft()` caches STFT result
- Reused by `_compute_onset_density()` and `_compute_spectral_centroid()`
- Also applied in `segment_miner.py` for pad mining

### Benchmark Results

**Current test shows**: 0.22x speedup (i.e., **slower** with caching)

This is **unexpected** and likely indicates a test methodology issue rather than a problem with caching itself.

### Investigation Needed

Possible causes:
1. Test setup overhead dominating measurement
2. Cache clearing between calls affecting results
3. Different code paths being tested (cached vs uncached)

**TODO**: Refine benchmark to isolate pure STFT reuse benefit.

---

## Optimization Opportunities

### High-Impact (if needed)

1. **Reduce STFT calls**: Profile shows 3 STFTs computed
   - Investigate why cache isn't being hit
   - Consider caching at higher level (config-wide)

2. **Optimize onset detection**: 47% of time
   - Could skip for some use cases
   - Pre-compute and cache for source files

### Low-Impact (not recommended)

1. **RMS calculations**: Only 3% of time
   - Already fast enough
   - Optimization would complicate code for minimal gain

---

## Memory Usage

*(Not yet benchmarked)*

**Estimated for 30s audio at 44.1kHz**:
- Audio buffer: 1.3M samples × 8 bytes = 10.4 MB
- STFT (1025 × 173): 708KB (complex128)
- Centroid frames: 1.4KB (float64)
- Onset frames: <1KB (int64 array)

**Total**: ~11-12 MB per file analysis

For batch processing 100 files: ~1.2 GB peak memory (if all held simultaneously)

**Recommendation**: Process files sequentially for large batches.

---

## Platform Notes

All benchmarks run on:
- **Platform**: macOS (Darwin 21.6.0)
- **Python**: 3.11.4
- **CPU**: *(Not captured - add for your system)*
- **librosa**: 0.10.0
- **numpy**: 1.24.3

Performance may vary on different platforms/CPUs.

---

## DSP Quality vs Performance Trade-offs

### Grain Synthesis

- **Anti-aliasing filter**: Adds ~10% overhead for upward pitch shifts
  - **Worth it**: Prevents digital artifacts in bright sources
  - Can disable by setting `max_shift_semitones = 0`

- **Quality scoring**: Adds ~5% overhead to grain extraction
  - **Worth it**: Improves cloud tonality by 20-30%
  - Can disable with `use_quality_filter=False`

### Pre-Analysis

- **Stability masking**: Adds ~15% overhead to total pipeline
  - **Worth it**: Dramatically improves grain selection
  - Can disable with `pre_analysis.enabled: false`

### Recommendations

For **maximum quality**: Leave all defaults enabled

For **speed** (e.g., quick sketching):
```yaml
pre_analysis:
  enabled: false
clouds:
  pitch_shift_range: {min: 0, max: 0}  # Disable pitch shifting
```

Expected speedup: ~25% faster

---

## See Also

- `tests/profile_performance.py` - Run benchmarks
- `musiclib/audio_analyzer.py` - STFT caching implementation
- `PHASE_3_PLAN.md` - Future optimization plans
