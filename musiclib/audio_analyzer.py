"""
Audio pre-analysis module: compute and cache per-file statistics.

Provides lightweight windowed analysis (RMS, onset density, spectral centroid,
DC offset, crest factor) to identify stable, high-quality regions before
mining pads or extracting grains. All stats are precomputed once per file
and reused across modules.
"""

from typing import Tuple, Dict
import numpy as np
import librosa
from . import dsp_utils


class AudioAnalyzer:
    """Precompute and cache audio statistics for quality-aware processing."""

    def __init__(
        self,
        audio: np.ndarray,
        sr: int,
        window_size_sec: float = 1.0,
        hop_sec: float = 0.5,
    ):
        """
        Initialize analyzer with audio and window parameters.

        Args:
            audio: Input audio array (mono)
            sr: Sample rate
            window_size_sec: Analysis window size in seconds
            hop_sec: Hop size in seconds
        """
        self.audio = audio
        self.sr = sr
        self.window_size_sec = window_size_sec
        self.hop_sec = hop_sec
        self.window_size_samples = int(window_size_sec * sr)
        self.hop_samples = int(hop_sec * sr)

        # Ensure window doesn't exceed audio length
        if self.window_size_samples > len(audio):
            self.window_size_samples = len(audio)
            self.hop_samples = len(audio)

        # Precompute all metrics (cached)
        self._rms_curve = None
        self._onset_strength = None
        self._onset_frames = None
        self._spectral_centroid = None
        self._dc_offset = None
        self._crest_factor = None
        self._stability_mask = None

    def _compute_rms_curve(self) -> np.ndarray:
        """
        Compute windowed RMS energy curve.

        Returns:
            Array of RMS values (dB) for each window
        """
        if self._rms_curve is not None:
            return self._rms_curve

        rms_values = []
        for start in range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples):
            end = start + self.window_size_samples
            segment = self.audio[start:end]
            rms_db = dsp_utils.rms_energy_db(segment)
            rms_values.append(rms_db)

        self._rms_curve = np.array(rms_values) if rms_values else np.array([-80.0])
        return self._rms_curve

    def _compute_onset_density(self) -> np.ndarray:
        """
        Compute windowed onset density.

        Returns:
            Array of onset counts per window
        """
        if self._onset_frames is not None:
            return self._onset_frames

        try:
            onset_strength = librosa.onset.onset_strength(y=self.audio, sr=self.sr)
            self._onset_strength = onset_strength
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_strength, sr=self.sr, units='samples'
            )
            self._onset_frames = onset_frames
            return onset_frames
        except Exception:
            self._onset_frames = np.array([])
            return np.array([])

    def _compute_spectral_centroid(self) -> np.ndarray:
        """
        Compute windowed spectral centroid.

        Returns:
            Array of centroid frequencies (Hz) for each window
        """
        if self._spectral_centroid is not None:
            return self._spectral_centroid

        try:
            centroid = librosa.feature.spectral_centroid(y=self.audio, sr=self.sr)[0]
            self._spectral_centroid = centroid
            return centroid
        except Exception:
            self._spectral_centroid = np.array([2000.0] * len(self._compute_rms_curve()))
            return self._spectral_centroid

    def _compute_dc_offset(self) -> np.ndarray:
        """
        Compute windowed DC offset (mean absolute value).

        Returns:
            Array of DC offsets for each window
        """
        if self._dc_offset is not None:
            return self._dc_offset

        dc_values = []
        for start in range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples):
            end = start + self.window_size_samples
            segment = self.audio[start:end]
            dc = np.abs(np.mean(segment))
            dc_values.append(dc)

        self._dc_offset = np.array(dc_values) if dc_values else np.array([0.0])
        return self._dc_offset

    def _compute_crest_factor(self) -> np.ndarray:
        """
        Compute windowed crest factor (peak / RMS).

        Returns:
            Array of crest factors for each window
        """
        if self._crest_factor is not None:
            return self._crest_factor

        crest_values = []
        rms_curve = self._compute_rms_curve()
        for start in range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples):
            end = start + self.window_size_samples
            segment = self.audio[start:end]
            peak = np.max(np.abs(segment))
            rms = dsp_utils.rms_energy(segment)
            if rms > 1e-6:
                crest = peak / rms
            else:
                crest = 0.0
            crest_values.append(crest)

        self._crest_factor = np.array(crest_values) if crest_values else np.array([1.0])
        return self._crest_factor

    def get_stable_regions(
        self,
        max_onset_rate: float = 3.0,
        rms_low_db: float = -40.0,
        rms_high_db: float = -10.0,
        max_dc_offset: float = 0.1,
        max_crest: float = 10.0,
    ) -> np.ndarray:
        """
        Identify stable, high-quality regions in audio.

        A region is stable if:
        - Low onset density (not percussive)
        - RMS in mid-range (not silent, not clipped)
        - Low DC offset (no bias)
        - Reasonable crest factor (not heavily clipped)

        Args:
            max_onset_rate: Max onsets per second to accept
            rms_low_db: Min RMS (dB) to accept
            rms_high_db: Max RMS (dB) to accept
            max_dc_offset: Max absolute DC offset
            max_crest: Max crest factor

        Returns:
            Boolean mask (length = number of windows) indicating stable regions
        """
        if self._stability_mask is not None:
            return self._stability_mask

        # Get all metrics
        rms = self._compute_rms_curve()
        onset_frames = self._compute_onset_density()
        dc = self._compute_dc_offset()
        crest = self._compute_crest_factor()

        # Initialize mask (all True)
        mask = np.ones(len(rms), dtype=bool)

        # Filter by RMS
        mask &= (rms >= rms_low_db) & (rms <= rms_high_db)

        # Filter by DC offset
        mask &= dc < max_dc_offset

        # Filter by crest factor
        mask &= crest < max_crest

        # Filter by onset density
        for i, start in enumerate(
            range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples)
        ):
            end = start + self.window_size_samples
            onsets_in_window = np.sum((onset_frames >= start) & (onset_frames < end))
            onset_rate = onsets_in_window / (self.window_size_samples / self.sr)
            if onset_rate > max_onset_rate:
                mask[i] = False

        self._stability_mask = mask
        return mask

    def get_sample_range_for_window(self, window_idx: int) -> Tuple[int, int]:
        """
        Get sample range corresponding to a window index.

        Args:
            window_idx: Index into window array

        Returns:
            (start_sample, end_sample) tuple
        """
        start = window_idx * self.hop_samples
        end = min(start + self.window_size_samples, len(self.audio))
        return start, end

    def sample_from_stable_region(
        self,
        duration_sec: float,
        min_stable_windows: int = 2,
        stable_mask: np.ndarray = None,
    ) -> Tuple[int, int] or None:
        """
        Pick a random segment from stable regions.

        Args:
            duration_sec: Desired segment length
            min_stable_windows: Minimum consecutive stable windows required
            stable_mask: Pre-computed stability mask (if None, computes it)

        Returns:
            (start_sample, end_sample) tuple, or None if no valid region found
            Note: start=0 is a valid return value and not treated as failure
        """
        if stable_mask is None:
            stable_mask = self.get_stable_regions()

        if not np.any(stable_mask):
            return None

        duration_samples = int(duration_sec * self.sr)

        # Find consecutive runs of stable windows
        # Pad with False at edges to detect run boundaries
        padded = np.concatenate([[False], stable_mask, [False]])
        diff = np.diff(padded.astype(int))
        run_starts = np.where(diff == 1)[0]
        run_ends = np.where(diff == -1)[0]

        # Filter runs by minimum length
        consecutive_runs = []
        for start_idx, end_idx in zip(run_starts, run_ends):
            run_length = end_idx - start_idx
            if run_length >= min_stable_windows:
                consecutive_runs.append((start_idx, end_idx))

        if not consecutive_runs:
            return None

        # Pick a random run and choose a window from it
        chosen_run = consecutive_runs[np.random.randint(len(consecutive_runs))]
        start_window_idx, end_window_idx = chosen_run
        window_idx = np.random.randint(start_window_idx, end_window_idx)
        start, _ = self.get_sample_range_for_window(window_idx)

        # Extend to requested duration
        end = min(start + duration_samples, len(self.audio))

        return start, end

    def get_stats_for_sample(
        self, start_sample: int, end_sample: int
    ) -> Dict[str, float]:
        """
        Get analysis stats for a specific sample range.

        Args:
            start_sample: Start index
            end_sample: End index

        Returns:
            Dictionary with keys: rms_db, dc_offset, crest_factor, centroid_hz
        """
        segment = self.audio[start_sample:end_sample]

        # Compute spectral centroid, with guard for very short segments
        if len(segment) >= 512:
            if librosa is not None:
                centroid_hz = np.mean(librosa.feature.spectral_centroid(y=segment, sr=self.sr))
            else:
                # Fallback FFT-based centroid if librosa unavailable
                fft = np.fft.rfft(segment)
                freqs = np.fft.rfftfreq(len(segment), 1 / self.sr)
                magnitudes = np.abs(fft)
                if np.sum(magnitudes) > 0:
                    centroid_hz = np.sum(freqs * magnitudes) / np.sum(magnitudes)
                else:
                    centroid_hz = 2000.0
        else:
            # For very short segments, use default
            centroid_hz = 2000.0  # Neutral midrange default

        return {
            'rms_db': dsp_utils.rms_energy_db(segment),
            'dc_offset': np.abs(np.mean(segment)),
            'crest_factor': np.max(np.abs(segment)) / (dsp_utils.rms_energy(segment) + 1e-6),
            'centroid_hz': centroid_hz,
        }
