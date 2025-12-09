"""
Test golden audio fixtures for regression detection.

These tests verify that DSP operations produce consistent, deterministic
results. If a golden fixture test fails, it indicates that a code change
has altered the output of a core DSP function.
"""

import unittest
import numpy as np
import soundfile as sf
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.dsp_utils as dsp_utils

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "golden_audio"
SR = 44100


class TestGoldenFixtures(unittest.TestCase):
    """Verify DSP operations produce consistent results against golden fixtures."""

    def _load_fixture(self, filename):
        """Load a golden fixture audio file."""
        path = FIXTURES_DIR / filename
        self.assertTrue(path.exists(), f"Golden fixture not found: {filename}")
        audio, sr = sf.read(path)
        self.assertEqual(sr, SR, f"Fixture {filename} has wrong sample rate")
        return audio

    def test_fixture_sine_440hz_characteristics(self):
        """Verify pure 440 Hz sine wave fixture has expected properties."""
        audio = self._load_fixture("sine_440hz.wav")

        # Duration should be 1.0s
        self.assertAlmostEqual(len(audio) / SR, 1.0, places=2)

        # Peak should be approximately 0.5
        peak = np.max(np.abs(audio))
        self.assertAlmostEqual(peak, 0.5, places=3)

        # Should be centered around zero (minimal DC offset)
        dc_offset = np.mean(audio)
        self.assertLess(abs(dc_offset), 0.001)

    def test_fixture_white_noise_characteristics(self):
        """Verify white noise fixture has expected statistical properties."""
        audio = self._load_fixture("white_noise.wav")

        # Should have Gaussian-like distribution
        mean = np.mean(audio)
        std = np.std(audio)

        # Mean should be close to zero
        self.assertLess(abs(mean), 0.05)

        # Std should be approximately the amplitude (0.3)
        self.assertAlmostEqual(std, 0.3, delta=0.05)

    def test_regenerate_normalized_minus3db(self):
        """Verify normalization produces same result as golden fixture."""
        # Regenerate the normalized audio
        np.random.seed(42)
        t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
        sine_quiet = np.sin(2 * np.pi * 440 * t) * 0.1
        regenerated = dsp_utils.normalize_audio(sine_quiet, target_peak_dbfs=-3.0)

        # Load golden fixture
        golden = self._load_fixture("normalized_minus3db.wav")

        # Should be identical (within 24-bit PCM quantization tolerance)
        # 24-bit quantization: 1/(2^23) ≈ 1.19e-7
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Normalization output differs from golden fixture")

        # Verify peak is at -3 dBFS
        peak_db = 20 * np.log10(np.max(np.abs(golden)))
        self.assertAlmostEqual(peak_db, -3.0, places=2)

    def test_regenerate_equal_power_crossfade(self):
        """Verify equal-power crossfade produces same result as golden fixture."""
        # Regenerate the crossfaded audio
        np.random.seed(42)
        t1 = np.linspace(0, 1.0, int(SR * 1.0), endpoint=False)
        audio1 = np.sin(2 * np.pi * 440 * t1) * 0.5
        audio2 = np.sin(2 * np.pi * 880 * t1) * 0.5
        fade_length = int(0.1 * SR)
        regenerated = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)

        # Load golden fixture
        golden = self._load_fixture("crossfade_equal_power.wav")

        # Should be identical
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Equal-power crossfade output differs from golden fixture")

    def test_regenerate_linear_crossfade(self):
        """Verify linear crossfade produces same result as golden fixture."""
        # Regenerate the crossfaded audio
        np.random.seed(42)
        t1 = np.linspace(0, 1.0, int(SR * 1.0), endpoint=False)
        audio1 = np.sin(2 * np.pi * 440 * t1) * 0.5
        audio2 = np.sin(2 * np.pi * 880 * t1) * 0.5
        fade_length = int(0.1 * SR)
        regenerated = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)

        # Load golden fixture
        golden = self._load_fixture("crossfade_linear.wav")

        # Should be identical
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Linear crossfade output differs from golden fixture")

    def test_regenerate_loop_equal_power(self):
        """Verify loop crossfade produces same result as golden fixture."""
        # Regenerate the looped audio
        np.random.seed(42)
        t = np.linspace(0, 2.0, int(SR * 2.0), endpoint=False)
        fundamental = 110.0
        loop_source = (np.sin(2 * np.pi * fundamental * t) * 0.4 +
                      np.sin(2 * np.pi * fundamental * 2 * t) * 0.2 +
                      np.sin(2 * np.pi * fundamental * 3 * t) * 0.15 +
                      np.sin(2 * np.pi * fundamental * 5 * t) * 0.1)
        regenerated = dsp_utils.time_domain_crossfade_loop(
            loop_source, crossfade_ms=50.0, sr=SR, optimize_loop=False, equal_power=True
        )

        # Load golden fixture
        golden = self._load_fixture("loop_equal_power.wav")

        # Should be identical
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Loop crossfade output differs from golden fixture")

    def test_regenerate_stereo_to_mono_average(self):
        """Verify stereo-to-mono (average) produces same result as golden fixture."""
        # Regenerate the mono audio
        np.random.seed(42)
        t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
        left = np.sin(2 * np.pi * 440 * t) * 0.6
        right = np.sin(2 * np.pi * 880 * t) * 0.4
        stereo = np.column_stack([left, right])
        regenerated = dsp_utils.ensure_mono(stereo, method="average")

        # Load golden fixture
        golden = self._load_fixture("stereo_to_mono_average.wav")

        # Should be identical
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Stereo-to-mono (average) output differs from golden fixture")

    def test_regenerate_stereo_to_mono_sum(self):
        """Verify stereo-to-mono (sum/power) produces same result as golden fixture."""
        # Regenerate the mono audio
        np.random.seed(42)
        t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
        left = np.sin(2 * np.pi * 440 * t) * 0.6
        right = np.sin(2 * np.pi * 880 * t) * 0.4
        stereo = np.column_stack([left, right])
        regenerated = dsp_utils.ensure_mono(stereo, method="sum")

        # Load golden fixture
        golden = self._load_fixture("stereo_to_mono_sum.wav")

        # Should be identical
        self.assertTrue(np.allclose(regenerated, golden, rtol=1e-5, atol=1e-6),
                       "Stereo-to-mono (sum) output differs from golden fixture")

    def test_crossfade_fixtures_differ(self):
        """Equal-power and linear crossfades should produce different results."""
        eq_power = self._load_fixture("crossfade_equal_power.wav")
        linear = self._load_fixture("crossfade_linear.wav")

        # Should NOT be identical
        self.assertFalse(np.allclose(eq_power, linear, rtol=1e-3),
                        "Equal-power and linear crossfades should differ")

        # But should have same length
        self.assertEqual(len(eq_power), len(linear))

    def test_stereo_to_mono_methods_differ(self):
        """Average and sum methods should produce different mono results."""
        average = self._load_fixture("stereo_to_mono_average.wav")
        sum_method = self._load_fixture("stereo_to_mono_sum.wav")

        # Should NOT be identical
        self.assertFalse(np.allclose(average, sum_method, rtol=1e-3),
                        "Average and sum methods should produce different results")

        # Sum method should have higher RMS (preserves power)
        rms_avg = np.sqrt(np.mean(average**2))
        rms_sum = np.sqrt(np.mean(sum_method**2))
        self.assertGreater(rms_sum, rms_avg * 1.2,
                          "Sum method should preserve more power than average")


if __name__ == '__main__':
    unittest.main()
