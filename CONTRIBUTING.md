# Contributing

Thanks for your interest in improving this audio texture tool. Contributions are welcome for fixes, docs, and small enhancements that keep the current design coherent.

## Environment
- Use Python 3.11 (repo ships `venv311` locally; you can create your own):  
  ```bash
  python3.11 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- Optional: set `reproducibility.random_seed` in your `config.yaml` for deterministic runs. Enable verbose logs with `dsp_utils.set_verbose(True)` if you need pre-analysis traces.

## Tests
- Run the minimal regression suite:  
  ```bash
  python test_review_fixes.py
  ```
- Smoke test the pipeline on a tiny source (place a short WAV/FLAC in `pad_sources/` or `source_audio/`):  
  ```bash
  python make_textures.py --make-clouds
  ```

## Style & Scope
- Keep changes incremental; avoid architectural rewrites.
- Preserve backward compatibility for config fields (fall back gracefully).
- Include doc updates when adding flags/config options.

## Filing Issues
- Include Python version, platform, and the command you ran.
- If possible, share a minimal audio snippet (or describe characteristics) that reproduces the issue.
