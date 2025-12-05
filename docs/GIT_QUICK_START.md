# Git Quick Start Guide

## After You Make Changes

### 1. Check What Changed
```bash
git status                 # Overview of changes
git diff                   # Detailed changes (not staged yet)
```

### 2. Stage Your Changes
```bash
git add <filename>         # Stage specific file
git add musiclib/          # Stage entire directory
git add .                  # Stage everything
```

### 3. Commit Your Changes
```bash
# Short message
git commit -m "config: Adjust swell duration"

# Longer message with details
git commit -m "config: Enhanced Solanus texture parameters

- Increased swell duration to 10s
- Added 4 pad durations for variation
- Improved cloud parameters

Result: 60+ textures (was 36)"
```

### 4. View Your Work
```bash
git log --oneline -5       # Last 5 commits
git show HEAD              # Latest commit details
```

---

## Common Scenarios

### After applying config_enhanced.yaml
```bash
cp config_enhanced.yaml config.yaml
python make_textures.py --all
# Listen to results...

git add config.yaml
git commit -m "config: Apply enhanced parameters for better textures"
git log --oneline -3
```

### After installing improved granular synthesis
```bash
cp granular_maker_improved.py musiclib/granular_maker.py
python make_textures.py --make-clouds
# Listen to clouds...

git add musiclib/granular_maker.py
git commit -m "feat: Add smart grain quality filtering for clouds"
git log --oneline -3
```

### After bug fix or refactoring
```bash
git status                  # See what's changed
git diff musiclib/          # See specific changes
git add musiclib/
git commit -m "fix: Improve grain extraction robustness"
```

### If you made a mistake and want to undo
```bash
git restore <file>         # Discard changes in that file
git restore --staged <file> # Unstage a file
git reset HEAD~1           # Undo last commit (keep changes)
```

---

## Helpful Commands

```bash
# View history
git log --oneline -10                    # Last 10 commits
git log --oneline --graph --all          # Visual tree
git log -- <file>                        # History of one file
git show <commit-hash>                   # Details of specific commit

# See what changed between commits
git diff HEAD~1 HEAD                     # Changes in last commit
git diff <commit1> <commit2>             # Between any two commits

# Search commit history
git log --grep="cloud"                   # Find commits mentioning "cloud"
git log -S "grain_quality"               # Find commits that added/removed this text
```

---

## Commit Message Tips

Good patterns:
```
config: Brief description of what config changed
feat: New feature added
fix: Bug fix
docs: Documentation updated
refactor: Code reorganized/cleaned up
test: Test cases added
```

Good examples:
```
config: Increase cloud grains from 200 to 300
feat: Add grain quality filtering to cloud synthesis
fix: Prevent phase discontinuity in swell loops
docs: Update configuration guide with examples
```

---

## Repository Layout

```
/Users/adrian/repos/music/
├── .git/                    # Git repository (hidden)
├── .gitignore              # Exclusion rules
├── config.yaml             # Active configuration
├── config_enhanced.yaml    # Enhanced parameters
├── make_textures.py        # Main CLI
├── musiclib/               # Core modules
├── discover_audio.py       # Phase 1: Discovery
├── select_sources.py       # Phase 2: Selection
├── batch_generate_textures.py  # Phase 3: Batch
├── granular_maker_improved.py  # Enhanced synthesis
├── *.md                    # Documentation files
└── export/                 # Generated textures (NOT tracked)
```

---

## What's Tracked vs Not

**TRACKED** (in git):
- Code (.py files)
- Config files (config.yaml)
- Documentation (.md files)

**NOT TRACKED** (excluded by .gitignore):
- Audio files (*.flac, *.wav, *.mp3) - too large
- Generated outputs (export/)
- Batch artifacts (audio_catalog.csv, etc.)
- Music collections (Elevations/, Mr. Cloudy/, etc.)
- IDE files (.vscode/, __pycache__)
- OS files (.DS_Store, Thumbs.db)

---

## Setting Up Aliases (Optional)

Add to `~/.gitconfig`:
```ini
[alias]
    st = status
    diff = diff --color-words
    co = checkout
    br = branch
    ci = commit
    unstage = restore --staged
    recent = log --oneline -10
    viz = log --oneline --graph --all
    last = show HEAD
```

Then you can use:
```bash
git st              # instead of git status
git recent          # instead of git log --oneline -10
git viz             # instead of git log --oneline --graph --all
```

---

## Pushing to Remote (Future)

When/if you want to add a remote later:
```bash
git remote add origin https://github.com/yourusername/music.git
git branch -M main
git push -u origin main
```

For now, you're purely local. ✓

---

## Questions?

- `git --help` – Git documentation
- `git <command> --help` – Help for specific command
- `.git-help` file in repo – Detailed cheat sheet

Good luck! 🎵
