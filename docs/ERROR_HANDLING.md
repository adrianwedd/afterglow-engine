# Error Handling

*Graceful failure in sonic archaeology.*

---

## Overview

Afterglow-engine v0.9 uses a custom exception hierarchy that:
- Provides domain-specific error types
- Includes contextual debugging information
- Maintains the "sonic archaeology" philosophical tone
- Enables graceful degradation in batch processing

---

## Exception Hierarchy

```
AfterglowError (base)
├── AudioError
│   ├── SilentArtifact - Audio below noise floor
│   ├── ClippedArtifact - Audio exceeds safe levels
│   └── ArchaeologyFailed - General audio processing failure
├── ConfigurationError
│   └── InvalidParameter - Invalid configuration value
├── FilesystemError
│   ├── DiskFullError - Insufficient disk space
│   ├── AfterglowPermissionError - Path outside export root
│   └── (PermissionError, IOError) - Standard I/O errors
└── ProcessingError
    ├── STFTError - STFT computation failed
    └── GrainExtractionError - Grain extraction failed
```

---

## Common Exceptions

### SilentArtifact

Raised when audio is too quiet to process (peak < 1e-8).

**When**: Normalizing, analyzing, or processing near-silent audio

**Example**:
```python
from musiclib.exceptions import SilentArtifact
import musiclib.dsp_utils as dsp_utils

try:
    normalized = dsp_utils.normalize_audio(audio, -1.0)
except SilentArtifact as e:
    logger.warning(f"Cannot normalize: {e}")
    logger.debug(f"Context: {e.context}")  # {'peak': 1.2e-9, 'rms_db': -120.5}
    # Handle gracefully - skip this audio or use different processing
```

**Recovery**:
- Skip the file in batch processing
- Try a different normalization target
- Check if input file is corrupt

### ClippedArtifact

Raised when audio contains clipping (samples at ±1.0).

**When**: Loading or analyzing heavily compressed audio

**Example**:
```python
try:
    audio, sr = io_utils.load_audio("overcompressed.wav")
except ClippedArtifact as e:
    logger.warning(f"Audio is clipped: {e}")
    # Proceed with caution or apply de-clipping
```

**Recovery**:
- Proceed anyway (clipping already happened)
- Apply gentle compression to reduce peaks
- Re-export source at lower level

### AfterglowPermissionError

Raised when attempting to write outside the export root directory.

**When**: Saving files to unapproved paths

**Example**:
```python
from musiclib.exceptions import AfterglowPermissionError

try:
    io_utils.save_audio("/tmp/sensitive_data.wav", audio, sr)
except AfterglowPermissionError as e:
    logger.error(f"Security violation: {e}")
    logger.debug(f"Requested: {e.context['requested_path']}")
    logger.debug(f"Export root: {e.context['export_root']}")
```

**Recovery**:
- Use proper export directory
- Set `AFTERGLOW_EXPORT_ROOT` environment variable
- For testing: set `AFTERGLOW_UNSAFE_IO=1`

### DiskFullError

Raised when insufficient disk space for output.

**When**: Saving large batch outputs

**Example**:
```python
from musiclib.exceptions import DiskFullError

try:
    io_utils.save_audio("output.wav", large_audio, sr)
except DiskFullError as e:
    logger.error(f"Disk full: {e}")
    available_mb = e.context['available_bytes'] / 1024 / 1024
    needed_mb = e.context['needed_bytes'] / 1024 / 1024
    logger.error(f"Need {needed_mb:.1f} MB, have {available_mb:.1f} MB")
```

**Recovery**:
- Free disk space
- Change export directory to larger volume
- Reduce output quality/duration

---

## Error Handling Patterns

### Pattern 1: Graceful Degradation (Batch Processing)

```python
from musiclib.logger import get_logger, log_success

logger = get_logger(__name__)

success_count = 0
fail_count = 0

for file_path in audio_files:
    try:
        audio, sr = io_utils.load_audio(file_path)
        if audio is None:
            logger.warning(f"Skipping corrupt file: {file_path}")
            fail_count += 1
            continue

        # Process audio...
        result = process_audio(audio, sr)

        # Save result...
        if io_utils.save_audio(output_path, result, sr):
            success_count += 1
        else:
            fail_count += 1

    except SilentArtifact as e:
        logger.warning(f"Skipping silent audio: {file_path}")
        logger.debug(str(e))
        fail_count += 1
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        logger.debug("Full traceback:", exc_info=True)
        fail_count += 1

log_success(logger, f"Processed {success_count} files ({fail_count} failed)")
```

### Pattern 2: Fail-Fast (CI/CD or --strict mode)

```python
import sys

try:
    result = process_critical_file(audio_file)
except AfterglowError as e:
    logger.error(f"Critical failure: {e}")
    logger.debug(f"Context: {e.context}")
    sys.exit(1)  # Exit immediately
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    logger.debug("Full traceback:", exc_info=True)
    sys.exit(2)
```

### Pattern 3: Retry with Fallback

```python
def extract_grains_robust(audio, sr):
    """Extract grains with fallback to looser quality filters."""
    try:
        # Try with strict quality filters
        grains = granular_maker.extract_grains(
            audio, sr, quality_threshold=0.8
        )
        if len(grains) < 10:
            raise GrainExtractionError("Low grain yield", context={'count': len(grains)})
        return grains

    except GrainExtractionError as e:
        logger.warning(f"Strict extraction failed: {e}")
        logger.info("Retrying with relaxed quality filters...")

        # Fallback: looser filters
        grains = granular_maker.extract_grains(
            audio, sr, quality_threshold=0.5
        )

        if len(grains) < 5:
            raise  # Give up

        logger.info(f"Extracted {len(grains)} grains with relaxed filters")
        return grains
```

---

## Raising Exceptions with Context

### Good: Rich Context

```python
from musiclib.exceptions import SilentArtifact

peak = np.max(np.abs(audio))
rms_db = dsp_utils.rms_energy_db(audio)

if peak < 1e-8:
    raise SilentArtifact(
        f"Audio below noise floor (peak={peak:.2e})",
        context={
            'peak': peak,
            'rms_db': rms_db,
            'duration_sec': len(audio) / sr,
            'suggested_action': 'Check source file or increase gain'
        }
    )
```

### Bad: Generic Message

```python
# Don't do this
if peak < 1e-8:
    raise ValueError("Audio too quiet")  # No context, generic exception
```

---

## Exit Codes

For CLI scripts and CI/CD:

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | All files processed |
| 1 | Partial failure | Some files failed, some succeeded |
| 2 | Critical failure | Configuration error, no output |
| 3 | User error | Invalid arguments |

**Implementation**:
```python
import sys

if success_count == 0 and fail_count > 0:
    sys.exit(2)  # Critical failure
elif fail_count > 0:
    sys.exit(1)  # Partial failure
else:
    sys.exit(0)  # Success
```

---

## Debugging with Context

All custom exceptions include a `context` dict for debugging:

```python
try:
    io_utils.save_audio(path, audio, sr)
except AfterglowPermissionError as e:
    print(f"Error: {e}")
    print(f"Context: {e.context}")
    # Output:
    # Error: Path is outside export root
    # Context: {'export_root': '/path/to/export', 'requested_path': '/tmp/file.wav'}
```

---

## Philosophy

Error handling in afterglow-engine reflects the "sonic archaeology" metaphor:

- **SilentArtifact**: The excavation site yielded no recoverable material
- **ClippedArtifact**: The artifact shows signs of damage during recovery
- **ArchaeologyFailed**: The excavation could not proceed
- **AfterglowPermissionError**: The dig site is restricted

Errors are not failures - they're information about the state of the dig.

---

## Best Practices

1. **Catch Specific Exceptions**: Use `except SilentArtifact` not `except Exception`
2. **Include Context**: Always provide debugging information
3. **Log Before Raising**: Use logger.debug() for diagnostics
4. **Fail Gracefully in Batch**: One corrupt file shouldn't stop the entire batch
5. **Fail Fast in CI**: Exit immediately on critical errors

---

## See Also

- `musiclib/exceptions.py` - Exception definitions
- `musiclib/logger.py` - Logging integration
- `docs/LOGGING.md` - Logging guide
- `tests/test_robustness.py` - Edge case handling examples
