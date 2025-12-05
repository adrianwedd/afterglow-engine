# Unified Threshold Application Fix

## Problem

Pad mining had a threshold divergence issue:
- The stability mask used pre_analysis thresholds (when enabled)
- But the window-level RMS and onset rate checks still used pad_miner defaults
- Result: A user could set strict pre_analysis RMS thresholds, but windows would still pass if pad_miner thresholds were looser

## Solution

Modified `extract_sustained_segments()` to track whether pre_analysis config has explicit threshold overrides:

1. **Detection**: Check if config['pre_analysis'] contains min_rms_db, max_rms_db, or max_onset_rate_hz
2. **Flag**: Set `use_pre_analysis_thresholds = True` if any explicit threshold is present
3. **Application**: Use pre_analysis thresholds for both mask AND window checks when flag is true
4. **Fallback**: Use pad_miner args if no explicit pre_analysis thresholds present

## Code Changes

**File**: `musiclib/segment_miner.py`

### Added threshold tracking (lines 57-60):
```python
use_pre_analysis_thresholds = False
pre_min_rms_db = min_rms_db
pre_max_rms_db = max_rms_db
pre_max_onset_rate = max_onset_rate
```

### Detection logic (lines 75-77):
```python
# If pre_analysis config has thresholds, use them for window-level checks too
if 'min_rms_db' in pre_analysis_config or 'max_rms_db' in pre_analysis_config or 'max_onset_rate_hz' in pre_analysis_config:
    use_pre_analysis_thresholds = True
```

### Window-level threshold application (lines 100-103):
```python
# Use pre-analysis thresholds if they were explicitly set, otherwise use pad_miner defaults
window_min_rms_db = pre_min_rms_db if use_pre_analysis_thresholds else min_rms_db
window_max_rms_db = pre_max_rms_db if use_pre_analysis_thresholds else max_rms_db
window_max_onset_rate = pre_max_onset_rate if use_pre_analysis_thresholds else max_onset_rate
```

## Behavior

### Scenario 1: Pre-analysis config has explicit thresholds
```python
config = {
    'pre_analysis': {
        'enabled': True,
        'max_onset_rate_hz': 0.5,  # Strict
        'min_rms_db': -25.0,       # Strict lower bound
        'max_rms_db': -20.0,       # Strict upper bound
    }
}
```
Result: Both stability mask AND window checks use strict thresholds → fewer candidates

### Scenario 2: Pre-analysis disabled or no explicit thresholds
```python
config = {
    'pre_analysis': {
        'enabled': True,
        'analysis_window_sec': 1.0,
        # No RMS/onset thresholds specified
    }
}
```
Result: Window checks use pad_miner args (unchanged behavior)

### Scenario 3: No config provided
```python
extract_sustained_segments(audio, sr, ..., config=None)
```
Result: Uses default pad_miner args throughout (unchanged behavior)

## Validation

Test case with synthetic audio:
```
Strict pre_analysis config (RMS=[-25,-20], onset_rate=0.5):
  Candidates: 0 (filters correctly)

Lenient pre_analysis config (RMS=[-50,0], onset_rate=20.0):
  Candidates: 3 (passes through)

Result: ✓ Unified threshold application confirmed
```

## Backward Compatibility

✓ 100% backward compatible
- No changes to function signatures
- Explicit threshold detection avoids affecting default behavior
- Config parameter remains optional
- All existing tests pass (9/9)

## Production Test

Full cloud generation pipeline with unified thresholds:
```
Input: 3 FLAC files (~230MB)
Output: 12 clouds generated successfully
Status: ✓ Clean and quiet (verbose disabled)
Thresholds: Unified across stability mask and window checks
```

## Impact

Users can now confidently set pre_analysis thresholds knowing they will be applied consistently throughout the pad mining pipeline. The stability mask and window-level filtering are no longer divergent.
