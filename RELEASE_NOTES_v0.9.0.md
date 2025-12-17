# Release Notes: v0.9.0 "The Sentinel"

**Production Hardening Release**

Transform afterglow-engine from prototype to battle-tested production system with comprehensive observability, automated quality gates, and hardened robustness.

---

## 🎯 What's New

### Observability & Error Handling
- **Structured logging** with module-level tagging (`musiclib.logger`)
- **Custom exception hierarchy** with rich debugging context (SilentArtifact, ClippedArtifact, FilesystemError)
- **Graceful degradation** in batch processing - failures don't stop the entire job
- **Visual CLI style preserved** - familiar `[*]`, `[!]`, `[✓]` prefixes maintained

### CI/CD & Automation
- **GitHub Actions workflows** - Automated testing across Python 3.9, 3.10, 3.11
- **Performance regression detection** - Builds fail if >20% slower than baseline
- **Code quality checks** - Flake8, Black, MyPy integration
- **Automated releases** - Triggered on version tags

### Robustness & Security
- **26 new edge case tests** - Corrupt audio, extreme configs, filesystem issues
- **Input validation** - NaN/Inf detection across all DSP functions
- **Path traversal protection** - Writes outside export root are blocked
- **Test suite doubled** - 159 tests passing (up from 73 in v0.8)

### Performance
- **STFT caching verified** - >100,000× speedup on subsequent calls
- **Single-pass optimization** - 66% reduction in STFT overhead
- **Performance baseline established** - Automated regression detection

### Documentation
- [**LOGGING.md**](docs/LOGGING.md) - Structured logging guide
- [**ERROR_HANDLING.md**](docs/ERROR_HANDLING.md) - Exception hierarchy and patterns
- [**CI_CD.md**](docs/CI_CD.md) - GitHub Actions workflow documentation
- [**MIGRATION_V0.9.md**](docs/MIGRATION_V0.9.md) - Upgrade guide from v0.8

---

## ⚠️ Breaking Changes (Minimal)

### 1. `load_audio()` return behavior
**v0.8**: Raised exceptions on errors
```python
# v0.8
try:
    audio, sr = io_utils.load_audio("file.wav")
except Exception as e:
    print(f"Error: {e}")
```

**v0.9**: Returns `(None, None)` for graceful degradation
```python
# v0.9
audio, sr = io_utils.load_audio("file.wav")
if audio is None:
    logger.warning("Failed to load file")
    continue  # Continue batch processing
```

### 2. Exception types changed
**v0.8**: Generic `ValueError`, `Exception`

**v0.9**: Specific custom exceptions
```python
from musiclib.exceptions import SilentArtifact, FilesystemError

try:
    normalized = dsp_utils.normalize_audio(audio, -1.0)
except SilentArtifact as e:
    logger.warning(f"Cannot normalize: {e}")
    logger.debug(f"Context: {e.context}")  # Rich debugging info
```

### 3. Logging migration
**v0.8**: Direct `print()` statements

**v0.9**: Structured logging
```python
from musiclib.logger import get_logger, log_success

logger = get_logger(__name__)
logger.info("Processing audio...")
log_success(logger, "Saved 10 files")
```

---

## 🚀 Upgrade Instructions

### Quick Start
```bash
# Pull latest code
git pull origin main
git checkout v0.9.0

# No dependency changes - existing environment works
pytest tests/  # Verify: 159 passed, 4 skipped
```

### Configuration (Optional)
```bash
# Control log verbosity
export AFTERGLOW_LOG_LEVEL=DEBUG

# Set export directory
export AFTERGLOW_EXPORT_ROOT=/path/to/export

# New CLI flags
python make_textures.py --verbose --all  # Debug logging
python make_textures.py --strict --all   # Fail-fast mode (CI/CD)
```

### Migration Guide
Most v0.8 code works unchanged. For detailed migration instructions, see [docs/MIGRATION_V0.9.md](docs/MIGRATION_V0.9.md).

---

## 📊 Stats

- **Lines changed**: 2,709 insertions, 244 deletions (29 files)
- **New tests**: 86 tests added (159 total, up from 73)
- **Test coverage**: DSP validation, spectral analysis, robustness, security, error handling
- **Documentation**: 1,253 lines of new documentation
- **Python support**: 3.9, 3.10, 3.11 (CI-validated)

---

## 📚 Resources

- **Full changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Migration guide**: [docs/MIGRATION_V0.9.md](docs/MIGRATION_V0.9.md)
- **Logging guide**: [docs/LOGGING.md](docs/LOGGING.md)
- **Error handling**: [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md)
- **CI/CD docs**: [docs/CI_CD.md](docs/CI_CD.md)

---

## 🙏 Acknowledgments

This release represents a comprehensive transformation from prototype to production-grade system. The "sonic archaeology" philosophy remains unchanged - the machine still quietly excavates textures from your archive - but now with the safeguards, observability, and reliability required for serious work.

---

**Install**: `git clone https://github.com/adrianwedd/afterglow-engine.git && cd afterglow-engine && git checkout v0.9.0`

**Upgrade**: `git pull origin main && git checkout v0.9.0`

**Report issues**: https://github.com/adrianwedd/afterglow-engine/issues
