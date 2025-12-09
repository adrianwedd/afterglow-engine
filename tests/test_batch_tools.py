import unittest
import numpy as np
import os
import shutil
import soundfile as sf
from pathlib import Path

# Import the modules to test
# We need to make sure the root dir is in path or we import relatively
import sys
sys.path.append(os.getcwd())

from dust_pads import dust_pad
from mine_silences import mine_silences
import musiclib.io_utils as io_utils

class TestBatchTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_batch_test"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_dummy_audio(self, filename, shape, sr=44100):
        """Create a dummy audio file with specific shape (samples, channels)"""
        # soundfile expects (samples, channels)
        audio = np.random.uniform(-0.5, 0.5, shape)
        path = os.path.join(self.test_dir, filename)
        sf.write(path, audio, sr)
        return path

    def test_dust_pads_channel_handling(self):
        """
        Verify that dust_pads correctly handles stereo files.
        Librosa loads as (2, N), Soundfile wants (N, 2).
        The script should detect this and transpose.
        """
        # Create "Stereo" pad: 1000 samples, 2 channels
        # saved as (1000, 2) via soundfile
        pad_path = self.create_dummy_audio("pad_stereo.wav", (1000, 2))
        hiss_path = self.create_dummy_audio("hiss_stereo.wav", (500, 2))
        out_path = os.path.join(self.test_dir, "dusted_stereo.wav")
        
        # Run dust_pad
        success = dust_pad(pad_path, hiss_path, out_path)
        self.assertTrue(success, "dust_pad should return True")
        
        # Check output
        # It should be readable by soundfile and have shape (1000, 2)
        data, sr = sf.read(out_path)
        self.assertEqual(data.shape, (1000, 2), "Output shape should match input (samples, channels)")
        
    def test_dust_pads_mono_to_stereo(self):
        """Verify mono pad gets converted to stereo if mixed with stereo hiss"""
        pad_path = self.create_dummy_audio("pad_mono.wav", (1000,))
        hiss_path = self.create_dummy_audio("hiss_stereo.wav", (500, 2))
        out_path = os.path.join(self.test_dir, "dusted_mono_stereo.wav")
        
        success = dust_pad(pad_path, hiss_path, out_path)
        self.assertTrue(success)
        
        data, sr = sf.read(out_path)
        self.assertEqual(data.shape, (1000, 2), "Mono pad should become stereo output")

    def test_mine_silences_import_and_run(self):
        """Verify mine_silences can be called programmatically without NameError"""
        # Create dummy source
        src_path = self.create_dummy_audio("source.wav", (44100 * 2,)) # 2 seconds
        
        try:
            # Should not raise ImportError or NameError
            mine_silences(src_path, self.test_dir, normalization_target_db=-12.0)
        except Exception as e:
            self.fail(f"mine_silences raised exception: {e}")

if __name__ == '__main__':
    unittest.main()
