# Batch Audio Archaeology Workflow

A concise, current workflow for running batch mining, curation, and formatting with the scripts that ship in this repo—our quiet machine for excavating surfaces, atmosphere, and dust.

## Quick Start

```bash
# 1) Batch mine pads/drones/drums/silences into a dedicated export folder
python process_batch.py --input_dir /path/to/source_audio --project_name MY_BATCH --config config.yaml

# 2) Curate a best-of set (optional)
python curate_best.py --input_root export/MY_BATCH --output_root export/MY_BATCH/best_of --force

# 3) Format for TR-8S (optional)
python format_for_tr8s.py --input_dir export/MY_BATCH --output_dir export/MY_BATCH --kit_name MY_KIT
```

Outputs live under `export/<project_name>/...` with per-source subfolders for pads, swells, clouds, hiss, drums, and silences.

If you need deterministic A/B runs while tuning, set `reproducibility.random_seed` in your config; grain placement and pitch draws will repeat, letting you hear the effect of a single change.

## Step-by-Step

### 1) Batch processing
- Use `process_batch.py` to drive mining. It rewrites a temporary config pointing `paths.source_audio_dir` to `--input_dir` and `paths.export_dir` to `export/<project_name>`.
- On failure, it exits non-zero so CI/automation can detect errors.

Tips:
- **Nested Folders**: `process_batch.py` only processes files in the top-level `--input_dir`. If you have nested subdirectories, either flatten them first or manually invoke the mining scripts on each subdirectory.
- **Selective Reprocessing**: If you want to rerun only certain stages, invoke the underlying scripts directly (`make_textures.py`, `mine_drums.py`, `mine_silences.py`).
- **Temp Config Cleanup**: The script creates `config_<project_name>.yaml` in the current directory, which is automatically cleaned up on exit. If a run is killed abruptly, you may need to manually delete this file.

### 2) Curation
- Run `curate_best.py` to pick top candidates per category.
- `--force` replaces an existing output folder; omit it to avoid accidental overwrites.
- Use `--fail-on-empty` if you want the process to exit non-zero when no files are curated.

### 3) Formatting (optional)
- `format_for_tr8s.py` prepares a kit folder. Use `--force` to overwrite an existing kit directory.
- Consider keeping a manifest (CSV or notes) mapping short kit names back to original filenames if provenance matters.

### 4) Dusting / Clouds (optional)
- `dust_pads.py` can layer hiss onto pads.
- `make_curated_clouds.py` builds clouds from a chosen folder. Point it at curated pads/silences if desired.

## Safety and Cleanup
- Many scripts have `--force` guards to prevent accidental deletion. Use them intentionally.
- Batch runs write a temporary config (config_<project_name>.yaml). You can delete it after runs if desired.
- Keep work inside `export/` to avoid clobbering other paths.

## Performance Notes
- Large/long files can consume significant RAM when decoded; consider pre-splitting or adding duration filters if processing hour-long recordings.
- For faster curation, use `soundfile` for simple level checks and reserve `librosa` for spectral features.
- Clouds normalize gently to ~-3 dBFS to keep overlapping grains from saturating. If you want hotter clouds, raise `clouds.target_peak_dbfs` in the config—but leave a little headroom for the texture to breathe.
