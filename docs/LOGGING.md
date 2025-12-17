# Logging System

*Structured logging for sonic archaeology.*

---

## Overview

Afterglow-engine uses Python's standard `logging` module with custom formatters that preserve the CLI's visual style while providing structured output for debugging.

**Key Features**:
- Preserves visual prefixes: `[*]`, `[!]`, `[✓]`, `[✗]`
- Module-level tagging for debugging
- Environment variable configuration
- Compatible with log aggregation tools

---

## Quick Start

### Using the Logger in Your Code

```python
from musiclib.logger import get_logger, log_success

logger = get_logger(__name__)

# Info messages (default level)
logger.info("Processing audio file...")  # [*] Processing audio file...

# Warnings
logger.warning("Audio contains DC offset")  # [!] Audio contains DC offset

# Success messages
log_success(logger, "Saved 10 textures")  # [✓] Saved 10 textures

# Errors
logger.error("Failed to load file")  # [✗] Failed to load file

# Debug (only shown when DEBUG level enabled)
logger.debug(f"STFT shape: {stft.shape}")
```

---

## Log Levels

Afterglow uses standard Python log levels with custom formatting:

| Level | Prefix | Usage | Example |
|-------|--------|-------|---------|
| **DEBUG** | `[DEBUG]` | Detailed diagnostic info | STFT cache hit, array shapes |
| **INFO** | `[*]` | General progress updates | Processing files, analysis steps |
| **WARNING** | `[!]` | Recoverable issues | Clipped audio, missing metadata |
| **SUCCESS** | `[✓]` | Successful operations | Files saved, processing complete |
| **ERROR** | `[✗]` | Errors that prevent operation | File not found, invalid config |
| **CRITICAL** | `[!!!]` | System-level failures | Out of disk space, corrupted state |

---

## Configuration

### Environment Variable

Set log level via `AFTERGLOW_LOG_LEVEL`:

```bash
# Show only warnings and errors
export AFTERGLOW_LOG_LEVEL=WARNING

# Show all info messages (default)
export AFTERGLOW_LOG_LEVEL=INFO

# Show detailed debug output
export AFTERGLOW_LOG_LEVEL=DEBUG

# Run with debug logging
AFTERGLOW_LOG_LEVEL=DEBUG python make_textures.py --mine-pads
```

### Valid Values

- `DEBUG` - Most verbose, includes internal details
- `INFO` - Default, shows progress and key events
- `WARNING` - Only warnings and errors
- `ERROR` - Only errors and critical failures
- `CRITICAL` - Only critical system failures

### Command-Line Flag

For scripts that support it (like `make_textures.py`):

```bash
# Enable debug logging for single run
python make_textures.py --verbose --mine-pads
```

---

## Module-Level Tagging

The logger automatically tags messages with the originating module:

```
[*] musiclib.segment_miner: Analyzing 30s audio for stable regions
[!] musiclib.granular_maker: Low grain yield (12 grains), consider relaxing quality filters
[✓] musiclib.io_utils: Saved pad_001.wav (2.1s, -12.0 dBFS)
```

This helps track execution flow across modules during debugging.

---

## Migration from print()

### Before (v0.8)
```python
print("[*] Processing audio...")
print(f"[!] Warning: {issue}")
if success:
    print(f"[✓] Saved {count} files")
```

### After (v0.9)
```python
from musiclib.logger import get_logger, log_success

logger = get_logger(__name__)

logger.info("Processing audio...")
logger.warning(f"Warning: {issue}")
if success:
    log_success(logger, f"Saved {count} files")
```

### Benefits
- Configurable log levels
- Module tagging
- Can redirect to file/syslog
- Better for CI/CD logging

---

## Advanced Usage

### Conditional Debug Logging

```python
if logger.isEnabledFor(logging.DEBUG):
    # Expensive computation only if DEBUG enabled
    logger.debug(f"Detailed analysis: {compute_expensive_stats()}")
```

### Logging Exceptions

```python
try:
    result = process_audio(audio)
except Exception as e:
    logger.error(f"Processing failed: {e}")
    logger.debug("Full traceback:", exc_info=True)  # Include traceback in DEBUG
    raise
```

### Context-Rich Messages

```python
from musiclib.exceptions import SilentArtifact

try:
    normalized = dsp_utils.normalize_audio(audio, -1.0)
except SilentArtifact as e:
    logger.warning(f"Cannot normalize: {e}")
    logger.debug(f"Context: {e.context}")  # Shows peak, RMS, etc.
```

---

## Logging in Tests

Tests should use minimal logging to avoid cluttering output:

```python
import logging
from musiclib.logger import get_logger

# In test setup
logging.getLogger('musiclib').setLevel(logging.WARNING)

# Or for debugging a specific test
logger = get_logger('musiclib.granular_maker')
logger.setLevel(logging.DEBUG)
```

---

## Output Redirection

### Log to File

```python
import logging
from musiclib.logger import get_logger

logger = get_logger(__name__)

# Add file handler
handler = logging.FileHandler('afterglow.log')
handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
logger.addHandler(handler)
```

### Log to JSON (for parsing)

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': record.created,
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
        })

handler = logging.FileHandler('afterglow.json')
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

---

## Philosophy

The logging system preserves afterglow-engine's "sonic archaeology" metaphor:

- **Visual style maintained**: `[*]`, `[!]`, `[✓]` prefixes keep CLI feel
- **Poetic yet precise**: Messages reference "textures", "grains", "surfaces"
- **Quiet by default**: INFO level shows progress without overwhelming
- **Debug reveals process**: DEBUG level exposes the archaeology at work

Example progression:
```
INFO:  [*] Excavating stable regions from 5 source files...
INFO:  [*] Analyzing file_01.flac (3m 42s)...
DEBUG: [*] Computed STFT (2049x172 bins)
DEBUG: [*] Onset density: 2.3 onsets/sec (target: <3.0)
INFO:  [✓] Extracted 3 candidate pads
```

---

## See Also

- `musiclib/logger.py` - Logger implementation
- `musiclib/exceptions.py` - Custom exceptions with context
- `docs/ERROR_HANDLING.md` - Error handling patterns
