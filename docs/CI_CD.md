# CI/CD Pipeline

*Automated quality gates for sonic archaeology.*

---

## Overview

Afterglow-engine uses GitHub Actions for continuous integration, automated testing, and performance regression detection.

**Workflows**:
- **CI** - Run tests across Python versions, check code quality
- **Performance** - Detect performance regressions
- **Release** - Automated releases on version tags

---

## Workflows

### CI Workflow (`.github/workflows/ci.yml`)

Runs on every push to `main` and all pull requests.

**Jobs**:

1. **Test Matrix** (Python 3.9, 3.10, 3.11)
   - Install system dependencies (libsndfile1, ffmpeg)
   - Install Python dependencies
   - Run full test suite with coverage
   - Upload coverage to Codecov (Python 3.11 only)

2. **Code Quality**
   - Lint with flake8 (syntax errors are fatal)
   - Check formatting with black
   - Type check with mypy
   - All quality checks use `continue-on-error: true` for gradual adoption

**Trigger**:
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

**Example run**:
```
✓ Test Python 3.9 - 123 passed, 4 skipped
✓ Test Python 3.10 - 123 passed, 4 skipped
✓ Test Python 3.11 - 123 passed, 4 skipped
✓ Code Quality Checks - 3 warnings (non-blocking)
```

---

### Performance Workflow (`.github/workflows/performance.yml`)

Runs on pull requests and pushes to `main` to detect performance regressions.

**Steps**:

1. **Run Benchmarks**
   - Execute `tests/run_benchmarks.py`
   - Generate `current_benchmarks.json`

2. **Compare Against Baseline**
   - Compare vs `.github/baselines/performance_baseline.json`
   - Fail if >20% slower on any benchmark
   - Upload results as artifacts

3. **Comment on PR** (if applicable)
   - Post benchmark results summary

**Baseline Benchmarks**:

| Benchmark | Baseline | Threshold |
|-----------|----------|-----------|
| stft_analysis | 3.69s | <4.43s (20% slower) |
| crossfade_loop | 0.0035s | <0.0042s |
| audio_normalization | 0.0023s | <0.0028s |
| filter_design | 0.0056s | <0.0067s |

**Updating Baseline**:

```bash
# Run benchmarks locally
python tests/run_benchmarks.py --output .github/baselines/performance_baseline.json

# Commit new baseline
git add .github/baselines/performance_baseline.json
git commit -m "Update performance baseline"
```

---

### Release Workflow (`.github/workflows/release.yml`)

Automatically creates GitHub releases when version tags are pushed.

**Trigger**:
```bash
# Tag a release (use semantic versioning)
git tag v0.9.0
git push origin v0.9.0
```

**Steps**:

1. **Run Full Test Suite**
   - All tests must pass before release

2. **Create Release Archive**
   - Package entire project (excluding .git, venv, etc.)
   - Create `afterglow-engine-v0.9.0.tar.gz`

3. **Create GitHub Release**
   - Auto-generate release notes
   - Attach release archive
   - Mark as latest release

**Release Artifact Contents**:
```
afterglow-engine-v0.9.0/
├── musiclib/
├── tests/
├── docs/
├── make_textures.py
├── requirements.txt
├── README.md
└── ... (all source files)
```

---

## Local Testing

### Test with act (GitHub Actions locally)

Install `act`:
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

Run workflows locally:
```bash
# Run CI workflow
act pull_request

# Run specific job
act -j test

# Run with specific Python version
act -j test --matrix python-version:3.11
```

---

## Badge Setup

Add status badges to README.md:

```markdown
![CI](https://github.com/YOUR_USERNAME/afterglow-engine/workflows/CI/badge.svg)
![Performance](https://github.com/YOUR_USERNAME/afterglow-engine/workflows/Performance%20Regression%20Detection/badge.svg)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/afterglow-engine/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/afterglow-engine)
```

---

## Troubleshooting

### Tests Fail on CI But Pass Locally

**Cause**: Environment differences (missing system dependencies, Python version)

**Solution**:
```bash
# Check which Python version failed
# Reproduce locally with exact version
pyenv install 3.9.18
pyenv local 3.9.18
pytest tests/
```

### Performance Check Fails

**Cause**: Legitimate regression or noisy baseline

**Solution**:
```bash
# Run benchmarks multiple times to check variability
for i in {1..5}; do
    python tests/run_benchmarks.py --output run_$i.json
done

# Compare variance
python tests/compare_benchmarks.py run_1.json run_2.json
```

If variance >10%, baseline is noisy - consider averaging multiple runs.

### Codecov Upload Fails

**Cause**: Missing `CODECOV_TOKEN` secret

**Solution**:
1. Get token from https://codecov.io/gh/YOUR_USERNAME/afterglow-engine
2. Add to GitHub Secrets: Settings → Secrets → New repository secret
3. Name: `CODECOV_TOKEN`
4. Re-run workflow

---

## Environment Variables

Workflows use these environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `AFTERGLOW_LOG_LEVEL` | Control logging verbosity | `INFO` |
| `AFTERGLOW_EXPORT_ROOT` | Set export directory | `export` |
| `AFTERGLOW_UNSAFE_IO` | Allow writes outside export (testing only) | `0` |

Set in workflow:
```yaml
env:
  AFTERGLOW_LOG_LEVEL: WARNING
  AFTERGLOW_UNSAFE_IO: 1  # For test suite
```

---

## Best Practices

### 1. Keep Tests Fast

- Use small test audio files (<5s)
- Mock expensive operations when possible
- Run full integration tests only in CI

### 2. Update Baseline Thoughtfully

- Only update after verified optimization
- Document reason in commit message
- Check for regressions on other benchmarks

### 3. Use continue-on-error for Non-Critical Checks

```yaml
- name: Check formatting with black
  continue-on-error: true  # Don't block PR on formatting
  run: black --check musiclib
```

### 4. Cache Dependencies

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # Cache pip dependencies
```

---

## Future Enhancements

Potential CI/CD improvements:

1. **Nightly Builds**: Test against latest librosa/numpy
2. **Docker Images**: Pre-built environments for faster CI
3. **Benchmarking Dashboard**: Track performance over time
4. **Auto-format PRs**: Bot to auto-fix black/flake8 issues
5. **Release Notes Automation**: Parse commits for changelog

---

## See Also

- `.github/workflows/ci.yml` - CI workflow definition
- `.github/workflows/performance.yml` - Performance testing
- `.github/workflows/release.yml` - Release automation
- `tests/run_benchmarks.py` - Benchmark runner
- `tests/compare_benchmarks.py` - Regression checker
