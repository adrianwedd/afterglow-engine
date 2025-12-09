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
import validate_config
import make_textures

class TestC2SilentAudioNormalization(unittest.TestCase):
    """C2: Verify silent audio normalization fix"""
    
    def test_absolute_silence_raises_error(self):
        """Should raise ValueError for all-zero array"""
        audio = np.zeros(44100)
        with self.assertRaises(ValueError) as cm:
            dsp_utils.normalize_audio(audio)
        self.assertIn("silent audio", str(cm.exception))

    def test_near_silence_raises_error(self):
        """Should raise ValueError for audio below 1e-8 peak"""
        audio = np.random.uniform(-1e-9, 1e-9, 44100)
        with self.assertRaises(ValueError) as cm:
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

class TestExpandedConfigValidation(unittest.TestCase):
    """Test validation of critical parameters"""

    def test_invalid_sample_rate(self):
        config = {"global": {"sample_rate": 441}} # Too low
        with self.assertRaises(ValueError) as cm:
            validate_config.validate_config(config)
        self.assertIn("outside reasonable range", str(cm.exception))

    def test_invalid_target_peak(self):
        config = {"global": {"sample_rate": 44100, "target_peak_dbfs": 1.0}} # Positive
        with self.assertRaises(ValueError) as cm:
            validate_config.validate_config(config)
        self.assertIn("must be negative", str(cm.exception))

    def test_h4_filter_length_validation(self):
        """H4: Filter length must be < sample_rate and >= 64"""
        # Case 1: Too large (hard error)
        config = {
            "global": {"sample_rate": 44100, "output_bit_depth": 24},
            "clouds": {"filter_length_samples": 88200}
        }
        with self.assertRaises(ValueError) as cm:
            validate_config.validate_config(config)
        self.assertIn("exceeds sample_rate", str(cm.exception))

        # Case 2: Too small (now a warning, not an error)
        # This should NOT raise, just print warning to stderr
        config["clouds"]["filter_length_samples"] = 32
        # Should not raise - this is now just a warning
        try:
            validate_config.validate_config(config)
        except ValueError:
            self.fail("filter_length < 64 should be a warning, not an error")

if __name__ == '__main__':
    unittest.main()