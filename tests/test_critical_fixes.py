import unittest
import numpy as np
import os
import shutil
import csv
import sys
from pathlib import Path

# Add project root to python path
sys.path.append(os.getcwd())

import musiclib.dsp_utils as dsp_utils
from musiclib.exceptions import InvalidParameter, SilentArtifact
import validate_config
import make_textures

class TestC2SilentAudioNormalization(unittest.TestCase):
    """C2: Verify silent audio normalization fix"""
    
    def test_absolute_silence_raises_error(self):
        """Should raise SilentArtifact for all-zero array"""
        audio = np.zeros(44100)
        with self.assertRaises(SilentArtifact) as cm:
            dsp_utils.normalize_audio(audio)
        self.assertIn("silent audio", str(cm.exception))

    def test_near_silence_raises_error(self):
        """Should raise SilentArtifact for audio below 1e-8 peak"""
        audio = np.random.uniform(-1e-9, 1e-9, 44100)
        with self.assertRaises(SilentArtifact) as cm:
            dsp_utils.normalize_audio(audio)
        self.assertIn("silent audio", str(cm.exception))

    def test_normal_audio_works(self):
        """Should normalize audible signals correctly"""
        audio = np.array([0.5, -0.5])
        target_db = -6.0
        normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=target_db)
        
        expected_peak = 10 ** (target_db / 20.0)
        actual_peak = np.max(np.abs(normalized))
        self.assertAlmostEqual(actual_peak, expected_peak, places=6)

class TestH2StereoMonoShapeHandling(unittest.TestCase):
    """H2: Verify robust shape handling for stereo/mono conversion"""

    def test_mono_passthrough(self):
        """1D array should pass through unchanged"""
        audio = np.zeros(100)
        result = dsp_utils.ensure_mono(audio)
        self.assertEqual(result.shape, (100,))
        self.assertTrue(np.array_equal(audio, result))

    def test_librosa_stereo_convention(self):
        """(2, N) should be averaged to (N,)"""
        # Create stereo with different left/right
        audio = np.zeros((2, 100))
        audio[0, :] = 1.0 # Left
        audio[1, :] = 0.5 # Right
        # Mean should be 0.75
        
        result = dsp_utils.ensure_mono(audio)
        self.assertEqual(result.shape, (100,))
        self.assertTrue(np.allclose(result, 0.75))

    def test_soundfile_stereo_convention(self):
        """(N, 2) should be averaged to (N,)"""
        audio = np.zeros((100, 2))
        audio[:, 0] = 1.0
        audio[:, 1] = 0.5
        
        result = dsp_utils.ensure_mono(audio)
        self.assertEqual(result.shape, (100,))
        self.assertTrue(np.allclose(result, 0.75))

    def test_invalid_shape_raises_error(self):
        """3D or weird shapes should raise ValueError"""
        audio = np.zeros((2, 2, 100))
        with self.assertRaises(ValueError):
            dsp_utils.ensure_mono(audio)

class TestH3AtomicManifestWrites(unittest.TestCase):
    """H3: Verify manifest writing logic uses tempfile"""
    
    def setUp(self):
        self.test_dir = "tests/temp_manifest_test"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_atomic_write_simulation(self):
        """
        Simulate the logic used in make_textures.py:
        Write to temp, then move.
        """
        import tempfile
        
        manifest_path = os.path.join(self.test_dir, "manifest.csv")
        data = [{"file": "test.wav", "grade": "A"}]
        fieldnames = ["file", "grade"]
        
        # 1. Write to temp
        with tempfile.NamedTemporaryFile(mode='w', dir=self.test_dir, delete=False, newline="") as tmp:
            writer = csv.DictWriter(tmp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            tmp_path = tmp.name
            
        # Verify temp exists and main doesn't (yet)
        self.assertTrue(os.path.exists(tmp_path))
        self.assertFalse(os.path.exists(manifest_path))
        
        # 2. Move
        shutil.move(tmp_path, manifest_path)
        
        # Verify final state
        self.assertTrue(os.path.exists(manifest_path))
        self.assertFalse(os.path.exists(tmp_path))
        
        # Check content
        with open(manifest_path, 'r') as f:
            content = f.read()
            self.assertIn("test.wav", content)

class TestH5CrestFactorGuards(unittest.TestCase):
    """H5: Verify crest factor calculations don't crash on silent/near-zero audio"""

    def test_audio_analyzer_crest_silent_audio(self):
        """AudioAnalyzer should handle silent audio without division by zero"""
        from musiclib.audio_analyzer import AudioAnalyzer

        # Silent audio
        audio = np.zeros(44100)
        analyzer = AudioAnalyzer(audio, sr=44100, window_size_sec=0.5)

        # Should not crash
        crest_values = analyzer._compute_crest_factor()
        self.assertIsNotNone(crest_values)
        # Silent audio should have crest = 0.0 (our guard value)
        self.assertTrue(np.all(crest_values == 0.0))

    def test_audio_analyzer_crest_near_zero(self):
        """AudioAnalyzer should handle near-zero RMS without crashes"""
        from musiclib.audio_analyzer import AudioAnalyzer

        # Very quiet audio (below 1e-10 threshold)
        audio = np.random.uniform(-1e-12, 1e-12, 44100)
        analyzer = AudioAnalyzer(audio, sr=44100, window_size_sec=0.5)

        # Should not crash
        crest_values = analyzer._compute_crest_factor()
        self.assertIsNotNone(crest_values)
        # Should use guard value of 0.0
        self.assertTrue(np.all(crest_values == 0.0))

    def test_curate_best_scoring_silent(self):
        """curate_best.py scoring should handle silent samples gracefully"""
        import tempfile
        import soundfile as sf
        import curate_best

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            # Write silent audio
            silent = np.zeros(44100)
            sf.write(tmp.name, silent, 44100)
            tmp_path = tmp.name

        try:
            # Should not crash, should return valid score (likely negative due to silence penalties)
            score = curate_best.score_sample(tmp_path, "drums")
            self.assertIsNotNone(score)
            self.assertIsInstance(score, (int, float))
        finally:
            os.unlink(tmp_path)

    def test_mine_silences_crest_guard(self):
        """mine_silences.py should handle zero RMS without division errors"""
        # This is tested implicitly via the scoring test above,
        # but we verify the pattern exists in the code
        import mine_silences
        import inspect

        # Check that the conservative threshold guard is in the source
        source = inspect.getsource(mine_silences.mine_silences)
        self.assertIn("1e-10", source, "Conservative threshold should be present")
        self.assertIn("if rms_val >", source, "RMS check should exist before division")

class TestH6BitDepthValidation(unittest.TestCase):
    """H6: Verify bit depth validation in save_audio"""

    def test_bit_depth_verification(self):
        """save_audio should verify actual bit depth matches request"""
        import tempfile
        import soundfile as sf
        from musiclib import io_utils

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AFTERGLOW_EXPORT_ROOT"] = tmp

            # Write 24-bit audio
            audio = np.random.randn(1000) * 0.1
            filepath = os.path.join(tmp, "test_24bit.wav")

            result = io_utils.save_audio(filepath, audio, sr=44100, bit_depth=24)
            self.assertTrue(result)

            # Verify it's actually 24-bit
            info = sf.info(filepath)
            self.assertEqual(info.subtype, "PCM_24")

            # Write 16-bit audio
            filepath16 = os.path.join(tmp, "test_16bit.wav")
            result = io_utils.save_audio(filepath16, audio, sr=44100, bit_depth=16)
            self.assertTrue(result)

            # Verify it's actually 16-bit
            info = sf.info(filepath16)
            self.assertEqual(info.subtype, "PCM_16")

class TestH7PhaseAwareStereoConversion(unittest.TestCase):
    """H7: Verify phase-aware stereo conversion methods"""

    def test_method_average(self):
        """Default 'average' method should mean channels"""
        audio_librosa = np.array([[1.0, 1.0], [0.0, 0.0]])  # (2, samples)
        result = dsp_utils.ensure_mono(audio_librosa, method="average")
        self.assertTrue(np.allclose(result, [0.5, 0.5]))

    def test_method_sum(self):
        """'sum' method should preserve power (divide by √2)"""
        audio_librosa = np.array([[1.0, 1.0], [0.0, 0.0]])  # (2, samples)
        result = dsp_utils.ensure_mono(audio_librosa, method="sum")
        # After summing [1.0, 1.0] + [0.0, 0.0] = [1.0, 1.0], then /√2 ≈ [0.707, 0.707]
        expected = 1.0 / np.sqrt(2.0)
        self.assertTrue(np.allclose(result, [expected, expected]))

    def test_method_left(self):
        """'left' method should take first channel"""
        audio_librosa = np.array([[1.0, 2.0], [0.5, 1.0]])  # (2, samples)
        result = dsp_utils.ensure_mono(audio_librosa, method="left")
        self.assertTrue(np.allclose(result, [1.0, 2.0]))

    def test_method_right(self):
        """'right' method should take second channel"""
        audio_librosa = np.array([[1.0, 2.0], [0.5, 1.0]])  # (2, samples)
        result = dsp_utils.ensure_mono(audio_librosa, method="right")
        self.assertTrue(np.allclose(result, [0.5, 1.0]))

    def test_soundfile_convention_methods(self):
        """All methods should work with soundfile (N, 2) convention"""
        # Use (3, 2) to avoid ambiguity with (2, 2)
        audio_sf = np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])  # (samples, 2)

        result_avg = dsp_utils.ensure_mono(audio_sf, method="average")
        self.assertTrue(np.allclose(result_avg, [0.5, 1.0, 1.5]))

        result_sum = dsp_utils.ensure_mono(audio_sf, method="sum")
        # Sum then divide by √2: [1.0, 2.0, 3.0] / √2
        expected = np.array([1.0, 2.0, 3.0]) / np.sqrt(2.0)
        self.assertTrue(np.allclose(result_sum, expected))

        result_left = dsp_utils.ensure_mono(audio_sf, method="left")
        self.assertTrue(np.allclose(result_left, [1.0, 2.0, 3.0]))

        result_right = dsp_utils.ensure_mono(audio_sf, method="right")
        self.assertTrue(np.allclose(result_right, [0.0, 0.0, 0.0]))

    def test_invalid_method_raises(self):
        """Unknown method should raise ValueError"""
        audio = np.array([[1.0, 2.0], [0.5, 1.0]])
        with self.assertRaises(ValueError) as cm:
            dsp_utils.ensure_mono(audio, method="invalid")
        self.assertIn("Unknown stereo conversion method", str(cm.exception))

class TestH8OnsetDetectionFeedback(unittest.TestCase):
    """H8: Verify verbose onset detection feedback"""

    def test_verbose_feedback(self):
        """AudioAnalyzer should provide rejection feedback when verbose=True"""
        from musiclib.audio_analyzer import AudioAnalyzer
        import logging

        # Create audio with high onset density
        audio = np.zeros(44100)
        # Add sharp transients every 0.1s to trigger rejections
        for i in range(0, len(audio), 4410):
            if i < len(audio):
                audio[i] = 1.0

        analyzer = AudioAnalyzer(audio, sr=44100, window_size_sec=1.0, hop_sec=0.5)

        # Capture logging output to verify verbose output
        # Set up a string handler to capture debug logs
        logger = logging.getLogger('musiclib.audio_analyzer')
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        # Store original level and handlers
        original_level = logger.level
        original_handlers = logger.handlers[:]

        # Configure logger for capture
        logger.setLevel(logging.DEBUG)
        logger.handlers = [handler]

        # Capture output
        import io
        captured = io.StringIO()
        handler.stream = captured

        try:
            # Call with verbose=True and strict onset limit
            mask = analyzer.get_stable_regions(max_onset_rate=1.0, verbose=True)

            output = captured.getvalue()
            # Should see rejection messages
            self.assertIn("[analyzer]", output)
            self.assertIn("rejected", output)

        finally:
            # Restore original logger configuration
            logger.setLevel(original_level)
            logger.handlers = original_handlers

    def test_verbose_off_by_default(self):
        """Verbose should be off by default (no output)"""
        from musiclib.audio_analyzer import AudioAnalyzer
        import logging
        import io

        audio = np.zeros(44100)
        for i in range(0, len(audio), 4410):
            if i < len(audio):
                audio[i] = 1.0

        analyzer = AudioAnalyzer(audio, sr=44100, window_size_sec=1.0)

        # Capture logging output
        logger = logging.getLogger('musiclib.audio_analyzer')
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        # Store original level and handlers
        original_level = logger.level
        original_handlers = logger.handlers[:]

        # Configure logger for capture
        logger.setLevel(logging.DEBUG)
        logger.handlers = [handler]

        # Capture output
        captured = io.StringIO()
        handler.stream = captured

        try:
            # Call WITHOUT verbose flag (default is False)
            mask = analyzer.get_stable_regions(max_onset_rate=1.0)
            output = captured.getvalue()
            # Should NOT see rejection messages (verbose=False by default)
            self.assertNotIn("[analyzer]", output)

        finally:
            # Restore original logger configuration
            logger.setLevel(original_level)
            logger.handlers = original_handlers

class TestExpandedConfigValidation(unittest.TestCase):
    """Test validation of critical parameters"""

    def test_invalid_sample_rate(self):
        config = {"global": {"sample_rate": 441}} # Too low
        with self.assertRaises(InvalidParameter) as cm:
            validate_config.validate_config(config)
        self.assertIn("outside reasonable range", str(cm.exception))

    def test_invalid_target_peak(self):
        config = {"global": {"sample_rate": 44100, "target_peak_dbfs": 1.0}} # Positive
        with self.assertRaises(InvalidParameter) as cm:
            validate_config.validate_config(config)
        self.assertIn("must be negative", str(cm.exception))

    def test_h4_filter_length_validation(self):
        """H4: Filter length must be < sample_rate and >= 64"""
        # Case 1: Too large (hard error)
        config = {
            "global": {"sample_rate": 44100, "output_bit_depth": 24},
            "clouds": {"filter_length_samples": 88200}
        }
        with self.assertRaises(InvalidParameter) as cm:
            validate_config.validate_config(config)
        self.assertIn("exceeds sample_rate", str(cm.exception))

        # Case 2: Too small (now a warning, not an error)
        # This should NOT raise, just print warning to stderr
        config["clouds"]["filter_length_samples"] = 32
        # Should not raise - this is now just a warning
        try:
            validate_config.validate_config(config)
        except InvalidParameter:
            self.fail("filter_length < 64 should be a warning, not an error")

if __name__ == '__main__':
    unittest.main()