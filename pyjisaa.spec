# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for pyjisaa — Ji's Shopify App Event Analyzer.

Build command:
    pyinstaller pyjisaa.spec

Or directly:
    pyinstaller --windowed --icon=ass/icon/icon256.png --name pyjisaa main.py
"""

import sys
from pathlib import Path

block_cipher = None

# ── Collect source files ────────────────────────────────────────────
root = Path(SPECPATH)  # SPECPATH is set by PyInstaller to the .spec file's directory

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[
        # Include icon files
        (str(root / 'ass' / 'icon' / 'icon256.png'), 'ass/icon'),
        (str(root / 'ass' / 'icon' / 'icon.ico'), 'ass/icon'),
        (str(root / 'ass' / 'icon' / 'icon.icns'), 'ass/icon'),
        (str(root / 'ass' / 'icon' / 'icon1024mac.png'), 'ass/icon'),
    ],
    hiddenimports=[
        'models',
        'definitions',
        'data_io',
        'analyzer',
        'gui',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pyjisaa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windows GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / 'ass' / 'icon' / 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pyjisaa',
)

app = BUNDLE(
    coll,
    name='pyjisaa.app',
    icon=str(root / 'ass' / 'icon' / 'icon.icns'),
    bundle_identifier='com.jihooyoon.pyjisaa',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'CFBundleDisplayName': 'Jisrot - Shopify Events Anal',
        'CFBundleName': 'pyjisaa',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': 'GPLv2',
    },
)
