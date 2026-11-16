# -*- mode: python ; coding: utf-8 -*-
"""Windows one-directory bundle, adapted from upstream movieprint_gui.spec.

Upstream: eldorado230/PyMoviePrint@a5ef5f1abd6fedd68eb7263e46b8ae56b9bda0a7
PyInstaller: https://pyinstaller.org/en/stable/spec-files.html
"""
import os
from PyInstaller.utils.hooks import collect_all


root = os.path.abspath(os.path.join(SPECPATH, '..'))
datas, binaries, hiddenimports = collect_all('tkinterdnd2')
ctk_datas, ctk_binaries, ctk_imports = collect_all('customtkinter')
datas += ctk_datas
datas += [(os.path.join(root, 'assets', 'movieprint-studio-v1.png'), 'assets')]
binaries += ctk_binaries
hiddenimports += ctk_imports
hiddenimports += [
    'scenedetect', 'cv2', 'PIL', 'tkinter', 'tkinter.filedialog',
    'tkinter.messagebox', 'tkinter.colorchooser', 'tkinter.scrolledtext',
    'tkinter.ttk', 'video_processing', 'image_grid', 'state_manager',
    'project_io', 'movieprint_maker', 'workspace_tools', 'face_analysis',
    'version', 'source_paths',
]

a = Analysis(
    [os.path.join(root, 'shell_entry.py')],
    pathex=[root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='PyMoviePrint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(root, 'windows', 'PyMoviePrint.ico'),
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name='PyMoviePrint',
)
