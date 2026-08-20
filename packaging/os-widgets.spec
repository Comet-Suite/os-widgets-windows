# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

qta_datas, qta_binaries, qta_hidden = collect_all('qtawesome')
tz_datas = collect_data_files('tzdata')

a = Analysis(
    ['os_widgets.py'],
    pathex=[],
    binaries=qta_binaries,
    datas=qta_datas + tz_datas,
    hiddenimports=qta_hidden + ['PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', 'IPython'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OS-Widgets',
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
    icon='assets/os-widgets.ico',
    version='packaging/version_info.txt',
)
