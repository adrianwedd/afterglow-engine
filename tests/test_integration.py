import os
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
    pads_export = export_dir / "pads"
    assert pads_export.exists()
    # Should find at least one pad from the 3s sine wave
    assert len(list(pads_export.glob("*.wav"))) > 0

    # 2. Run Drone Maker
    # Drone maker reads from pad_sources_dir
    run_make_drones(config)
    swells_export = export_dir / "swells"
    assert pads_export.exists() # Drones also write to pads dir
    assert swells_export.exists()
    # Should generate loops and swells
    assert len(list(swells_export.glob("*.wav"))) > 0

    # 3. Run Cloud Maker
    # Cloud maker reads from pad_sources_dir
    run_make_clouds(config)
    clouds_export = export_dir / "clouds"
    assert clouds_export.exists()
    assert len(list(clouds_export.glob("*.wav"))) > 0

    # 4. Run Hiss Maker
    # Hiss maker reads from drums_dir and uses synthetic noise
    run_make_hiss(config)
    hiss_export = export_dir / "hiss"
    assert hiss_export.exists()
    assert len(list(hiss_export.glob("*.wav"))) > 0