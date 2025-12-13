"""
Property-based tests using Hypothesis for DSP functions.

Property-based testing generates random inputs to verify that certain
invariants (properties) hold for all possible inputs, catching edge
cases that manual tests might miss.
"""

import unittest
import numpy as np
import sys
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.numpy import arrays

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.dsp_utils as dsp_utils


# Custom strategies for audio testing
def audio_array(min_size=100, max_size=10000, min_value=-1.0, max_value=1.0):
    """Generate random audio arrays."""
    return arrays(
        dtype=np.float64,
        shape=st.integers(min_value=min_size, max_value=max_size),
        elements=st.floats(
            min_value=min_value,
            max_value=max_value,
            allow_nan=False,
            allow_infinity=False,
        ),
    )


class TestNormalizationProperties(unittest.TestCase):
    """Property-based tests for normalize_audio()."""

    @given(audio=audio_array(min_size=100, max_size=5000, min_value=-0.8, max_value=0.8))
    @settings(max_examples=50, deadline=2000)
    def test_normalization_preserves_shape(self, audio):
        """Normalization should not change signal shape, only scale."""
        # Skip silent or near-silent audio
        peak = np.max(np.abs(audio))
        assume(peak > 1e-6)

        # Skip constant signals (no variance)
        variance = np.var(audio)
        assume(variance > 1e-10)

        # Normalize to -6 dBFS
        normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=-6.0)

        # Shape should be preserved
        self.assertEqual(len(normalized), len(audio))

        # Correlation should be perfect (shape preserved)
        correlation = np.corrcoef(audio, normalized)[0, 1]
        self.assertGreater(correlation, 0.9999, "Normalization should only scale, not distort")

    @given(
        audio=audio_array(min_size=100, max_size=5000, min_value=-0.5, max_value=0.5),
        target_db=st.floats(min_value=-20.0, max_value=-1.0),
    )
    @settings(max_examples=50, deadline=2000)
    def test_normalization_achieves_target_peak(self, audio, target_db):
        """Normalized audio should have peak at target dBFS."""
        peak = np.max(np.abs(audio))
        assume(peak > 1e-6)

        normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=target_db)

        # Check peak level
        actual_peak = np.max(np.abs(normalized))
        expected_peak = 10 ** (target_db / 20.0)

        self.assertAlmostEqual(actual_peak, expected_peak, places=4)

    @given(audio=audio_array(min_size=100, max_size=5000, min_value=-0.8, max_value=0.8))
    @settings(max_examples=30, deadline=2000)
    def test_normalization_preserves_zero_crossings(self, audio):
        """Normalization should preserve zero-crossing positions."""
        peak = np.max(np.abs(audio))
        assume(peak > 1e-6)

        normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=-3.0)

        # Count zero crossings
        zero_crossings_orig = np.sum(np.diff(np.signbit(audio)))
        zero_crossings_norm = np.sum(np.diff(np.signbit(normalized)))

        self.assertEqual(zero_crossings_orig, zero_crossings_norm,
                        "Normalization should not change zero crossings")


class TestCrossfadeProperties(unittest.TestCase):
    """Property-based tests for crossfade functions."""

    @given(
        audio1=audio_array(min_size=5000, max_size=10000, min_value=-0.5, max_value=0.5),
        audio2=audio_array(min_size=5000, max_size=10000, min_value=-0.5, max_value=0.5),
        fade_pct=st.floats(min_value=0.01, max_value=0.3),
    )
    @settings(max_examples=30, deadline=3000)
    def test_crossfade_length_preservation(self, audio1, audio2, fade_pct):
        """Crossfaded audio should have expected length."""
        # Ensure same length
        min_len = min(len(audio1), len(audio2))
        audio1 = audio1[:min_len]
        audio2 = audio2[:min_len]

        fade_length = int(fade_pct * min_len)
        assume(fade_length > 10)
        assume(fade_length < min_len)

        result = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)

        # Expected length: len(audio1) + len(audio2) - fade_length
        expected_len = len(audio1) + len(audio2) - fade_length
        self.assertEqual(len(result), expected_len)

    # NOTE: Property for energy stability during crossfades doesn't hold for
    # constant or perfectly correlated signals, so this test is commented out.
    # The golden fixtures test verifies crossfade behavior on realistic signals.
    #
    # @given(
    #     audio1=audio_array(min_size=5000, max_size=8000, min_value=-0.5, max_value=0.5),
    #     audio2=audio_array(min_size=5000, max_size=8000, min_value=-0.5, max_value=0.5),
    # )
    # @settings(max_examples=30, deadline=3000)
    # def test_equal_power_crossfade_energy_stable(self, audio1, audio2):
    #     """Equal-power crossfade should have more stable RMS than linear."""
    #     ...

    # NOTE: Loop crossfade discontinuity reduction doesn't hold for near-constant signals.
    # Hypothesis found examples like [0.25, 0.5, 0.5, ..., 0.5] where crossfading actually
    # increases discontinuity (from 0.25 to 0.5). This property holds for realistic audio
    # with varied content, but not for all possible arrays. Golden fixtures test verifies
    # crossfade behavior on real signals.
    #
    # @given(audio=audio_array(min_size=5000, max_size=10000, min_value=-0.5, max_value=0.5))
    # @settings(max_examples=30, deadline=3000)
    # def test_loop_crossfade_reduces_discontinuity(self, audio):
    #     """Loop crossfade should create smoother loop point than no crossfade."""
    #     ...


class TestStereoMonoProperties(unittest.TestCase):
    """Property-based tests for ensure_mono()."""

    # NOTE: Power preservation property only holds for uncorrelated signals.
    # Perfectly correlated or anti-correlated signals (like constant arrays) break this.
    # Golden fixtures test verifies sum method on realistic signals.
    #
    # @given(
    #     left=audio_array(min_size=1000, max_size=5000, min_value=-0.8, max_value=0.8),
    #     right=audio_array(min_size=1000, max_size=5000, min_value=-0.8, max_value=0.8),
    # )
    # @settings(max_examples=30, deadline=2000)
    # def test_sum_method_preserves_power(self, left, right):
    #     """Sum method should approximately preserve RMS power."""
    #     ...

    @given(mono=audio_array(min_size=1000, max_size=5000, min_value=-0.8, max_value=0.8))
    @settings(max_examples=30, deadline=2000)
    def test_mono_passthrough(self, mono):
        """1D mono audio should pass through unchanged."""
        result = dsp_utils.ensure_mono(mono)

        self.assertEqual(len(result), len(mono))
        self.assertTrue(np.array_equal(result, mono))

    @given(
        left=audio_array(min_size=1000, max_size=3000, min_value=-0.5, max_value=0.5),
        right=audio_array(min_size=1000, max_size=3000, min_value=-0.5, max_value=0.5),
    )
    @settings(max_examples=30, deadline=2000)
    def test_average_method_is_mean(self, left, right):
        """Average method should compute arithmetic mean of channels."""
        min_len = min(len(left), len(right))
        left = left[:min_len]
        right = right[:min_len]

        stereo = np.column_stack([left, right])
        mono_avg = dsp_utils.ensure_mono(stereo, method="average")

        expected = (left + right) / 2.0

        self.assertTrue(np.allclose(mono_avg, expected, rtol=1e-10))


class TestRMSEnergyProperties(unittest.TestCase):
    """Property-based tests for RMS energy calculations."""

    @given(audio=audio_array(min_size=100, max_size=5000, min_value=-1.0, max_value=1.0))
    @settings(max_examples=30, deadline=1000)
    def test_rms_energy_db_range(self, audio):
        """RMS energy in dB should be in reasonable range."""
        # Skip near-silent audio (RMS close to zero can cause log errors)
        rms_val = dsp_utils.rms_energy(audio)
        assume(rms_val > 1e-8)

        rms_db = dsp_utils.rms_energy_db(audio)

        # For signals in [-1, 1], RMS dB should be between -inf and 0
        self.assertLessEqual(rms_db, 0.0)
        # For non-silent signals, should be > -120 dB
        self.assertGreater(rms_db, -120.0)

    @given(
        audio=audio_array(min_size=100, max_size=2000, min_value=-0.5, max_value=0.5),
        scale=st.floats(min_value=0.1, max_value=10.0),
    )
    @settings(max_examples=30, deadline=1000)
    def test_rms_energy_scales_correctly(self, audio, scale):
        """Scaling audio by N should change RMS by 20*log10(N) dB."""
        assume(np.max(np.abs(audio)) > 1e-6)

        rms_orig = dsp_utils.rms_energy_db(audio)
        scaled_audio = audio * scale
        rms_scaled = dsp_utils.rms_energy_db(scaled_audio)

        expected_change = 20 * np.log10(scale)
        actual_change = rms_scaled - rms_orig

        self.assertAlmostEqual(actual_change, expected_change, places=3)


if __name__ == "__main__":
    unittest.main()
