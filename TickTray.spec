# -*- mode: python ; coding: utf-8 -*-
import os

# Qt modules the app never imports (only QtCore/QtGui/QtWidgets are used).
QT_EXCLUDES = [
    'PyQt6.QtNetwork', 'PyQt6.QtSvg', 'PyQt6.QtPdf', 'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtMultimedia', 'PyQt6.QtPrintSupport', 'PyQt6.QtDBus',
]
# DLLs the PyQt6 hook bundles anyway. Only the .ico image plugin is needed (to load TickTray.ico).
DROP_BINARIES = {
    'opengl32sw.dll', 'qt6pdf.dll', 'qt6svg.dll', 'qt6network.dll',
    'qtuiotouchplugin.dll', 'qsvgicon.dll', 'qminimal.dll', 'qoffscreen.dll',
    'qgif.dll', 'qicns.dll', 'qjpeg.dll', 'qpdf.dll', 'qsvg.dll', 'qtga.dll', 'qtiff.dll', 'qwbmp.dll', 'qwebp.dll',
}


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('TickTray.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'] + QT_EXCLUDES,
    noarchive=False,
    optimize=0,
)
a.binaries = [b for b in a.binaries if os.path.basename(b[0]).lower() not in DROP_BINARIES]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TickTray',
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
    icon=['TickTray.ico'],
    version='version_info.txt',
)
