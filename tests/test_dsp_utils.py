import numpy as np
from musiclib import dsp_utils


def test_normalize_audio():
    sig = np.array([0.2, -0.2, 0.1], dtype=float)
    out = dsp_utils.normalize_audio(sig, target_peak_dbfs=-1.0)
    peak = np.max(np.abs(out))
    # -1 dBFS corresponds to ~0.891
    assert np.isclose(peak, 10 ** (-1 / 20), atol=1e-3)


def test_time_domain_crossfade_loop_short_guard():
    sig = np.ones(10, dtype=float)
    out = dsp_utils.time_domain_crossfade_loop(sig, crossfade_ms=0, sr=44100)
    # Should return a copy without error
    assert np.array_equal(out, sig)


def test_loop_optimization_aligns_phase():
    """Test that optimizing the loop trims the audio to align phase."""
    sr = 1000
    freq = 10.0
    # 1.5 seconds = 15 cycles. Ends perfectly on phase.
    # Let's make it 1.55 seconds so it's out of phase at the end.
    duration = 1.55 
    t = np.arange(int(sr * duration)) / sr
    audio = np.sin(2 * np.pi * freq * t)
    
    # Without optimization
    # Crossfade 100ms (0.1s)
    out_raw = dsp_utils.time_domain_crossfade_loop(audio, crossfade_ms=100, sr=sr, optimize_loop=False)
    assert len(out_raw) == len(audio)
    
    # With optimization
    # It should find that trimming ~0.05s (50 samples) aligns the phase best (back to 1.5s)
    out_opt = dsp_utils.time_domain_crossfade_loop(audio, crossfade_ms=100, sr=sr, optimize_loop=True)
    
    # It should have trimmed something
    assert len(out_opt) < len(audio)
    
    diff = len(audio) - len(out_opt)
    # Ensure some trimming happened but not more than half the buffer
    assert 1 <= diff <= len(audio) // 2
