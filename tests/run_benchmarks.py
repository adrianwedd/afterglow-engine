#!/usr/bin/env python3
"""
Run performance benchmarks and output results in JSON format for CI/CD.

Usage:
    python tests/run_benchmarks.py [--output results.json]
"""

import time
import json
import argparse
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.audio_analyzer as audio_analyzer
import musiclib.granular_maker as granular_maker
import musiclib.dsp_utils as dsp_utils


def benchmark_stft_analysis():
    """Benchmark STFT analysis with caching."""
    sr = 44100
    duration = 10.0
    audio = np.random.randn(int(sr * duration)) * 0.3

    start = time.perf_counter()
    analyzer = audio_analyzer.AudioAnalyzer(audio, sr, window_size_sec=1.0, hop_sec=0.5)
    # Trigger STFT computation via internal methods
    _ = analyzer._compute_onset_density()
    _ = analyzer._compute_spectral_centroid()
    _ = analyzer._compute_crest_factor()
    elapsed = time.perf_counter() - start

    return elapsed


def benchmark_crossfade_loop():
    """Benchmark crossfade loop creation."""
    sr = 44100
    duration = 2.0
    audio = np.random.randn(int(sr * duration)) * 0.3

    start = time.perf_counter()
    for _ in range(20):
        _ = dsp_utils.time_domain_crossfade_loop(audio.copy(), crossfade_ms=50, sr=sr)
    elapsed = time.perf_counter() - start

    return elapsed / 20  # Average per call


def benchmark_audio_normalization():
    """Benchmark audio normalization."""
    sr = 44100
    duration = 5.0
    audio = np.random.randn(int(sr * duration)) * 0.3

    start = time.perf_counter()
    for _ in range(100):
        _ = dsp_utils.normalize_audio(audio.copy(), -1.0)
    elapsed = time.perf_counter() - start

    return elapsed / 100  # Average per call


def benchmark_filter_design():
    """Benchmark filter design and application."""
    sr = 44100
    duration = 2.0
    audio = np.random.randn(int(sr * duration)) * 0.3

    start = time.perf_counter()
    for _ in range(50):
        b, a = dsp_utils.design_butterworth_bandpass(1000, 5000, sr, order=4)
        _ = dsp_utils.apply_filter(audio.copy(), b, a)
    elapsed = time.perf_counter() - start

    return elapsed / 50  # Average per call


def run_all_benchmarks():
    """Run all benchmarks and return results."""
    benchmarks = {
        'stft_analysis': benchmark_stft_analysis,
        'crossfade_loop': benchmark_crossfade_loop,
        'audio_normalization': benchmark_audio_normalization,
        'filter_design': benchmark_filter_design,
    }

    results = {}
    print("Running benchmarks...")

    for name, func in benchmarks.items():
        print(f"  {name}...", end=" ", flush=True)
        try:
            elapsed = func()
            results[name] = elapsed
            print(f"{elapsed:.4f}s")
        except Exception as e:
            print(f"FAILED: {e}")
            results[name] = None

    return results


def main():
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument('--output', '-o', default='benchmark_results.json',
                        help='Output JSON file (default: benchmark_results.json)')
    args = parser.parse_args()

    results = run_all_benchmarks()

    # Write results to JSON
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults written to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    for name, time_val in results.items():
        if time_val is not None:
            print(f"{name:.<40} {time_val:.4f}s")
        else:
            print(f"{name:.<40} FAILED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
