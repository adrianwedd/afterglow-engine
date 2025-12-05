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


def test_set_random_seed_seeds_numpy_and_random():
    dsp_utils.set_random_seed(42)
    a = np.random.rand()
    import random
    b = random.random()
    dsp_utils.set_random_seed(42)
    a2 = np.random.rand()
    random.seed(42)
    b2 = random.random()
    assert a == a2
    assert b == b2
