# obsplay

**DISCLAIMER:** This project uses an unofficial SoundCloud API and is for educational purposes only. Not affiliated with SoundCloud. Use at your own risk.

## Requirements

- Python 3.9+
- PyQt6 ≥ 6.6 (bundles Qt6 + FFmpeg backend on Windows)
- requests ≥ 2.31

## Installation

```bash
pip install -r requirements.txt
python -m obsyde

## Build Command

```bash
python -m PyInstaller --onefile --windowed --name Obsyde --collect-binaries PyQt6 --collect-data PyQt6 --exclude-module PyQt6.QtWebEngineCore --exclude-module PyQt6.QtWebEngineWidgets --exclude-module PyQt6.QtQml --exclude-module PyQt6.QtQuick --exclude-module PyQt6.QtQuick3D --exclude-module PyQt6.Qt3DCore --exclude-module PyQt6.Qt3DRender --exclude-module PyQt6.QtCharts --exclude-module PyQt6.QtDataVisualization --exclude-module PyQt6.QtPdf --exclude-module PyQt6.QtPdfWidgets --exclude-module PyQt6.QtTextToSpeech --exclude-module PyQt6.QtBluetooth --exclude-module PyQt6.QtSerialPort --exclude-module PyQt6.QtPositioning --exclude-module PyQt6.QtLocation --exclude-module PyQt6.QtSensors --exclude-module PyQt6.QtSql --exclude-module PyQt6.QtTest --exclude-module PyQt6.QtSpatialAudio --exclude-module tkinter --exclude-module unittest run.py