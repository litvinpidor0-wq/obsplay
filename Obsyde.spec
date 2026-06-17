# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
datas += collect_data_files('PyQt6')
binaries += collect_dynamic_libs('PyQt6')


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtMultimedia'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuick3D', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.QtCharts', 'PyQt6.QtDataVisualization', 'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets', 'PyQt6.QtTextToSpeech', 'PyQt6.QtBluetooth', 'PyQt6.QtSerialPort', 'PyQt6.QtPositioning', 'PyQt6.QtLocation', 'PyQt6.QtSensors', 'PyQt6.QtNfc', 'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtSpatialAudio', 'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'tkinter', 'unittest', 'pydoc'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Obsyde',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
