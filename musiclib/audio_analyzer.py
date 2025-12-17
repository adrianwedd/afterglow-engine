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
from .logger import get_logger
from .exceptions import AudioError

logger = get_logger(__name__)


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

        Raises:
            ValueError: If parameters are invalid (negative/zero sample rate, etc.)
        """
        # Validate parameters
        if sr <= 0:
            raise ValueError(f"Sample rate must be positive, got {sr}")

        if window_size_sec <= 0:
            raise ValueError(f"Window size must be positive, got {window_size_sec}")

        if hop_sec < 0:
            raise ValueError(f"Hop size must be non-negative, got {hop_sec}")

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
        self._stft_cache = None  # Shared STFT for onset and spectral analysis

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

    def _get_stft(self) -> np.ndarray:
        """
        Compute and cache STFT for reuse across spectral features.

        This eliminates redundant STFT computation when multiple spectral
        features (onset strength, spectral centroid) are needed.

        Returns:
            Complex STFT matrix (shape: freq_bins x time_frames)
        """
        if self._stft_cache is None:
            self._stft_cache = librosa.stft(y=self.audio)
        return self._stft_cache

    def _compute_onset_density(self) -> np.ndarray:
        """
        Compute windowed onset density.

        Returns:
            Array of onset counts per window
        """
        if self._onset_frames is not None:
            return self._onset_frames

        try:
            # Use cached STFT to avoid redundant computation
            S = self._get_stft()
            onset_strength = librosa.onset.onset_strength(S=S, sr=self.sr)
            self._onset_strength = onset_strength
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_strength, sr=self.sr, units='samples'
            )
            self._onset_frames = onset_frames
            return onset_frames
        except Exception as e:
            # Fallback for very short audio or other edge cases
            logger.debug(f"Onset detection failed, using empty array fallback: {e}")
            self._onset_frames = np.array([])
            return np.array([])

    def _compute_spectral_centroid(self) -> np.ndarray:
        """
        Compute windowed spectral centroid.

        Returns:
            Array of centroid frequencies (Hz) for each analysis window
        """
        if self._spectral_centroid is not None:
            return self._spectral_centroid

        try:
            # Use cached STFT to avoid redundant computation
            S = self._get_stft()
            # Get per-STFT-frame centroid values
            # spectral_centroid needs power spectrogram (magnitude squared)
            S_power = np.abs(S)**2
            centroid_frames = librosa.feature.spectral_centroid(S=S_power, sr=self.sr)[0]

            # Average centroid over each analysis window
            # (STFT hop is typically 512 samples; analysis hop is ~22050 samples)
            centroid_values = []
            stft_hop_length = 512  # librosa default
            for start in range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples):
                end = start + self.window_size_samples
                # Map analysis window to STFT frame indices
                start_frame = librosa.samples_to_frames(start, hop_length=stft_hop_length)
                end_frame = librosa.samples_to_frames(end, hop_length=stft_hop_length)
                # Average centroid over this window's frames
                if end_frame > start_frame and end_frame <= len(centroid_frames):
                    avg_centroid = np.mean(centroid_frames[start_frame:end_frame])
                elif start_frame < len(centroid_frames):
                    avg_centroid = np.mean(centroid_frames[start_frame:])
                else:
                    avg_centroid = 2000.0  # Fallback for edge case
                centroid_values.append(avg_centroid)

            self._spectral_centroid = np.array(centroid_values) if centroid_values else np.array([2000.0])
            return self._spectral_centroid
        except Exception as e:
            # Fallback for very short audio or other edge cases
            logger.debug(f"Spectral centroid computation failed, using neutral fallback: {e}")
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
            # Use conservative threshold to avoid division by zero / floating point issues
            if rms > 1e-10:
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
        centroid_low_hz: float = None,
        centroid_high_hz: float = None,
        verbose: bool = False,
    ) -> np.ndarray:
        """
        Identify stable, high-quality regions in audio.

        A region is stable if:
        - Low onset density (not percussive)
        - RMS in mid-range (not silent, not clipped)
        - Low DC offset (no bias)
        - Reasonable crest factor (not heavily clipped)
        - (Optional) Spectral centroid within tonal range

        Args:
            max_onset_rate: Max onsets per second to accept
            rms_low_db: Min RMS (dB) to accept
            rms_high_db: Max RMS (dB) to accept
            max_dc_offset: Max absolute DC offset
            max_crest: Max crest factor
            centroid_low_hz: Min spectral centroid (Hz)
            centroid_high_hz: Max spectral centroid (Hz)
            verbose: If True, log rejection reasons for debugging

        Returns:
            Boolean mask (length = number of windows) indicating stable regions
        """
        cache_key = (
            max_onset_rate,
            rms_low_db,
            rms_high_db,
            max_dc_offset,
            max_crest,
            centroid_low_hz,
            centroid_high_hz,
            self.window_size_sec,
            self.hop_sec,
        )
        if isinstance(self._stability_mask, dict) and cache_key in self._stability_mask:
            return self._stability_mask[cache_key]
        if self._stability_mask is None:
            self._stability_mask = {}

        # Get all metrics
        rms = self._compute_rms_curve()
        onset_frames = self._compute_onset_density()
        dc = self._compute_dc_offset()
        crest = self._compute_crest_factor()

        # Initialize mask (all True)
        mask = np.ones(len(rms), dtype=bool)

        # Filter by RMS
        rms_mask = (rms >= rms_low_db) & (rms <= rms_high_db)
        if verbose:
            for i, passes in enumerate(rms_mask):
                if not passes and mask[i]:
                    logger.debug(f"  [analyzer] Window {i} rejected: RMS {rms[i]:.1f} dB outside [{rms_low_db}, {rms_high_db}]")
        mask &= rms_mask

        # Filter by DC offset
        dc_mask = dc < max_dc_offset
        if verbose:
            for i, passes in enumerate(dc_mask):
                if not passes and mask[i]:
                    logger.debug(f"  [analyzer] Window {i} rejected: DC offset {dc[i]:.4f} >= {max_dc_offset}")
        mask &= dc_mask

        # Filter by crest factor
        crest_mask = crest < max_crest
        if verbose:
            for i, passes in enumerate(crest_mask):
                if not passes and mask[i]:
                    logger.debug(f"  [analyzer] Window {i} rejected: Crest factor {crest[i]:.2f} >= {max_crest}")
        mask &= crest_mask

        # Filter by spectral centroid (optional tonal gate)
        if centroid_low_hz is not None or centroid_high_hz is not None:
            centroid = self._compute_spectral_centroid()
            if centroid_low_hz is not None:
                centroid_low_mask = centroid >= centroid_low_hz
                if verbose:
                    for i, passes in enumerate(centroid_low_mask):
                        if not passes and mask[i]:
                            logger.debug(f"  [analyzer] Window {i} rejected: Centroid {centroid[i]:.1f} Hz < {centroid_low_hz}")
                mask &= centroid_low_mask
            if centroid_high_hz is not None:
                centroid_high_mask = centroid <= centroid_high_hz
                if verbose:
                    for i, passes in enumerate(centroid_high_mask):
                        if not passes and mask[i]:
                            logger.debug(f"  [analyzer] Window {i} rejected: Centroid {centroid[i]:.1f} Hz > {centroid_high_hz}")
                mask &= centroid_high_mask

        # Filter by onset density
        for i, start in enumerate(
            range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples)
        ):
            end = start + self.window_size_samples
            onsets_in_window = np.sum((onset_frames >= start) & (onset_frames < end))
            onset_rate = onsets_in_window / (self.window_size_samples / self.sr)
            if onset_rate > max_onset_rate:
                if verbose and mask[i]:
                    logger.debug(f"  [analyzer] Window {i} rejected: Onset rate {onset_rate:.2f} > {max_onset_rate}")
                mask[i] = False

        self._stability_mask[cache_key] = mask
        return self._stability_mask[cache_key]

    def get_sorted_windows(
        self,
        rms_low_db: float = -40.0,
        rms_high_db: float = -10.0,
        max_dc_offset: float = 0.1,
        max_crest: float = 10.0,
        centroid_low_hz: float = None,
        centroid_high_hz: float = None,
    ) -> np.ndarray:
        """
        Return window indices sorted by stability (most stable first).
        
        Primary ranking metric: Onset density (ascending).
        Secondary ranking metric: RMS energy (distance from -24dB ideal).

        Windows failing RMS/DC/crest/centroid gates are excluded first. If that
        yields no candidates, all windows are considered.

        Returns:
            Array of window indices.
        """
        onset_frames = self._compute_onset_density()
        rms = self._compute_rms_curve()
        dc = self._compute_dc_offset()
        crest = self._compute_crest_factor()
        centroid = None
        if centroid_low_hz is not None or centroid_high_hz is not None:
            centroid = self._compute_spectral_centroid()
        
        window_onset_counts = []
        window_rms_scores = []
        keep_mask = []
        
        for i, start in enumerate(range(0, len(self.audio) - self.window_size_samples + 1, self.hop_samples)):
            end = start + self.window_size_samples

            keep = True
            if not (rms_low_db <= rms[i] <= rms_high_db):
                keep = False
            if dc[i] >= max_dc_offset:
                keep = False
            if crest[i] >= max_crest:
                keep = False
            if centroid is not None:
                if centroid_low_hz is not None and centroid[i] < centroid_low_hz:
                    keep = False
                if centroid_high_hz is not None and centroid[i] > centroid_high_hz:
                    keep = False
            keep_mask.append(keep)
            
            # Onset count
            count = np.sum((onset_frames >= start) & (onset_frames < end))
            window_onset_counts.append(count)
            
            # RMS score: distance from ideal -24dB (lower distance is better)
            # We use the already computed window RMS
            dist = abs(rms[i] - (-24.0))
            window_rms_scores.append(dist)
            
        keep_mask = np.array(keep_mask, dtype=bool)
        if not np.any(keep_mask):
            keep_mask = np.ones_like(keep_mask, dtype=bool)

        window_onset_counts = np.array(window_onset_counts)
        window_rms_scores = np.array(window_rms_scores)

        # Lexical sort: primary=onsets (ascending), secondary=rms_dist (ascending)
        # np.lexsort sorts by last key first, so we pass (rms, onsets)
        sorted_indices = np.lexsort((window_rms_scores, window_onset_counts))
        return sorted_indices[keep_mask[sorted_indices]]

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
