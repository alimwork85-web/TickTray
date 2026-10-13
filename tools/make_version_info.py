"""Generates version_info.txt (Windows file-properties version resource) from version.py.

Usage:  venv/Scripts/python tools/make_version_info.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from version import __version__  # noqa: E402

parts = [int(x) for x in __version__.split(".")] + [0] * 4
major, minor, patch, build = parts[:4]
tup = f"({major}, {minor}, {patch}, {build})"
dotted = f"{major}.{minor}.{patch}.{build}"

text = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tup},
    prodvers={tup},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'alimwork85-web'),
         StringStruct('FileDescription', 'TickTray - system tray countdown timer'),
         StringStruct('FileVersion', '{dotted}'),
         StringStruct('InternalName', 'TickTray'),
         StringStruct('LegalCopyright', 'MIT License'),
         StringStruct('OriginalFilename', 'TickTray.exe'),
         StringStruct('ProductName', 'TickTray'),
         StringStruct('ProductVersion', '{dotted}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
with open(os.path.join(ROOT, "version_info.txt"), "w", encoding="utf-8") as f:
    f.write(text)
print("version_info.txt written for", dotted)
