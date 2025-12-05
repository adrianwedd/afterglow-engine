# Contributing to the Machine

*How to tend the engine.*

---

You are entering the back room of the studio.

We are building a tool for **sonic archaeology**. It is robust, quiet, and precise. If you wish to help us maintain or expand it, please adhere to these principles.

## The Philosophy

1.  **No Synthesis**: We do not generate sound from math alone. We mine existing audio.
2.  **No Composition**: We do not make artistic decisions about arrangement. We only provide the textures.
3.  **Safety First**: The machine must not crash when fed silence, noise, or emptiness. It must simply wait.

## The Standard

*   **Type Hints**: Every function signature must be typed. The machine requires clarity.
*   **Guards**: Always check if an array is empty, if a file is silent, or if a fade is longer than the clip.
*   **Dependencies**: Keep them light. We rely on `numpy`, `scipy`, and `librosa`. We do not add weight without purpose.

## The Process

1.  **Fork the Archive**: Clone the repository.
2.  **Calibrate**: Create your environment and run the validation suite.
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pytest
    ```
3.  **Excavate**: Make your changes. Ensure every new feature has a corresponding test in `tests/`.
4.  **Verify**: Run the full integration test (`tests/test_integration.py`) to ensure the pipeline remains unbroken.

## The Tone

When writing documentation or commit messages, avoid purely mechanical language where possible. Use the language of physical media and memory:

*   Instead of "processing samples," consider **"mining textures."**
*   Instead of "randomizing grains," consider **"scattering dust."**
*   Instead of "stable segments," consider **"surfaces."**

We are building a machine that feels like it has always been there.