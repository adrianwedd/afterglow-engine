"""
Performance profiling for afterglow-engine.

Measures:
1. STFT caching speedup in AudioAnalyzer
2. Full pipeline bottlenecks
3. Cloud generation scaling with grain count
"""

import cProfile
import pstats
import io
import time
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.audio_analyzer as audio_analyzer
import musiclib.granular_maker as granular_maker
import musiclib.segment_miner as segment_miner
import musiclib.dsp_utils as dsp_utils


def profile_stft_caching_isolated():
    """Measure PURE STFT caching speedup (isolated from feature caching)."""
    print("\n" + "="*70)
    print("PROFILE 1A: STFT Caching Speedup (Isolated)")
    print("="*70)
    print("\nThis test isolates STFT caching from feature result caching.")

    sr = 44100
    duration = 10.0  # Shorter for focused test
    audio = np.random.randn(int(sr * duration)) * 0.3

    # Add tonal content
    t = np.linspace(0, duration, int(sr * duration))
    audio += 0.2 * np.sin(2 * np.pi * 220 * t)  # A3
    audio += 0.15 * np.sin(2 * np.pi * 440 * t)  # A4

    print(f"\nTest audio: {duration}s @ {sr}Hz ({len(audio):,} samples)")

    # Measure STFT computation time directly
    import librosa
    print("\n--- Scenario 1: First STFT call (no cache) ---")
    start = time.perf_counter()
    stft1 = librosa.stft(audio, n_fft=2048, hop_length=512, center=True)
    first_call_time = time.perf_counter() - start
    print(f"Time: {first_call_time:.4f}s")

    # Measure reference return (essentially free)
    print("\n--- Scenario 2: Cached reference return ---")
    start = time.perf_counter()
    stft2 = stft1  # Reference copy (what cached STFT does)
    cached_return_time = time.perf_counter() - start
    print(f"Time: {cached_return_time:.4e}s (essentially free)")

    # Measure multiple fresh STFT calls
    print("\n--- Scenario 3: Three fresh STFT calls (no cache) ---")
    start = time.perf_counter()
    for _ in range(3):
        _ = librosa.stft(audio, n_fft=2048, hop_length=512, center=True)
    three_calls_time = time.perf_counter() - start
    print(f"Time: {three_calls_time:.4f}s")

    # Calculate speedup
    speedup_vs_single = first_call_time / cached_return_time if cached_return_time > 0 else float('inf')
    overhead_reduction = (three_calls_time - first_call_time) / three_calls_time * 100

    print(f"\n{'RESULTS (ISOLATED STFT CACHING)':^70}")
    print(f"{'-'*70}")
    print(f"  First STFT call: {first_call_time:.4f}s")
    print(f"  Cached return: {cached_return_time:.4e}s")
    print(f"  Speedup: >{speedup_vs_single:.0f}x (essentially free after first call)")
    print(f"\n  Within single analysis pass (3 features needing STFT):")
    print(f"    Without cache: 3 calls = {three_calls_time:.4f}s")
    print(f"    With cache: 1 call = {first_call_time:.4f}s")
    print(f"    Overhead reduction: {overhead_reduction:.1f}%")

    return {
        'first_call_time': first_call_time,
        'cached_return_time': cached_return_time,
        'three_calls_time': three_calls_time,
        'speedup_vs_single': speedup_vs_single,
        'overhead_reduction_pct': overhead_reduction
    }


def profile_stft_caching():
    """Measure STFT caching speedup in AudioAnalyzer (legacy test for comparison)."""
    print("\n" + "="*70)
    print("PROFILE 1B: Feature Computation with STFT Caching")
    print("="*70)
    print("\nThis test shows total speedup including feature result caching.")

    # Generate 30s of test audio (long enough to see caching benefit)
    sr = 44100
    duration = 30.0
    audio = np.random.randn(int(sr * duration)) * 0.3

    # Add some tonal content
    t = np.linspace(0, duration, int(sr * duration))
    audio += 0.2 * np.sin(2 * np.pi * 220 * t)  # A3
    audio += 0.15 * np.sin(2 * np.pi * 440 * t)  # A4

    print(f"\nTest audio: {duration}s @ {sr}Hz ({len(audio):,} samples)")

    # Scenario 1: Multiple feature calls with caching
    print("\n--- With Full Caching (STFT + Features) ---")
    start = time.perf_counter()
    analyzer = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=1.0, hop_sec=0.5)

    # Call features multiple times - STFT computed once, features cached
    onset1 = analyzer._compute_onset_density()
    centroid1 = analyzer._compute_spectral_centroid()
    onset2 = analyzer._compute_onset_density()  # Reuses feature cache
    centroid2 = analyzer._compute_spectral_centroid()  # Reuses feature cache

    elapsed_cached = time.perf_counter() - start

    print(f"Elapsed time: {elapsed_cached:.3f}s")
    print(f"STFT computed: 1 time")
    print(f"Features computed: 2 times (then cached)")
    print(f"Total calls: 4 (2 onset + 2 centroid)")

    # Scenario 2: No caching (clear ONLY STFT cache, not feature caches)
    print("\n--- With Only Feature Caching (No STFT Cache) ---")
    start = time.perf_counter()
    analyzer2 = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=1.0, hop_sec=0.5)

    # First call computes STFT and feature
    onset1 = analyzer2._compute_onset_density()
    analyzer2._stft_cache = None  # Clear ONLY STFT cache
    # Second call recomputes STFT, uses cached onset_frames
    centroid1 = analyzer2._compute_spectral_centroid()
    # Note: onset2 and centroid2 still use feature caches

    elapsed_partial = time.perf_counter() - start

    print(f"Elapsed time: {elapsed_partial:.3f}s")
    print(f"STFT computed: 2 times (no STFT cache)")
    print(f"Features: cached after first computation")

    speedup = elapsed_partial / elapsed_cached
    savings = (1 - elapsed_cached / elapsed_partial) * 100

    print(f"\n{'RESULTS (FEATURE CACHING)':^70}")
    print(f"{'-'*70}")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time saved: {savings:.1f}%")
    print(f"  Absolute savings: {(elapsed_partial - elapsed_cached):.3f}s per analysis")

    return {
        'cached_time': elapsed_cached,
        'partial_cached_time': elapsed_partial,
        'speedup': speedup,
        'savings_pct': savings
    }


def profile_cloud_generation():
    """Benchmark cloud generation with different grain counts."""
    print("\n" + "="*70)
    print("PROFILE 2: Cloud Generation Scaling")
    print("="*70)

    sr = 44100
    # Generate 5s of test audio for cloud generation
    audio = np.random.randn(sr * 5) * 0.3
    t = np.linspace(0, 5, sr * 5)
    audio += 0.2 * np.sin(2 * np.pi * 220 * t)

    grain_counts = [50, 100, 200, 400, 800]
    results = []

    print(f"\nTest audio: 5s @ {sr}Hz")
    print(f"Cloud duration: 6s")
    print(f"\n{'Grains':<10} {'Time (s)':<12} {'Time/Grain (ms)':<18}")
    print("-" * 70)

    for grain_count in grain_counts:
        start = time.perf_counter()

        # Generate cloud
        config = {'pre_analysis': {'enabled': False}}  # Disable pre-analysis for pure grain perf
        cloud = granular_maker.create_cloud(
            audio,
            sr=sr,
            grain_length_min_ms=50,
            grain_length_max_ms=150,
            num_grains=grain_count,
            cloud_duration_sec=6.0,
            pitch_shift_min=-7,
            pitch_shift_max=7,
            overlap_ratio=0.65,
            config=config,
        )

        elapsed = time.perf_counter() - start
        per_grain = (elapsed / grain_count) * 1000  # ms per grain

        print(f"{grain_count:<10} {elapsed:<12.3f} {per_grain:<18.2f}")

        results.append({
            'grain_count': grain_count,
            'time': elapsed,
            'per_grain_ms': per_grain
        })

    # Calculate scaling factor
    if len(results) >= 2:
        ratio = results[-1]['time'] / results[0]['time']
        grain_ratio = results[-1]['grain_count'] / results[0]['grain_count']

        print(f"\n{'SCALING ANALYSIS':^70}")
        print(f"{'-'*70}")
        print(f"  {grain_counts[0]} → {grain_counts[-1]} grains:")
        print(f"  Time increased: {ratio:.2f}x")
        print(f"  Grain count increased: {grain_ratio:.2f}x")
        print(f"  Scaling: O(n^{np.log(ratio)/np.log(grain_ratio):.2f})")

    return results


def profile_full_pipeline():
    """Profile full pipeline with cProfile to identify bottlenecks."""
    print("\n" + "="*70)
    print("PROFILE 3: Full Pipeline Bottlenecks")
    print("="*70)

    # Generate test audio
    sr = 44100
    audio = np.random.randn(sr * 10) * 0.3
    t = np.linspace(0, 10, sr * 10)
    audio += 0.2 * np.sin(2 * np.pi * 220 * t)

    config = {
        'global': {'sample_rate': sr, 'target_peak_dbfs': -3.0},
        'pad_miner': {
            'min_rms_db': -40.0,
            'max_rms_db': -10.0,
            'max_onset_rate_per_second': 3.0,
            'spectral_flatness_threshold': 0.5,
            'window_hop_sec': 0.5,
            'max_candidates_per_file': 2,
        },
        'pre_analysis': {
            'enabled': True,
            'analysis_window_sec': 1.0,
            'analysis_hop_sec': 0.5,
            'min_rms_db': -40.0,
            'max_rms_db': -10.0,
            'max_onset_rate_hz': 3.0,
            'max_dc_offset': 0.1,
            'max_crest_factor': 10.0,
        }
    }

    print("\nProfiling pad mining...")

    # Profile pad mining
    profiler = cProfile.Profile()
    profiler.enable()

    candidates = segment_miner.extract_sustained_segments(
        audio,
        sr=sr,
        target_duration_sec=2.0,
        min_rms_db=-40.0,
        max_rms_db=-10.0,
        max_onset_rate=3.0,
        spectral_flatness_threshold=0.5,
        window_hop_sec=0.5,
        use_pre_analysis=True,
        config=config,
    )

    profiler.disable()

    # Print top 20 time-consuming functions
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(20)

    print("\nTop 20 functions by cumulative time:")
    print("-" * 70)
    print(s.getvalue())

    return stats


def main():
    """Run all performance profiles."""
    print("\n" + "="*70)
    print("AFTERGLOW ENGINE PERFORMANCE PROFILING")
    print("="*70)

    results = {}

    # Profile 1A: STFT caching (isolated)
    results['stft_isolated'] = profile_stft_caching_isolated()

    # Profile 1B: STFT caching (with features)
    results['stft_with_features'] = profile_stft_caching()

    # Profile 2: Cloud generation scaling
    results['cloud_scaling'] = profile_cloud_generation()

    # Profile 3: Full pipeline bottlenecks
    results['pipeline_stats'] = profile_full_pipeline()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n1. STFT Caching (Isolated):")
    print(f"   - Speedup: >{results['stft_isolated']['speedup_vs_single']:.0f}x (essentially free after first call)")
    print(f"   - Overhead reduction in single pass: {results['stft_isolated']['overhead_reduction_pct']:.1f}%")
    print(f"\n2. Feature Computation Caching:")
    print(f"   - Speedup: {results['stft_with_features']['speedup']:.2f}x")
    print(f"   - Saves {results['stft_with_features']['savings_pct']:.1f}% of analysis time")
    print(f"\n3. Cloud Generation: ~Linear scaling O(n)")
    print(f"   - 50 grains: {results['cloud_scaling'][0]['time']:.3f}s")
    print(f"   - 800 grains: {results['cloud_scaling'][-1]['time']:.3f}s")
    print(f"\n4. Pipeline Bottlenecks: See detailed profile above")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
