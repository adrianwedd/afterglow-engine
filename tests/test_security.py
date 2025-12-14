import unittest
import os
import shutil
import sys
import tempfile
import numpy as np
from pathlib import Path

# Add project root to python path
sys.path.append(os.getcwd())

import musiclib.io_utils as io_utils
from musiclib.exceptions import PermissionError as AfterglowPermissionError

class TestPathTraversalProtection(unittest.TestCase):
    """Verify security protections against path traversal"""

    def test_symlink_escape_blocked(self):
        """Verify that symlinks cannot be used to escape export directory"""
        with tempfile.TemporaryDirectory() as tmp:
            # Create export directory
            export_dir = Path(tmp) / "export"
            export_dir.mkdir()

            # Set export root to the export directory (not tmp)
            os.environ["AFTERGLOW_EXPORT_ROOT"] = str(export_dir)

            # Create a target directory outside export (to escape to)
            outside_dir = Path(tmp) / "outside"
            outside_dir.mkdir()

            # Create a symlink inside export pointing outside
            evil_link = export_dir / "evil_link"
            try:
                evil_link.symlink_to(outside_dir, target_is_directory=True)
            except OSError:
                # Some filesystems don't support symlinks
                self.skipTest("Filesystem does not support symlinks")

            # Try to write through the symlink
            audio = np.random.randn(1000) * 0.1
            evil_path = str(evil_link / "malicious.wav")

            # Should raise PermissionError
            with self.assertRaises(AfterglowPermissionError) as cm:
                io_utils.save_audio(evil_path, audio, sr=44100, bit_depth=24)

            # Verify file was not created
            self.assertFalse((outside_dir / "malicious.wav").exists(),
                           "File should not exist outside export root")

    def test_absolute_path_outside_export_blocked(self):
        """Verify that absolute paths outside export root are blocked"""
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp) / "export"
            export_dir.mkdir()
            outside_dir = Path(tmp) / "outside"
            outside_dir.mkdir()

            os.environ["AFTERGLOW_EXPORT_ROOT"] = str(export_dir)

            audio = np.random.randn(1000) * 0.1
            evil_path = str(outside_dir / "escape.wav")

            # Should raise PermissionError
            with self.assertRaises(AfterglowPermissionError):
                io_utils.save_audio(evil_path, audio, sr=44100, bit_depth=24)

            # Verify file was not created
            self.assertFalse((outside_dir / "escape.wav").exists(),
                           "File should not exist outside export root")

class TestShellInjectionProtection(unittest.TestCase):
    """Verify security protections against shell injection"""

    def test_no_shell_execution_in_source(self):
        """Verify source code does not use os.system() or shell=True"""
        import subprocess
        result = subprocess.run(
            ['grep', '-rn', r'os\.system\|shell=True', '--include=*.py',
             'musiclib/', 'make_textures.py', 'mine_drums.py', 'mine_silences.py',
             'dust_pads.py', 'curate_best.py', 'process_batch.py'],
            capture_output=True,
            text=True
        )
        # Filter out __pycache__ and .pyc
        lines = [line for line in result.stdout.split('\n')
                 if line and '__pycache__' not in line and '.pyc' not in line]

        self.assertEqual(len(lines), 0,
                        f"Found potential shell execution: {lines}")

class TestDataValidation(unittest.TestCase):
    """Verify security protections against invalid data"""

    def test_save_audio_rejects_invalid_bit_depth(self):
        """Verify save_audio rejects invalid bit depths"""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AFTERGLOW_EXPORT_ROOT"] = tmp
            audio = np.random.randn(1000) * 0.1
            path = str(Path(tmp) / "test.wav")

            # Try invalid bit depth - should raise ValueError
            with self.assertRaises(ValueError) as cm:
                io_utils.save_audio(path, audio, sr=44100, bit_depth=32)

            # Verify error message mentions invalid bit depth
            self.assertIn("bit_depth", str(cm.exception).lower())

            # Verify file was not created
            self.assertFalse(Path(path).exists(), "File should not be created")

    def test_save_audio_accepts_valid_bit_depths(self):
        """Verify save_audio accepts 16 and 24 bit depths"""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AFTERGLOW_EXPORT_ROOT"] = tmp
            audio = np.random.randn(1000) * 0.1

            # Test 16-bit
            path_16 = str(Path(tmp) / "test16.wav")
            result_16 = io_utils.save_audio(path_16, audio, sr=44100, bit_depth=16)
            self.assertTrue(result_16, "Should accept bit_depth=16")
            self.assertTrue(Path(path_16).exists())

            # Test 24-bit
            path_24 = str(Path(tmp) / "test24.wav")
            result_24 = io_utils.save_audio(path_24, audio, sr=44100, bit_depth=24)
            self.assertTrue(result_24, "Should accept bit_depth=24")
            self.assertTrue(Path(path_24).exists())

if __name__ == '__main__':
    unittest.main()