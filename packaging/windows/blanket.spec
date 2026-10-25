# -*- mode: python -*-
# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

# PyInstaller spec of the Windows bundle, built from an MSYS2 UCRT64 shell
# after tools/build.py, from the repository root:
#
#     pyinstaller --noconfirm --clean packaging/windows/blanket.spec
#
# The result is dist/Blanket/Blanket.exe with everything it needs next to it.

import re
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPECPATH).resolve().parent.parent  # noqa: F821 (set by PyInstaller)
DATA = ROOT / "build" / "data"
ICON = ROOT / "data" / "blanket.ico"

if not (DATA / "blanket.gresource").exists():
    raise SystemExit("build/data is missing, run tools/build.py first")

define = (ROOT / "blanket" / "define.py").read_text(encoding="utf-8")
VERSION = re.search(r'^VERSION = "([^"]+)"', define, re.MULTILINE).group(1)
LANGUAGES = (ROOT / "po" / "LINGUAS").read_text(encoding="utf-8").split()

# GStreamer plugins Blanket uses, the rest of what MSYS2 ships is left out
GSTREAMER_PLUGINS = [
    # Pipeline
    "coreelements",
    "playback",  # uridecodebin
    "typefindfunctions",
    "pbtypes",
    "app",
    "audioconvert",
    "audioresample",
    "audiomixer",
    "volume",
    "audiotestsrc",  # Noises
    "gio",  # resource:// URIs of the bundled sounds
    # Output
    "autodetect",
    "wasapi2",
    "wasapi",
    "directsound",
    # Bundled sounds
    "ogg",
    "vorbis",
    # Custom sounds
    "opus",
    "flac",
    "wavparse",
    "audioparsers",
    "mpg123",
    "id3demux",
    "isomp4",
    "mediafoundation",  # AAC
]

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "windows" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=[(str(DATA), "blanket-data")],
    hiddenimports=[
        # Loaded lazily, at runtime or by GTK
        "blanket.mpris",
        "blanket.smoke",
        # Makes the hook collect the pixbuf loaders, SVG app icon included
        "gi.repository.GdkPixbuf",
    ],
    hooksconfig={
        "gi": {
            "icons": ["Adwaita", "hicolor"],
            "themes": ["Adwaita"],
            "languages": LANGUAGES,
            "module-versions": {
                "Gtk": "4.0",
                "Gdk": "4.0",
            },
        },
        "gstreamer": {
            "include_plugins": GSTREAMER_PLUGINS,
        },
    },
    excludes=["tkinter", "test", "pydoc", "gi.repository.Xdp"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

version_numbers = tuple(int(n) for n in VERSION.split(".")[:4])
version_numbers += (0,) * (4 - len(version_numbers))

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("FileDescription", "Blanket"),
                        StringStruct("FileVersion", VERSION),
                        StringStruct("InternalName", "Blanket"),
                        StringStruct("LegalCopyright", "GPL-3.0-or-later"),
                        StringStruct("OriginalFilename", "Blanket.exe"),
                        StringStruct("ProductName", "Blanket"),
                        StringStruct("ProductVersion", VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Blanket",
    icon=str(ICON),
    version=version_info,
    console=False,
    debug=False,
    strip=False,
    upx=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Blanket",
)
