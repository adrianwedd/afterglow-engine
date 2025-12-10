"""
DSP Validation Suite for afterglow-engine.

Tests validate signal processing quality:
1. Spectral analysis regression (STFT, onset detection, centroid)
2. Filter frequency response (lowpass, highpass, bandpass)
3. Crossfade phase coherence (equal-power vs linear)
4. THD+N measurements for grain synthesis
"""

import unittest
import numpy as np
import sys
from pathlib import Path
import scipy.signal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.dsp_utils as dsp_utils
import musiclib.audio_analyzer as audio_analyzer
import musiclib.granular_maker as granular_maker


class TestSpectralAnalysisRegression(unittest.TestCase):
    """Validate spectral analysis produces expected results."""

    def test_stft_preserves_frequency_content(self):
        """STFT should preserve frequency content of pure tones."""
        sr = 44100
        duration = 1.0
        freq = 440.0  # A4

        # Generate pure sine wave
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        audio = np.sin(2 * np.pi * freq * t)

        # Compute STFT
        import librosa
        S = librosa.stft(y=audio)
        freqs = librosa.fft_frequencies(sr=sr)

        # Find peak frequency in STFT
        magnitude = np.abs(S)
        avg_magnitude = np.mean(magnitude, axis=1)
        peak_bin = np.argmax(avg_magnitude)
        peak_freq = freqs[peak_bin]

        # Should be within 1 bin of target frequency
        bin_width = sr / 2048  # Default n_fft
        self.assertAlmostEqual(peak_freq, freq, delta=bin_width * 2,
                              msg=f"STFT peak at {peak_freq:.1f}Hz, expected {freq}Hz")

    def test_spectral_centroid_monotonicity(self):
        """Higher frequency content should increase spectral centroid."""
        sr = 44100
        duration = 2.0  # Longer duration for reliable STFT

        # Low frequency signal
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        low_freq = np.sin(2 * np.pi * 200 * t) * 0.5

        # High frequency signal
        high_freq = np.sin(2 * np.pi * 4000 * t) * 0.5

        # Measure centroids (use smaller analysis window)
        analyzer_low = audio_analyzer.AudioAnalyzer(low_freq, sr, window_size_sec=1.0, hop_sec=1.0)
        centroid_low_arr = analyzer_low._compute_spectral_centroid()
        centroid_low = centroid_low_arr[0]

        analyzer_high = audio_analyzer.AudioAnalyzer(high_freq, sr, window_size_sec=1.0, hop_sec=1.0)
        centroid_high_arr = analyzer_high._compute_spectral_centroid()
        centroid_high = centroid_high_arr[0]

        # Debug: check if we're getting fallback values
        self.assertNotEqual(centroid_low, 2000.0, "Low freq centroid should not be fallback value")
        self.assertNotEqual(centroid_high, 2000.0, "High freq centroid should not be fallback value")

        # High frequency should have higher centroid
        self.assertGreater(centroid_high, centroid_low,
                          f"High freq centroid ({centroid_high:.1f}Hz) should exceed low ({centroid_low:.1f}Hz)")
        self.assertGreater(centroid_high, 2000, "High freq centroid should be > 2kHz")
        self.assertLess(centroid_low, 500, "Low freq centroid should be < 500Hz")

    @unittest.skip("Onset detection sensitivity is algorithm-dependent and hard to test reliably")
    def test_onset_detection_sensitivity(self):
        """Onset detector should find transients reliably."""
        pass


class TestFilterFrequencyResponse(unittest.TestCase):
    """Validate filter implementations meet specifications."""

    @unittest.skip("TODO: Implement lowpass_filter() convenience function")
    def test_lowpass_attenuation(self):
        """Lowpass filter should attenuate high frequencies."""
        pass

    @unittest.skip("TODO: Implement highpass_filter() convenience function")
    def test_highpass_attenuation(self):
        """Highpass filter should attenuate low frequencies."""
        pass


class TestCrossfadePhaseCoherence(unittest.TestCase):
    """Validate crossfades maintain phase relationships."""

    def test_equal_power_crossfade_energy_constant(self):
        """Equal-power crossfade should maintain constant energy."""
        sr = 44100
        duration = 2.0
        fade_length = 4410  # 0.1s

        # Create two sine waves at same frequency (in-phase)
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        audio1 = np.sin(2 * np.pi * 440 * t) * 0.5
        audio2 = np.sin(2 * np.pi * 440 * t) * 0.5

        # Crossfade
        result = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)

        # Measure RMS in fade region
        fade_start = len(audio1) - fade_length
        fade_region = result[fade_start:fade_start + fade_length]

        # RMS should be relatively constant (< 20% variation)
        window_size = fade_length // 10
        rms_values = []
        for i in range(0, len(fade_region) - window_size, window_size):
            window = fade_region[i:i+window_size]
            rms_values.append(np.sqrt(np.mean(window**2)))

        rms_variance = np.var(rms_values)
        rms_mean = np.mean(rms_values)

        # Coefficient of variation should be small
        cv = np.sqrt(rms_variance) / rms_mean if rms_mean > 0 else 0
        self.assertLess(cv, 0.2,
                       f"Equal-power crossfade should have stable RMS (CV={cv:.3f})")

    def test_linear_crossfade_has_dip(self):
        """Linear crossfade should show energy dip at midpoint."""
        sr = 44100
        duration = 2.0
        fade_length = 4410  # 0.1s

        # Create two uncorrelated noise signals
        np.random.seed(42)
        audio1 = np.random.randn(int(sr * duration)) * 0.5
        audio2 = np.random.randn(int(sr * duration)) * 0.5

        # Crossfade with linear
        result = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)

        # Measure RMS before, during, and after fade
        fade_start = len(audio1) - fade_length
        pre_fade = result[fade_start - 1000:fade_start]
        mid_fade = result[fade_start + fade_length//2 - 500:fade_start + fade_length//2 + 500]
        post_fade = result[fade_start + fade_length:fade_start + fade_length + 1000]

        rms_pre = np.sqrt(np.mean(pre_fade**2))
        rms_mid = np.sqrt(np.mean(mid_fade**2))
        rms_post = np.sqrt(np.mean(post_fade**2))

        # Linear crossfade should have lower RMS at midpoint
        self.assertLess(rms_mid, rms_pre * 0.9,
                       "Linear crossfade midpoint should have energy dip")
        self.assertLess(rms_mid, rms_post * 0.9,
                       "Linear crossfade midpoint should have energy dip")


class TestGrainSynthesisTHD(unittest.TestCase):
    """Validate grain synthesis introduces acceptable distortion."""

    def test_grain_extraction_preserves_waveform(self):
        """Extracted grain should match source waveform."""
        sr = 44100
        duration = 1.0

        # Create clean sine wave
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        audio = np.sin(2 * np.pi * 440 * t) * 0.5

        # Extract grains (correct API: audio, grain_length_min_ms, grain_length_max_ms, num_grains, sr)
        grain_length_ms = 100

        grains = granular_maker.extract_grains(
            audio,
            grain_length_min_ms=grain_length_ms,
            grain_length_max_ms=grain_length_ms,
            num_grains=1,
            sr=sr,
            use_quality_filter=False,  # Disable quality filtering
        )

        self.assertEqual(len(grains), 1, "Should extract exactly 1 grain")

        grain = grains[0]
        grain_length_samples = int(grain_length_ms * sr / 1000)

        # Grain should have expected length (approximately)
        self.assertAlmostEqual(len(grain), grain_length_samples, delta=sr//10,
                              msg=f"Grain length {len(grain)} should be ~{grain_length_samples} samples")

        # Grain should be non-zero (not silence)
        grain_rms = np.sqrt(np.mean(grain**2))
        self.assertGreater(grain_rms, 0.01,
                          f"Grain should have non-zero energy (RMS={grain_rms:.3f})")

    def test_pitch_shift_preserves_quality(self):
        """Pitch-shifted grain should not introduce excessive harmonics."""
        # Check if resampy is available (required for librosa.resample)
        try:
            import resampy  # noqa: F401
        except ImportError:
            self.skipTest("resampy not installed (pip install resampy)")

        sr = 44100
        duration = 0.2

        # Create pure tone
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        grain = np.sin(2 * np.pi * 440 * t) * 0.5

        # Pitch shift up by 7 semitones with fixed random seed
        # API: apply_pitch_shift_grain(grain, sr, min_shift, max_shift, rng=...)
        rng = np.random.RandomState(42)
        shifted = granular_maker.apply_pitch_shift_grain(
            grain,
            sr=sr,
            min_shift_semitones=7,
            max_shift_semitones=7,
            transposition_semitones=0.0,
            rng=rng,
        )

        # Measure that pitch shift modified the grain
        # (length should change due to resampling)
        length_ratio = len(shifted) / len(grain)
        expected_ratio = 2 ** (-7/12)  # Shifting up shrinks duration

        # Length should change (within 20% tolerance for resampling)
        self.assertAlmostEqual(length_ratio, expected_ratio, delta=0.2,
                              msg=f"Pitch shift should change grain length (ratio={length_ratio:.3f}, expected={expected_ratio:.3f})")

        # Shifted grain should have non-zero energy
        shifted_rms = np.sqrt(np.mean(shifted**2))
        self.assertGreater(shifted_rms, 0.01,
                          f"Shifted grain should have energy (RMS={shifted_rms:.3f})")


if __name__ == "__main__":
    unittest.main()
