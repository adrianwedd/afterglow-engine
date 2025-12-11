# Security Policy

*The machine is patient. The machine is offline. The machine touches only what you give it.*

---

## The Machine's Nature

`afterglow-engine` is an **offline archaeology tool**. It does not:
- Connect to networks
- Process untrusted remote data
- Expose services or APIs
- Store credentials or personal information

It operates entirely within your local filesystem, reading audio files you explicitly provide and writing textures to directories you specify.

The machine is as safe as the archive you feed it.

---

## Supported Versions

**Current**: The `main` branch is the only supported version. Use the latest release tag (e.g., `v0.8.1`) for stability.

**Legacy**: Older versions receive no security updates. The machine evolves forward.

---

## Reporting a Vulnerability

If you discover a security issue—path traversal, unsafe file handling, arbitrary code execution via malformed audio—please report it responsibly.

### How to Report

**Public Issues** (for non-critical bugs):
- Open an issue at: https://github.com/adrianwedd/afterglow-engine/issues
- Tag it with `security` label

**Private Disclosure** (for critical vulnerabilities):
- Email: **adrian@adrianwedd.com**
- Subject: `[afterglow-engine] Security: <brief description>`
- Do not disclose publicly until a fix is released

### What to Include

1. **Environment**:
   - Operating system (macOS version, Linux distro)
   - Python version (`python --version`)
   - Installation method (pip, git clone)

2. **Reproduction**:
   - Exact command or config used
   - File characteristics that trigger the issue (e.g., "44.1kHz WAV with negative duration metadata")
   - Expected vs actual behavior

3. **Impact**:
   - What files/directories are affected?
   - Can it escape the export directory?
   - Is arbitrary code execution possible?

**Important**: Do not include sensitive or copyrighted audio files in reports. Describe the file structure instead (sample rate, bit depth, metadata anomalies).

---

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Development**: Depends on severity (critical issues prioritized)
- **Public Disclosure**: After fix is merged and released

Critical vulnerabilities will receive expedited fixes and an immediate patch release.

---

## Philosophy on Safety

The machine processes files you control, in directories you specify, on a system you administer. It does not reach beyond its boundaries.

If a vulnerability allows the machine to escape those boundaries—to write outside export paths, to execute commands, to leak information—that is a betrayal of trust. Report it, and it will be corrected.

The archaeology must remain safe.

---

**Maintainer**: Adrian Wedd ([@adrianwedd](https://github.com/adrianwedd))
**Contact**: adrian@adrianwedd.com
