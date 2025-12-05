import numpy as np

from musiclib.audio_analyzer import AudioAnalyzer
from musiclib.granular_maker import create_cloud


def test_stable_regions_cache_keyed():
    """Stable regions should differ with different thresholds (no stale cache)."""
    sr = 1000
    t = np.arange(sr * 2) / sr
    audio = 0.2 * np.sin(2 * np.pi * 5 * t)
    analyzer = AudioAnalyzer(audio, sr, window_size_sec=0.5, hop_sec=0.5)

    mask_loose = analyzer.get_stable_regions(
        max_onset_rate=5.0, rms_low_db=-60, rms_high_db=-5, max_dc_offset=0.1, max_crest=20.0
    )
    mask_strict = analyzer.get_stable_regions(
        max_onset_rate=1.0, rms_low_db=-20, rms_high_db=-10, max_dc_offset=0.01, max_crest=5.0
    )
    assert not np.array_equal(mask_loose, mask_strict)


def test_sorted_windows_respects_quality_gates():
    """Sorted windows should prefer low-onset, low-crest windows and filter spikes."""
    sr = 1000
    # Two windows of 0.5s each
    base = 0.2 * np.sin(2 * np.pi * 5 * np.arange(sr) / sr)
    spike = base.copy()
    spike[sr // 4] = 5.0  # transient to increase crest
    audio = np.concatenate([base, spike])

    analyzer = AudioAnalyzer(audio, sr, window_size_sec=0.5, hop_sec=0.5)
    sorted_idx = analyzer.get_sorted_windows(
        rms_low_db=-60,
        rms_high_db=0,
        max_dc_offset=0.2,
        max_crest=10.0,
    )
    # The first window (index 0) should rank ahead of the spiky one
    assert sorted_idx[0] == 0


def test_cloud_fade_guard_preserves_signal():
    """Short clouds should retain signal after guarded fades."""
    sr = 44100
    audio = 0.2 * np.sin(2 * np.pi * 220 * np.arange(sr) / sr)
    cloud = create_cloud(
        audio,
        sr=sr,
        grain_length_min_ms=10,
        grain_length_max_ms=20,
        num_grains=10,
        cloud_duration_sec=0.05,  # very short to exercise fade guard
        pitch_shift_min=0,
        pitch_shift_max=0,
        overlap_ratio=0.5,
        config={"pre_analysis": {"enabled": False}},
    )
    assert cloud.size > 0
    assert np.max(np.abs(cloud)) > 0
