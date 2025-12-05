# GEMINI.md: Project Overview and Development Guide

This document provides a comprehensive overview of the "Music Texture Tool" project, intended to be used as a quick-start guide and instructional context for development.

## Project Overview

This is a Python-based command-line tool designed for creating a variety of audio textures for music production, with a specific focus on generating samples compatible with the Roland TR-8S drum machine. The tool can analyze existing audio files and generate new, unique sounds such as pads, drones, swells, granular clouds, and hiss textures.

The project is structured as a command-line application that reads from and writes to specific directories. A central `config.yaml` file allows for detailed customization of the sound generation parameters.

## Building and Running

### 1. Setup

The project uses a Python virtual environment to manage dependencies.

```bash
# Create and activate the virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

The tool is configured via a `config.yaml` file. A default configuration is automatically generated on the first run. This file contains all the parameters for the sound generation process, including:

*   Global settings like sample rate and bit depth.
*   Paths for source and export directories.
*   Parameters for each sound generation module (pad miner, drones, clouds, hiss).
*   Settings for pre-analysis and quality filtering.

### 3. Usage

The main entry point is `make_textures.py`. You can run the entire pipeline or individual steps.

```bash
# Generate all types of textures
python make_textures.py --all

# Run a specific step, for example, generate granular clouds
python make_textures.py --make-clouds

# View all available commands
python make_textures.py --help
```

### 4. Testing

A minimal test suite is available to verify the core functionality.

```bash
python archive/scripts/test_review_fixes.py
```

## Project Structure

```
.
├── config.yaml           # Main configuration file
├── requirements.txt      # Python dependencies
├── README.md             # Detailed project documentation
├── make_textures.py      # Main CLI entrypoint
├── musiclib/             # Core Python package
│   ├── audio_analyzer.py # Audio analysis and quality scoring
│   ├── drone_maker.py    # Generates pad loops and swells
│   ├── granular_maker.py # Granular cloud generator
│   ├── hiss_maker.py     # Hiss loops & flicker bursts
│   └── segment_miner.py  # Mines sustained pad segments
├── source_audio/         # Input audio for pad mining
├── pad_sources/          # Input audio for drone and cloud generation
├── drums/                # Percussive material for hiss generation
└── export/tr8s/          # Output directory for generated samples
```

## Development Conventions

*   **Modularity:** The core logic is organized into distinct modules within the `musiclib` package, each responsible for a specific type of sound generation.
*   **Configuration-driven:** All major parameters are exposed in the `config.yaml` file, promoting flexibility and experimentation without code changes.
*   **Clear I/O:** The tool follows a simple pattern of reading from source directories (`source_audio`, `pad_sources`, `drums`) and writing to an export directory (`export/tr8s`).
*   **Command-Line Interface:** The `argparse` module is used to provide a clear and user-friendly CLI.
*   **Dependencies:** All Python dependencies are listed in `requirements.txt`.
*   **Code Style:** The code is well-commented, with clear function and module-level documentation.