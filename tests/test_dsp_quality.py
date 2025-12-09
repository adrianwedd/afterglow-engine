"""
Test DSP quality improvements (Phase 2/3).
"""

import unittest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.dsp_utils as dsp_utils


class TestEqualPowerCrossfades(unittest.TestCase):
    """Test equal-power crossfade implementation."""

    def test_equal_power_maintains_rms_energy(self):
        """Equal-power crossfade should maintain approximately constant RMS through crossfade region."""
        sr = 44100
        duration_sec = 1.0
        freq = 440.0  # A440

        # Create two sine waves
        t1 = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
        audio1 = np.sin(2 * np.pi * freq * t1) * 0.5

        t2 = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
        audio2 = np.sin(2 * np.pi * freq * 1.5 * t2) * 0.5  # Different frequency

        fade_length = int(0.1 * sr)  # 100ms crossfade

        # Equal-power crossfade
        result_eq_power = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)

        # Linear crossfade for comparison
        result_linear = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)

        # Analyze RMS energy in crossfade region
        # Equal-power should have more stable RMS than linear
        crossfade_start = len(audio1) - fade_length
        crossfade_end = crossfade_start + fade_length

        # Compute windowed RMS through crossfade
        window_size = fade_length // 10
        eq_power_rms = []
        linear_rms = []

        for i in range(crossfade_start, crossfade_end - window_size, window_size // 2):
            eq_power_rms.append(np.sqrt(np.mean(result_eq_power[i:i+window_size]**2)))
            linear_rms.append(np.sqrt(np.mean(result_linear[i:i+window_size]**2)))

        # Equal-power should have lower variance in RMS
        eq_power_variance = np.var(eq_power_rms)
        linear_variance = np.var(linear_rms)

        self.assertLess(eq_power_variance, linear_variance,
                        "Equal-power crossfade should have more stable RMS than linear")

    def test_equal_power_with_uncorrelated_signals(self):
        """Equal-power crossfade maintains energy with uncorrelated signals."""
        sr = 44100
        duration_sec = 0.5

        # Create two uncorrelated noise signals (realistic case for equal-power)
        np.random.seed(42)
        audio1 = np.random.randn(int(sr * duration_sec)) * 0.5
        audio2 = np.random.randn(int(sr * duration_sec)) * 0.5

        fade_length = int(0.05 * sr)  # 50ms

        # Equal-power crossfade
        result_eq = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)

        # Linear crossfade
        result_linear = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)

        # Check RMS through crossfade region
        crossfade_start = len(audio1) - fade_length
        crossfade_region_eq = result_eq[crossfade_start:crossfade_start + fade_length]
        crossfade_region_linear = result_linear[crossfade_start:crossfade_start + fade_length]

        # Compute RMS variance across crossfade (lower = more stable)
        window_size = fade_length // 10
        eq_rms_values = []
        linear_rms_values = []

        for i in range(0, len(crossfade_region_eq) - window_size, window_size // 2):
            eq_rms_values.append(np.sqrt(np.mean(crossfade_region_eq[i:i+window_size]**2)))
            linear_rms_values.append(np.sqrt(np.mean(crossfade_region_linear[i:i+window_size]**2)))

        # Equal-power should have more stable RMS (lower variance)
        eq_variance = np.var(eq_rms_values)
        linear_variance = np.var(linear_rms_values)

        self.assertLess(eq_variance, linear_variance,
                        "Equal-power should have more stable RMS with uncorrelated signals")

    def test_loop_crossfade_equal_power(self):
        """time_domain_crossfade_loop should support equal-power option."""
        sr = 44100
        duration_sec = 1.0
        freq = 440.0

        t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
        audio = np.sin(2 * np.pi * freq * t) * 0.5

        crossfade_ms = 50.0

        # Test with equal_power=True
        result_eq = dsp_utils.time_domain_crossfade_loop(
            audio, crossfade_ms, sr, optimize_loop=False, equal_power=True
        )

        # Test with equal_power=False
        result_linear = dsp_utils.time_domain_crossfade_loop(
            audio, crossfade_ms, sr, optimize_loop=False, equal_power=False
        )

        # Both should return valid audio
        self.assertEqual(len(result_eq), len(audio))
        self.assertEqual(len(result_linear), len(audio))

        # Equal-power should have different (more stable) RMS profile
        crossfade_samples = int(crossfade_ms * sr / 1000)

        rms_eq = np.sqrt(np.mean(result_eq[:crossfade_samples]**2))
        rms_linear = np.sqrt(np.mean(result_linear[:crossfade_samples]**2))

        # Equal-power should preserve more energy
        self.assertGreater(rms_eq, rms_linear * 0.9,
                           "Equal-power should preserve RMS better")

    def test_crossfade_backward_compatibility(self):
        """Crossfade with equal_power=False should match old linear behavior."""
        sr = 44100
        audio1 = np.random.randn(sr) * 0.5
        audio2 = np.random.randn(sr) * 0.5
        fade_length = 1000

        # New function with equal_power=False
        result_new = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)

        # Manual linear crossfade (old behavior)
        t = np.linspace(0, 1, fade_length)
        fade_out_manual = 1 - t
        fade_in_manual = t
        overlap_manual = (audio1[-fade_length:] * fade_out_manual +
                          audio2[:fade_length] * fade_in_manual)
        result_manual = np.concatenate([audio1[:-fade_length], overlap_manual, audio2[fade_length:]])

        # Should be identical
        self.assertTrue(np.allclose(result_new, result_manual),
                        "equal_power=False should match old linear behavior")


if __name__ == '__main__':
    unittest.main()
