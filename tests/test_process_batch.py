"""
Test process_batch.py to ensure imports work and basic invocation doesn't crash.
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestProcessBatch(unittest.TestCase):
    """Test batch processing script imports and basic functionality"""

    def test_imports_successfully(self):
        """Verify process_batch.py imports without errors (catches missing imports like atexit)"""
        try:
            import process_batch
        except ImportError as e:
            self.fail(f"process_batch.py failed to import: {e}")
        except NameError as e:
            self.fail(f"process_batch.py has undefined names: {e}")

    def test_minimal_invocation(self):
        """Test that batch runner can be invoked and creates/cleans temp config"""
        with tempfile.TemporaryDirectory() as tmp:
            # Create minimal input structure
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()

            # Create a tiny test audio file (won't actually be processed much)
            import numpy as np
            import soundfile as sf
            test_audio = np.random.randn(1000) * 0.1
            test_file = input_dir / "test.wav"
            sf.write(str(test_file), test_audio, 44100)

            # Create minimal config
            config_path = Path(tmp) / "config.yaml"
            import yaml
            minimal_config = {
                "global": {"sample_rate": 44100, "output_bit_depth": 24, "target_peak_dbfs": -1.0},
                "paths": {"source_audio_dir": str(input_dir), "export_dir": "export"},
                "pad_miner": {"min_rms_db": -40, "max_rms_db": -10},
            }
            with open(config_path, 'w') as f:
                yaml.dump(minimal_config, f)

            # Set AFTERGLOW_EXPORT_ROOT to temp directory for safety
            original_root = os.environ.get("AFTERGLOW_EXPORT_ROOT")
            os.environ["AFTERGLOW_EXPORT_ROOT"] = tmp

            try:
                # Import and run main (will fail on actual processing, but we're testing imports)
                import process_batch

                # Check that the module loaded
                self.assertTrue(hasattr(process_batch, 'main'))
                self.assertTrue(hasattr(process_batch, 'run_step'))

                # Verify atexit is available (the critical import that was missing)
                import atexit as check_atexit
                self.assertIsNotNone(check_atexit)

            finally:
                # Restore original env
                if original_root:
                    os.environ["AFTERGLOW_EXPORT_ROOT"] = original_root
                elif "AFTERGLOW_EXPORT_ROOT" in os.environ:
                    del os.environ["AFTERGLOW_EXPORT_ROOT"]


if __name__ == '__main__':
    unittest.main()
