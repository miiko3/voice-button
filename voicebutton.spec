# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('models', 'models')]
binaries = []
hiddenimports = []

d, b, h = collect_all('vosk')
datas += d
binaries += b
hiddenimports += h

excludes = [
    'numpy',
    'scipy',
    'pandas',
    'matplotlib',
    'PIL',
    'tkinter.test',
    'test',
    'unittest',
    'pydoc_data',
    'requests',
    'urllib3',
    'certifi',
    'srt',
    'tqdm',
    'setuptools',
    'pip',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['tkinter', 'sounddevice'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VoiceButton',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/logo.ico',
)
