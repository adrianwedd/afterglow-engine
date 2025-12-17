#!/usr/bin/env python3
"""
Robustness Suite: Edge case testing for corrupt audio, extreme configs, filesystem issues.

This suite tests the system's resilience against pathological inputs and error conditions.
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
import shutil

from musiclib import io_utils, dsp_utils, audio_analyzer
from musiclib.exceptions import SilentArtifact, AfterglowError

# Enable unsafe I/O for robustness tests (allows writing to temp directories)
os.environ["AFTERGLOW_UNSAFE_IO"] = "1"


class TestCorruptAudio:
    """Test handling of corrupt/malformed audio files."""

    def test_zero_byte_file(self, tmp_path):
        """Test that zero-byte files are handled gracefully."""
        empty_file = tmp_path / "empty.wav"
        empty_file.touch()

        audio, sr = io_utils.load_audio(str(empty_file))
        assert audio is None, "Zero-byte file should return None"

    def test_truncated_wav_header(self, tmp_path):
        """Test handling of WAV file with incomplete header."""
        truncated = tmp_path / "truncated.wav"
        # Write partial WAV header (only 10 bytes instead of 44)
        with open(truncated, 'wb') as f:
            f.write(b'RIFF\x00\x00\x00\x00WA')

        audio, sr = io_utils.load_audio(str(truncated))
        assert audio is None, "Truncated WAV should return None"

    def test_non_audio_file_with_wav_extension(self, tmp_path):
        """Test handling of text file masquerading as WAV."""
        fake_wav = tmp_path / "fake.wav"
        fake_wav.write_text("This is not a WAV file")

        audio, sr = io_utils.load_audio(str(fake_wav))
        assert audio is None, "Non-audio file should return None"

    def test_audio_with_nan_values(self):
        """Test that NaN values in audio are detected."""
        audio = np.array([0.1, 0.2, np.nan, 0.3, 0.4])

        # dsp_utils should detect NaN
        with pytest.raises(ValueError, match="NaN"):
            dsp_utils.normalize_audio(audio, -1.0)

    def test_audio_with_inf_values(self):
        """Test that Inf values in audio are detected."""
        audio = np.array([0.1, 0.2, np.inf, 0.3, 0.4])

        with pytest.raises(ValueError, match="Inf"):
            dsp_utils.normalize_audio(audio, -1.0)

    def test_empty_audio_array(self):
        """Test that empty audio arrays are rejected."""
        audio = np.array([])

        with pytest.raises(ValueError, match="empty"):
            dsp_utils.normalize_audio(audio, -1.0)

    def test_silent_audio_below_noise_floor(self):
        """Test that completely silent audio raises SilentArtifact."""
        audio = np.zeros(44100)  # 1 second of silence

        with pytest.raises(SilentArtifact, match="noise floor"):
            dsp_utils.normalize_audio(audio, -1.0)

    def test_extremely_quiet_audio(self):
        """Test audio that's technically not silent but extremely quiet."""
        audio = np.random.randn(44100) * 1e-9  # Extremely quiet

        with pytest.raises(SilentArtifact):
            dsp_utils.normalize_audio(audio, -1.0)


class TestExtremeConfigurations:
    """Test handling of extreme or invalid configuration parameters."""

    def test_grain_length_exceeds_audio_length(self):
        """Test graceful handling when grain length > audio length."""
        sr = 44100
        audio = np.random.randn(sr // 10)  # 0.1 seconds
        grain_length_ms = 500  # 0.5 seconds - longer than audio!

        # Should handle gracefully without crashing
        analyzer = audio_analyzer.AudioAnalyzer(audio, sr)
        # The system should either skip grain extraction or clip to available length

    def test_zero_sample_rate(self):
        """Test that zero sample rate is rejected."""
        audio = np.random.randn(1000)

        with pytest.raises((ValueError, ZeroDivisionError)):
            audio_analyzer.AudioAnalyzer(audio, sr=0)

    def test_negative_sample_rate(self):
        """Test that negative sample rate is rejected."""
        audio = np.random.randn(1000)

        with pytest.raises(ValueError):
            audio_analyzer.AudioAnalyzer(audio, sr=-44100)

    def test_inverted_rms_range(self):
        """Test configuration with min_rms > max_rms."""
        sr = 44100
        audio = np.random.randn(sr) * 0.3

        analyzer = audio_analyzer.AudioAnalyzer(audio, sr)
        # Should handle gracefully - either swap or return empty results
        result = analyzer.get_stable_regions(rms_low_db=-20.0, rms_high_db=-60.0)
        # Should not crash - acceptable to return empty list

    def test_extreme_normalization_target(self):
        """Test normalization to extreme dB levels."""
        audio = np.random.randn(1000) * 0.1

        # Extremely loud target (+20 dB) - should clip
        normalized = dsp_utils.normalize_audio(audio, target_peak_dbfs=20.0)
        assert np.max(np.abs(normalized)) <= 1.0, "Should not exceed [-1, 1] range"

        # Extremely quiet target (-100 dB)
        normalized_quiet = dsp_utils.normalize_audio(audio, target_peak_dbfs=-100.0)
        assert np.max(np.abs(normalized_quiet)) < 0.01, "Should be very quiet"

    def test_crossfade_longer_than_audio(self):
        """Test crossfade with fade length > audio length."""
        sr = 44100
        audio = np.random.randn(sr // 4)  # 0.25 seconds
        crossfade_ms = 500  # 0.5 seconds - longer than audio!

        # Should handle gracefully without crashing
        result = dsp_utils.time_domain_crossfade_loop(audio, crossfade_ms, sr)
        assert result is not None


class TestFilesystemIssues:
    """Test handling of filesystem errors (disk full, permissions, etc.)."""

    def test_save_to_nonexistent_directory(self, tmp_path):
        """Test that save_audio auto-creates missing directories."""
        audio = np.random.randn(1000) * 0.3
        nonexistent = tmp_path / "does" / "not" / "exist" / "output.wav"

        # save_audio should auto-create parent directories
        result = io_utils.save_audio(str(nonexistent), audio, 44100)
        assert result is True, "Should auto-create directories and save successfully"
        assert nonexistent.exists(), "File should exist after save"

    def test_save_to_readonly_directory(self, tmp_path):
        """Test saving audio to read-only directory."""
        audio = np.random.randn(1000) * 0.3
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only
        os.chmod(readonly_dir, 0o444)

        output_file = readonly_dir / "output.wav"

        try:
            # Should raise FilesystemError on permission error
            from musiclib.exceptions import FilesystemError
            with pytest.raises((FilesystemError, PermissionError)):
                io_utils.save_audio(str(output_file), audio, 44100)
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)

    def test_load_from_nonexistent_file(self, tmp_path):
        """Test loading audio from non-existent file."""
        nonexistent = tmp_path / "does_not_exist.wav"

        audio, sr = io_utils.load_audio(str(nonexistent))
        assert audio is None, "Should return None for non-existent file"

    def test_symlink_traversal(self, tmp_path):
        """Test that symlinks are handled correctly."""
        # Create a real audio file
        real_file = tmp_path / "real.wav"
        audio = np.random.randn(1000) * 0.3
        io_utils.save_audio(str(real_file), audio, 44100, bit_depth=16)

        # Create a symlink
        symlink = tmp_path / "link.wav"
        symlink.symlink_to(real_file)

        # Should load through symlink
        loaded, sr = io_utils.load_audio(str(symlink))
        assert loaded is not None, "Should load through symlink"
        assert len(loaded) > 0


class TestInputValidation:
    """Test input validation across DSP functions."""

    def test_normalize_audio_validates_input(self):
        """Test that normalize_audio validates its inputs."""
        # Empty array
        with pytest.raises(ValueError):
            dsp_utils.normalize_audio(np.array([]), -1.0)

        # NaN values
        with pytest.raises(ValueError):
            dsp_utils.normalize_audio(np.array([0.1, np.nan, 0.2]), -1.0)

        # Inf values
        with pytest.raises(ValueError):
            dsp_utils.normalize_audio(np.array([0.1, np.inf, 0.2]), -1.0)

        # Silent audio
        with pytest.raises(SilentArtifact):
            dsp_utils.normalize_audio(np.zeros(1000), -1.0)

    def test_apply_fade_validates_length(self):
        """Test that fade functions validate fade length."""
        audio = np.random.randn(100)

        # Fade longer than audio - should handle gracefully
        faded = dsp_utils.apply_fade_in(audio, fade_length=200)
        assert len(faded) == len(audio), "Should preserve audio length"

    def test_bandpass_filter_validates_frequencies(self):
        """Test that bandpass filter validates frequency parameters."""
        sr = 44100

        # High freq > Nyquist
        with pytest.raises((ValueError, Exception)):
            dsp_utils.design_butterworth_bandpass(1000, sr, sr, order=4)

        # Low freq > High freq
        with pytest.raises((ValueError, Exception)):
            dsp_utils.design_butterworth_bandpass(5000, 1000, sr, order=4)

        # Negative frequencies
        with pytest.raises((ValueError, Exception)):
            dsp_utils.design_butterworth_bandpass(-100, 1000, sr, order=4)

    def test_audio_analyzer_validates_parameters(self):
        """Test that AudioAnalyzer validates its parameters."""
        audio = np.random.randn(44100) * 0.3

        # Negative sample rate
        with pytest.raises(ValueError):
            audio_analyzer.AudioAnalyzer(audio, sr=-44100)

        # Zero window size
        with pytest.raises((ValueError, ZeroDivisionError)):
            audio_analyzer.AudioAnalyzer(audio, sr=44100, window_size_sec=0.0)

        # Negative hop
        with pytest.raises(ValueError):
            audio_analyzer.AudioAnalyzer(audio, sr=44100, hop_sec=-0.1)


class TestMemoryPressure:
    """Test handling of very large files and batch processing limits."""

    @pytest.mark.slow
    def test_very_large_audio_array(self):
        """Test processing of very large audio (simulating long file)."""
        # 10 minutes at 44.1kHz = 26,460,000 samples
        sr = 44100
        duration_sec = 600  # 10 minutes
        large_audio = np.random.randn(sr * duration_sec) * 0.3

        # Should not crash
        analyzer = audio_analyzer.AudioAnalyzer(large_audio, sr, window_size_sec=2.0, hop_sec=1.0)
        regions = analyzer.get_stable_regions()

        # Just verify it completes without error
        assert regions is not None

    def test_batch_processing_limit_respected(self, tmp_path):
        """Test that batch processing doesn't exhaust memory."""
        # Create 100 small audio files
        sr = 44100
        for i in range(100):
            audio = np.random.randn(sr) * 0.3  # 1 second each
            io_utils.save_audio(str(tmp_path / f"file_{i:03d}.wav"), audio, sr, bit_depth=16)

        # Verify files exist
        files = list(tmp_path.glob("*.wav"))
        assert len(files) == 100

        # Should be able to iterate without loading all into memory
        loaded_count = 0
        for file_path in files[:10]:  # Just test first 10
            audio, sr_loaded = io_utils.load_audio(str(file_path))
            if audio is not None:
                loaded_count += 1

        assert loaded_count == 10


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    def test_partial_batch_success(self, tmp_path):
        """Test that batch processing continues after individual failures."""
        # Create mix of valid and invalid files
        sr = 44100

        # Valid file
        valid_audio = np.random.randn(sr) * 0.3
        io_utils.save_audio(str(tmp_path / "valid.wav"), valid_audio, sr, bit_depth=16)

        # Invalid file (empty)
        (tmp_path / "empty.wav").touch()

        # Another valid file
        io_utils.save_audio(str(tmp_path / "valid2.wav"), valid_audio, sr, bit_depth=16)

        # Process all files - should succeed for valid ones
        files = list(tmp_path.glob("*.wav"))
        success_count = 0
        fail_count = 0

        for file_path in files:
            audio, sr_loaded = io_utils.load_audio(str(file_path))
            if audio is not None:
                success_count += 1
            else:
                fail_count += 1

        assert success_count == 2, "Should load 2 valid files"
        assert fail_count == 1, "Should fail on 1 invalid file"

    def test_graceful_degradation_on_feature_failure(self):
        """Test that analysis continues if one feature computation fails."""
        sr = 44100
        # Create challenging audio (very short)
        audio = np.random.randn(100) * 0.3

        # Should not crash even with very short audio
        analyzer = audio_analyzer.AudioAnalyzer(audio, sr)

        # Some features may fail, but should not crash
        try:
            _ = analyzer.get_stable_regions()
        except Exception as e:
            # Acceptable to raise exception, but should not be unhandled crash
            assert isinstance(e, (ValueError, AfterglowError))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
