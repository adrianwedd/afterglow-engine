#!/usr/bin/env python3
"""
Compare benchmark results against baseline for CI/CD performance regression detection.

Usage:
    python tests/compare_benchmarks.py <current_results.json> <baseline.json> [--threshold 0.20]
"""

import sys
import json
import argparse
from pathlib import Path


def compare_benchmarks(current_path: str, baseline_path: str, threshold: float = 0.20) -> int:
    """
    Compare current benchmark results against baseline.

    Args:
        current_path: Path to current benchmark results JSON
        baseline_path: Path to baseline benchmark results JSON
        threshold: Maximum allowed slowdown (0.20 = 20%)

    Returns:
        0 if performance is acceptable, 1 if regressions detected
    """
    # Load results
    with open(current_path, 'r') as f:
        current = json.load(f)

    with open(baseline_path, 'r') as f:
        baseline = json.load(f)

    print("=" * 60)
    print("PERFORMANCE REGRESSION ANALYSIS")
    print("=" * 60)

    regressions = []
    improvements = []

    for bench_name, current_time in current.items():
        if bench_name not in baseline:
            print(f"⚠️  NEW: {bench_name}: {current_time:.4f}s (no baseline)")
            continue

        baseline_time = baseline[bench_name]
        diff = current_time - baseline_time
        pct_change = (diff / baseline_time) * 100

        status = "✓"
        if diff > baseline_time * threshold:
            status = "✗"
            regressions.append((bench_name, baseline_time, current_time, pct_change))
        elif diff < -baseline_time * 0.05:  # 5% improvement
            status = "↑"
            improvements.append((bench_name, baseline_time, current_time, pct_change))

        print(f"{status} {bench_name}:")
        print(f"    Baseline:  {baseline_time:.4f}s")
        print(f"    Current:   {current_time:.4f}s")
        print(f"    Change:    {diff:+.4f}s ({pct_change:+.1f}%)")

    print("\n" + "=" * 60)

    if improvements:
        print(f"\n✨ IMPROVEMENTS ({len(improvements)}):")
        for name, base, curr, pct in improvements:
            print(f"  {name}: {pct:.1f}% faster ({base:.4f}s → {curr:.4f}s)")

    if regressions:
        print(f"\n⚠️  REGRESSIONS DETECTED ({len(regressions)}):")
        for name, base, curr, pct in regressions:
            print(f"  {name}: {pct:.1f}% slower ({base:.4f}s → {curr:.4f}s)")
        print(f"\nThreshold: {threshold * 100:.0f}% slowdown allowed")
        print("=" * 60)
        return 1
    else:
        print("\n✓ All benchmarks within acceptable performance range")
        print("=" * 60)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument('current', help='Path to current benchmark results JSON')
    parser.add_argument('baseline', help='Path to baseline benchmark results JSON')
    parser.add_argument('--threshold', type=float, default=0.20,
                        help='Maximum allowed slowdown (default: 0.20 = 20%%)')
    args = parser.parse_args()

    if not Path(args.current).exists():
        print(f"Error: Current results file not found: {args.current}")
        return 1

    if not Path(args.baseline).exists():
        print(f"Error: Baseline file not found: {args.baseline}")
        print("Creating baseline from current results...")
        # Copy current to baseline
        with open(args.current, 'r') as f:
            data = json.load(f)
        with open(args.baseline, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Baseline created at {args.baseline}")
        return 0

    return compare_benchmarks(args.current, args.baseline, args.threshold)


if __name__ == "__main__":
    sys.exit(main())
