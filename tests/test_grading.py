import pytest
from musiclib import dsp_utils

def test_grade_audio():
    """Test grading logic with various metadata profiles."""
    # Thresholds
    thresholds = {
        "min_rms_db": -60.0,
        "clipping_tolerance": 0.01,
        "max_crest_factor": 25.0
    }

    # 1. Perfect Audio (Grade A)
    meta_a = {
        "rms_db": -20.0,       # Well above min (-60 + 15 = -45)
        "peak": 0.8,           # < 0.99
        "crest_factor": 10.0,  # < 25 * 0.6 = 15
        "loop_error_db": -40.0 # < -30
    }
    assert dsp_utils.grade_audio(meta_a, thresholds) == "A"

    # 2. Good but not perfect (Grade B) - High Loop Error
    meta_b_loop = meta_a.copy()
    meta_b_loop["loop_error_db"] = -10.0
    assert dsp_utils.grade_audio(meta_b_loop, thresholds) == "B"

    # 3. Good but not perfect (Grade B) - High Crest
    meta_b_crest = meta_a.copy()
    meta_b_crest["crest_factor"] = 20.0 # > 15 but < 25
    assert dsp_utils.grade_audio(meta_b_crest, thresholds) == "B"

    # 4. Fail (Grade F) - Silence
    meta_f_silent = meta_a.copy()
    meta_f_silent["rms_db"] = -70.0
    assert dsp_utils.grade_audio(meta_f_silent, thresholds) == "F"

    # 5. Fail (Grade F) - Clipping
    meta_f_clip = meta_a.copy()
    meta_f_clip["peak"] = 1.0
    assert dsp_utils.grade_audio(meta_f_clip, thresholds) == "F"

    # 6. Fail (Grade F) - Extreme Crest (transient garbage)
    meta_f_crest = meta_a.copy()
    meta_f_crest["crest_factor"] = 50.0
    assert dsp_utils.grade_audio(meta_f_crest, thresholds) == "F"
