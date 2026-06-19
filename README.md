# obsplay

**DISCLAIMER:** This project uses an unofficial SoundCloud API and is for educational purposes only. Not affiliated with SoundCloud. Use at your own risk.

## Requirements

- Python 3.9+
- PyQt6 ≥ 6.6
- PyAudio ≥ 0.2.11 (for software audio playback with real-time EQ)
- numpy ≥ 1.24 (for DSP processing)
- audioread ≥ 3.0 (for audio file decoding)
- requests ≥ 2.31

FFmpeg is required for audio decoding — `imageio-ffmpeg` bundles it automatically on all platforms.

## Installation

```bash
pip install -r requirements.txt
python -m obsyde
```

> **Note:** PyAudio may require additional system libraries:
> - **Windows:** `pip install pyaudio` should work out of the box.
> - **macOS:** `brew install portaudio` then `pip install pyaudio`.
> - **Linux:** `sudo apt install portaudio19-dev python3-pyaudio` then `pip install pyaudio`.

## Build

```bash
pip install pyinstaller
pyinstaller Obsyde.spec
```

The standalone executable will be in `dist/`.

## Features

- SoundCloud streaming (search, playlists, likes)
- 10-band graphic equalizer with real-time DSP
- Custom frameless UI with particle effects (rain, snow, stars, bubbles)
- System tray controls
- Keyboard shortcuts
- Import / export playlists
- Settings persistence (EQ, volume, background effects, window opacity)
