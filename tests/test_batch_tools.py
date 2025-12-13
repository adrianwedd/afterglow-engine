import unittest
import numpy as np
import os
import shutil
import soundfile as sf
from pathlib import Path
import subprocess

# Import the modules to test
# We need to make sure the root dir is in path or we import relatively
import sys
sys.path.append(os.getcwd())

from dust_pads import dust_pad
from mine_silences import mine_silences
import musiclib.io_utils as io_utils

# Import main function from curate_best
from curate_best import main as curate_best_main

class TestBatchTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_batch_test"
        os.makedirs(self.test_dir, exist_ok=True)

        # Set export root to allow writes to test directory
        self._original_export_root = os.environ.get("AFTERGLOW_EXPORT_ROOT")
        os.environ["AFTERGLOW_EXPORT_ROOT"] = os.path.abspath(self.test_dir)

    def tearDown(self):
        # Restore original export root
        if self._original_export_root is not None:
            os.environ["AFTERGLOW_EXPORT_ROOT"] = self._original_export_root
        elif "AFTERGLOW_EXPORT_ROOT" in os.environ:
            del os.environ["AFTERGLOW_EXPORT_ROOT"]

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_dummy_audio(self, full_path, shape, sr=44100, content_type="random"):
        """Create a dummy audio file with specific shape (samples, channels)"""
        # Ensure target directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if content_type == "random":
            audio = np.random.uniform(-0.5, 0.5, shape)
        elif content_type == "silent":
            audio = np.zeros(shape)
        else: # Simple sine wave for more "tonal" qualities
            # Handle shape for mono vs stereo
            if isinstance(shape, tuple) and len(shape) > 1: # Stereo
                num_samples = shape[0]
                num_channels = shape[1]
                t = np.linspace(0, num_samples/sr, num_samples, endpoint=False)
                audio = np.sin(2 * np.pi * 440 * t) * 0.2
                audio = np.column_stack([audio]*num_channels)
            else: # Mono
                num_samples = shape if isinstance(shape, int) else shape[0]
                t = np.linspace(0, num_samples/sr, num_samples, endpoint=False)
                audio = np.sin(2 * np.pi * 440 * t) * 0.2

        sf.write(full_path, audio.astype(np.float32), sr) # Ensure float32
        return full_path

    def test_dust_pads_channel_handling(self):
        """
        Verify that dust_pads correctly handles stereo files.
        Librosa loads as (2, N), Soundfile wants (N, 2).
        The script should detect this and transpose.
        """
        pad_path = self.create_dummy_audio(os.path.join(self.test_dir, "pad_stereo.wav"), (1000, 2))
        hiss_path = self.create_dummy_audio(os.path.join(self.test_dir, "hiss_stereo.wav"), (500, 2))
        out_path = os.path.join(self.test_dir, "dusted_stereo.wav")
        
        success = dust_pad(pad_path, hiss_path, out_path)
        self.assertTrue(success, "dust_pad should return True")
        
        data, sr = sf.read(out_path)
        self.assertEqual(data.shape, (1000, 2), "Output shape should match input (samples, channels)")
        
    def test_dust_pads_mono_to_stereo(self):
        """Verify mono pad gets converted to stereo if mixed with stereo hiss"""
        pad_path = self.create_dummy_audio(os.path.join(self.test_dir, "pad_mono.wav"), (1000,))
        hiss_path = self.create_dummy_audio(os.path.join(self.test_dir, "hiss_stereo.wav"), (500, 2))
        out_path = os.path.join(self.test_dir, "dusted_mono_stereo.wav")
        
        success = dust_pad(pad_path, hiss_path, out_path)
        self.assertTrue(success)
        
        data, sr = sf.read(out_path)
        self.assertEqual(data.shape, (1000, 2), "Mono pad should become stereo output")

    def test_mine_silences_import_and_run(self):
        """Verify mine_silences can be called programmatically without NameError"""
        src_path = self.create_dummy_audio(os.path.join(self.test_dir, "source.wav"), (44100 * 2,)) # 2 seconds
        
        try:
            mine_silences(src_path, self.test_dir, normalization_target_db=-12.0)
        except SystemExit as e:
            # mine_silences might exit if no silences found. This is okay for a basic run.
            self.assertEqual(e.code, 0)
        except Exception as e:
            self.fail(f"mine_silences raised exception: {e}")

        # Check if output files were created (even if 0 extracted, dir should exist)
        expected_output_dir = os.path.join(self.test_dir, "source", "silences")
        self.assertTrue(os.path.exists(expected_output_dir))


    def test_curate_best_prunes_output_dir(self):
        """
        Verify curate_best does not descend into its own output directory
        when output_root is a subdirectory of input_root.
        """
        input_root = os.path.join(self.test_dir, "input_for_curation")
        pads_dir = os.path.join(input_root, "pads")
        os.makedirs(pads_dir, exist_ok=True)
        
        self.create_dummy_audio(os.path.join(pads_dir, "pad_01.wav"), (44100,), sr=44100, content_type="sine")
        self.create_dummy_audio(os.path.join(pads_dir, "pad_02.wav"), (44100,), sr=44100, content_type="sine")

        # Create a "fake" curated file INSIDE what would be the output directory
        # This file should NOT be re-curated or cause issues.
        output_root = os.path.join(input_root, "best_of_curation")
        os.makedirs(os.path.join(output_root, "pads"), exist_ok=True)
        self.create_dummy_audio(os.path.join(output_root, "pads", "pad_curated_fake.wav"), (44100,), sr=44100, content_type="sine")

        # Capture stdout to verify logs
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        # Run curate_best with input_root being the parent of output_root
        # This will trigger the pruning logic
        class Args:
            def __init__(self, input_r, output_r, force):
                self.input_root = input_r
                self.output_root = output_r
                self.force = force
        
        try:
            curate_best_main(Args(input_root, output_root, force=True))
            
        except SystemExit as e:
            self.assertEqual(e.code, 0, "curate_best should exit with 0 on successful curation")
        finally:
            sys.stdout = old_stdout # Restore stdout

        # Verify:
        # 1. The fake curated file should not be processed (no score/pick message for it)
        # 2. Only the real pads should be picked (pad_01, pad_02)
        
        output_logs = mystdout.getvalue()
        
        self.assertNotIn("pad_curated_fake.wav", output_logs, "Fake curated file should not be processed")
        self.assertIn("pad_01.wav", output_logs, "Real pad_01 should be processed")
        self.assertIn("pad_02.wav", output_logs, "Real pad_02 should be processed")

        # Check content of the actual output directory
        output_pads_dir = os.path.join(output_root, "pads")
        self.assertTrue(os.path.exists(output_pads_dir))
        # It should contain exactly 2 files (pad_01, pad_02)
        output_files = [f for f in os.listdir(output_pads_dir) if f.endswith(".wav")]
        self.assertEqual(len(output_files), 2, "Output directory should contain only 2 curated files")
        self.assertIn("pad_01.wav", output_files)
        self.assertIn("pad_02.wav", output_files)


if __name__ == '__main__':
    unittest.main()
