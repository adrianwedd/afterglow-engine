import os
from pathlib import Path
import numpy as np
import soundfile as sf
from musiclib import io_utils
import pytest
from make_textures import load_or_create_config, run_mine_pads, run_make_drones, run_make_clouds, run_make_hiss

def create_sine_wave(filepath, duration_sec=1.0, sr=44100, freq=440.0):
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    audio = 0.1 * np.sin(2 * np.pi * freq * t)
    sf.write(filepath, audio, sr)

def test_full_pipeline_integration(tmp_path):
    """
    Integration test that runs the full pipeline on synthetic data.
    """
    # Setup directory structure
    source_dir = tmp_path / "source_audio"
    pad_sources_dir = tmp_path / "pad_sources"
    drums_dir = tmp_path / "drums"
    export_dir = tmp_path / "export"
    
    source_dir.mkdir()
    pad_sources_dir.mkdir()
    drums_dir.mkdir()
    export_dir.mkdir()

    # Create synthetic audio files
    create_sine_wave(source_dir / "test_src.wav", duration_sec=3.0) # Long enough for pad mining
    create_sine_wave(pad_sources_dir / "test_pad.wav", duration_sec=2.0)
    create_sine_wave(drums_dir / "test_drum.wav", duration_sec=1.0)

    # Create a config that points to these directories
    config_path = tmp_path / "config.yaml"
    # We can use the default config but override paths
    config = load_or_create_config(str(config_path))
    
    config['paths']['source_audio_dir'] = str(source_dir)
    config['paths']['pad_sources_dir'] = str(pad_sources_dir)
    config['paths']['drums_dir'] = str(drums_dir)
    config['paths']['export_dir'] = str(export_dir)
    
    # Tweak settings for speed/reliability on synthetic data
    config['pad_miner']['min_rms_db'] = -80.0
    config['pad_miner']['max_rms_db'] = 0.0
    config['pad_miner']['window_hop_sec'] = 0.5
    config['pad_miner']['max_onset_rate_per_second'] = 100.0
    config['pad_miner']['spectral_flatness_threshold'] = 1.0
    config['pre_analysis']['enabled'] = False # Disable pre-analysis to simplify
    config['hiss']['use_synthetic_noise'] = True # Test synthetic path too
    
    # 1. Run Pad Miner
    run_mine_pads(config)
    # Pads land under export/<source>/pads when using custom export_dir
    pads_export = Path(config['paths']['export_dir'])
    pad_files = list(pads_export.glob("**/pads/*.wav"))
    assert pad_files, "No pads were exported"

    # 2. Run Drone Maker
    # Drone maker reads from pad_sources_dir (test_pad.wav)
    run_make_drones(config)
    # Drones/swells are written under export_dir (pads/swells)
    drone_exports = list(Path(config['paths']['export_dir']).glob("**/pads/*.wav"))
    swell_exports = list(Path(config['paths']['export_dir']).glob("**/swells/*.wav"))
    assert drone_exports, "No drone pads exported"
    assert swell_exports, "No swells exported"

    # 3. Run Cloud Maker
    # Cloud maker reads from pad_sources_dir (test_pad.wav)
    run_make_clouds(config)
    cloud_export = list(Path(config['paths']['export_dir']).glob("**/clouds/*.wav"))
    assert cloud_export, "No clouds exported"

    # 4. Run Hiss Maker
    # Hiss maker reads from drums_dir (test_drum.wav) AND synthetic noise
    run_make_hiss(config)

    # Check hiss output (may live under export_dir/hiss or nested)
    hiss_files = list(Path(config['paths']['export_dir']).glob("**/hiss/*.wav"))
    assert hiss_files, "No hiss exports found"
