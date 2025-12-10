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


def profile_stft_caching():
    """Measure STFT caching speedup in AudioAnalyzer."""
    print("\n" + "="*70)
    print("PROFILE 1: STFT Caching Speedup")
    print("="*70)

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
    print("\n--- With STFT Caching (current implementation) ---")
    start = time.perf_counter()
    analyzer = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=1.0, hop_sec=0.5)

    # Call features multiple times - STFT computed once
    onset1 = analyzer._compute_onset_density()
    centroid1 = analyzer._compute_spectral_centroid()
    onset2 = analyzer._compute_onset_density()  # Reuses cache
    centroid2 = analyzer._compute_spectral_centroid()  # Reuses cache

    elapsed_cached = time.perf_counter() - start

    print(f"Elapsed time: {elapsed_cached:.3f}s")
    print(f"STFT computed: 1 time (cached)")
    print(f"Features computed: 4 calls (2 onset + 2 centroid)")

    # Scenario 2: No caching (clear cache between each call)
    print("\n--- Without STFT Caching (simulated) ---")
    start = time.perf_counter()
    analyzer2 = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=1.0, hop_sec=0.5)

    # Each call recomputes STFT
    onset1 = analyzer2._compute_onset_density()
    analyzer2._stft_cache = None  # Clear cache
    centroid1 = analyzer2._compute_spectral_centroid()
    analyzer2._stft_cache = None  # Clear cache
    analyzer2._onset_frames = None  # Clear onset cache
    onset2 = analyzer2._compute_onset_density()
    analyzer2._stft_cache = None  # Clear cache
    analyzer2._spectral_centroid = None  # Clear centroid cache
    centroid2 = analyzer2._compute_spectral_centroid()

    elapsed_uncached = time.perf_counter() - start

    print(f"Elapsed time: {elapsed_uncached:.3f}s")
    print(f"STFT computed: 4 times (no caching)")
    print(f"Features computed: 4 calls (2 onset + 2 centroid)")

    speedup = elapsed_uncached / elapsed_cached
    savings = (1 - elapsed_cached / elapsed_uncached) * 100

    print(f"\n{'RESULTS':^70}")
    print(f"{'-'*70}")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time saved: {savings:.1f}%")
    print(f"  Absolute savings: {(elapsed_uncached - elapsed_cached):.3f}s per analysis")

    return {
        'cached_time': elapsed_cached,
        'uncached_time': elapsed_uncached,
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

    # Profile 1: STFT caching
    results['stft_caching'] = profile_stft_caching()

    # Profile 2: Cloud generation scaling
    results['cloud_scaling'] = profile_cloud_generation()

    # Profile 3: Full pipeline bottlenecks
    results['pipeline_stats'] = profile_full_pipeline()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n1. STFT Caching: {results['stft_caching']['speedup']:.2f}x speedup")
    print(f"   - Saves {results['stft_caching']['savings_pct']:.1f}% of analysis time")
    print(f"\n2. Cloud Generation: ~Linear scaling O(n)")
    print(f"   - 50 grains: {results['cloud_scaling'][0]['time']:.3f}s")
    print(f"   - 800 grains: {results['cloud_scaling'][-1]['time']:.3f}s")
    print(f"\n3. Pipeline Bottlenecks: See detailed profile above")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
