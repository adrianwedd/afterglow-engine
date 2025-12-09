#!/usr/bin/env python3
"""
Generate golden audio fixtures for regression testing.

These fixtures are deterministic reference files used to verify that
DSP operations produce consistent results across code changes.
"""

import numpy as np
import soundfile as sf
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import musiclib.dsp_utils as dsp_utils

# Ensure deterministic output
SEED = 42
np.random.seed(SEED)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "golden_audio"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

SR = 44100


def generate_test_sine(freq=440.0, duration=1.0, amplitude=0.5):
    """Generate deterministic sine wave."""
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t) * amplitude


def generate_test_noise(duration=1.0, amplitude=0.3):
    """Generate deterministic white noise."""
    samples = int(SR * duration)
    return np.random.randn(samples) * amplitude


def generate_test_harmonics(fundamental=220.0, duration=1.0):
    """Generate complex tone with harmonics."""
    t = np.linspace(0, duration, int(SR * duration), endpoint=False)
    audio = (np.sin(2 * np.pi * fundamental * t) * 0.4 +
             np.sin(2 * np.pi * fundamental * 2 * t) * 0.2 +
             np.sin(2 * np.pi * fundamental * 3 * t) * 0.15 +
             np.sin(2 * np.pi * fundamental * 5 * t) * 0.1)
    return audio


print("Generating golden audio fixtures...")
print(f"Output directory: {FIXTURES_DIR}")
print(f"Random seed: {SEED}\n")

# Fixture 1: Pure sine wave (440 Hz A4)
print("1. Pure sine wave (440 Hz)...")
sine_440 = generate_test_sine(freq=440.0, duration=1.0, amplitude=0.5)
sf.write(FIXTURES_DIR / "sine_440hz.wav", sine_440, SR, subtype='PCM_24')

# Fixture 2: White noise
print("2. White noise...")
noise = generate_test_noise(duration=1.0, amplitude=0.3)
sf.write(FIXTURES_DIR / "white_noise.wav", noise, SR, subtype='PCM_24')

# Fixture 3: Complex harmonic tone
print("3. Complex harmonic tone...")
harmonics = generate_test_harmonics(fundamental=220.0, duration=1.0)
sf.write(FIXTURES_DIR / "harmonics_220hz.wav", harmonics, SR, subtype='PCM_24')

# Fixture 4: Normalized sine (test normalize_audio)
print("4. Normalized sine to -3 dBFS...")
sine_quiet = generate_test_sine(freq=440.0, duration=0.5, amplitude=0.1)
normalized = dsp_utils.normalize_audio(sine_quiet, target_peak_dbfs=-3.0)
sf.write(FIXTURES_DIR / "normalized_minus3db.wav", normalized, SR, subtype='PCM_24')

# Fixture 5: Equal-power crossfade result
print("5. Equal-power crossfade...")
audio1 = generate_test_sine(freq=440.0, duration=1.0, amplitude=0.5)
audio2 = generate_test_sine(freq=880.0, duration=1.0, amplitude=0.5)
fade_length = int(0.1 * SR)  # 100ms
crossfaded_eq = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=True)
sf.write(FIXTURES_DIR / "crossfade_equal_power.wav", crossfaded_eq, SR, subtype='PCM_24')

# Fixture 6: Linear crossfade result
print("6. Linear crossfade...")
crossfaded_linear = dsp_utils.crossfade(audio1, audio2, fade_length, equal_power=False)
sf.write(FIXTURES_DIR / "crossfade_linear.wav", crossfaded_linear, SR, subtype='PCM_24')

# Fixture 7: Looped audio with equal-power crossfade
print("7. Looped audio (equal-power)...")
loop_source = generate_test_harmonics(fundamental=110.0, duration=2.0)
looped = dsp_utils.time_domain_crossfade_loop(
    loop_source, crossfade_ms=50.0, sr=SR, optimize_loop=False, equal_power=True
)
sf.write(FIXTURES_DIR / "loop_equal_power.wav", looped, SR, subtype='PCM_24')

# Fixture 8: Stereo to mono (average method)
print("8. Stereo to mono (average)...")
left = generate_test_sine(freq=440.0, duration=0.5, amplitude=0.6)
right = generate_test_sine(freq=880.0, duration=0.5, amplitude=0.4)
stereo = np.column_stack([left, right])  # soundfile format (N, 2)
mono_avg = dsp_utils.ensure_mono(stereo, method="average")
sf.write(FIXTURES_DIR / "stereo_to_mono_average.wav", mono_avg, SR, subtype='PCM_24')

# Fixture 9: Stereo to mono (sum method for power preservation)
print("9. Stereo to mono (sum/power-preserving)...")
mono_sum = dsp_utils.ensure_mono(stereo, method="sum")
sf.write(FIXTURES_DIR / "stereo_to_mono_sum.wav", mono_sum, SR, subtype='PCM_24')

print(f"\n✓ Generated 9 golden audio fixtures in {FIXTURES_DIR}")
print("\nFixtures:")
for fixture in sorted(FIXTURES_DIR.glob("*.wav")):
    info = sf.info(fixture)
    print(f"  - {fixture.name:40s} {info.duration:.2f}s  {info.subtype}")

print("\nThese fixtures are used for regression testing to ensure DSP operations")
print("produce consistent results across code changes.")
