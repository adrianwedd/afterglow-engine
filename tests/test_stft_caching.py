"""Test STFT caching in AudioAnalyzer (Phase 3)."""

import unittest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from musiclib.audio_analyzer import AudioAnalyzer


class TestSTFTCaching(unittest.TestCase):
    """Test STFT result caching for performance optimization."""

    def test_stft_cached_across_features(self):
        """STFT should be computed once and reused for onset + centroid."""
        # Create test audio
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # Sine wave with harmonics
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5 +
                 np.sin(2 * np.pi * 880 * t) * 0.25)

        analyzer = AudioAnalyzer(audio, sr, window_size_sec=1.0)

        # Access STFT before any feature computation
        self.assertIsNone(analyzer._stft_cache, "STFT cache should start empty")

        # Compute onset density (triggers STFT)
        onset_frames = analyzer._compute_onset_density()
        self.assertIsNotNone(analyzer._stft_cache, "STFT should be cached after onset computation")

        # Save reference to cached STFT
        first_stft = analyzer._stft_cache
        first_stft_id = id(first_stft)

        # Compute spectral centroid (should reuse cached STFT)
        centroid = analyzer._compute_spectral_centroid()
        second_stft_id = id(analyzer._stft_cache)

        # Verify the SAME STFT object is reused
        self.assertEqual(first_stft_id, second_stft_id,
                        "STFT cache should be reused, not recomputed")

    def test_stft_cache_works_with_multiple_calls(self):
        """Multiple calls to features should all use the same cached STFT."""
        sr = 22050
        audio = np.random.randn(sr) * 0.5

        analyzer = AudioAnalyzer(audio, sr, window_size_sec=0.5)

        # Call features multiple times
        for _ in range(3):
            _ = analyzer._compute_onset_density()
            _ = analyzer._compute_spectral_centroid()

        # STFT should have been computed exactly once
        self.assertIsNotNone(analyzer._stft_cache)

    def test_get_stft_method(self):
        """_get_stft() should cache and return the STFT."""
        sr = 22050
        audio = np.random.randn(sr) * 0.5
        analyzer = AudioAnalyzer(audio, sr)

        # First call should compute
        stft1 = analyzer._get_stft()
        self.assertIsNotNone(stft1)
        self.assertEqual(stft1.shape[1], len(stft1[0]))  # Complex matrix

        # Second call should return cached version
        stft2 = analyzer._get_stft()
        self.assertIs(stft1, stft2, "Should return same object instance")

    def test_caching_produces_correct_results(self):
        """Cached STFT should produce same results as non-cached."""
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t) * 0.5

        analyzer = AudioAnalyzer(audio, sr, window_size_sec=0.5)

        # Compute features with caching
        onset_cached = analyzer._compute_onset_density()
        centroid_cached = analyzer._compute_spectral_centroid()

        # Both should return valid results
        self.assertIsNotNone(onset_cached)
        self.assertIsNotNone(centroid_cached)
        self.assertTrue(len(centroid_cached) > 0)


if __name__ == '__main__':
    unittest.main()
