# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('models', 'models')]
binaries = []
hiddenimports = []

for package in ('vosk',):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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