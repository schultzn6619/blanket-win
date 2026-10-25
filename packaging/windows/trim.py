# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Leave out of the bundle what Blanket never uses

PyInstaller's GTK hooks collect every gdk-pixbuf loader and GIO module
MSYS2 has, along with everything those link to: the HEIF loader alone
drags in ~50 MB of video encoders. Given a few modules to drop, the DLLs
only they import are dropped too, by walking the import tables.

Anything loaded at runtime by name (GI typelibs, GStreamer plugins, Python
extensions) is never imported by a dropped module alone, so it stays.
verify() then checks every DLL left can resolve its imports.
"""

import os
from pathlib import Path

import pefile


def _name(entry) -> str:
    return Path(entry[0]).name.lower()


def _imports(path: str) -> set[str]:
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    )
    names = {
        entry.dll.decode("ascii", "replace").lower()
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])
    }
    pe.close()
    return names


def drop_binaries(binaries, unused: set[str]):
    """Binaries without the unused ones and what only they need"""
    imports = {
        _name(entry): _imports(entry[1])
        for entry in binaries
        if entry[1].lower().endswith((".dll", ".pyd", ".exe"))
    }
    importers: dict[str, set[str]] = {}
    for importer, deps in imports.items():
        for dep in deps:
            importers.setdefault(dep, set()).add(importer)

    removed = {name.lower() for name in unused}
    changed = True
    while changed:
        changed = False
        for name in imports:
            if name in removed:
                continue
            users = importers.get(name, set())
            # Only ever imported by dropped modules, nothing else needs it
            if users and users <= removed:
                removed.add(name)
                changed = True

    kept = [entry for entry in binaries if _name(entry) not in removed]
    return kept, sorted(removed & set(imports))


def drop_datas(datas, directories: list[str]):
    """Data files without those under the given bundle directories"""
    prefixes = [Path(d).parts for d in directories]
    return [
        entry
        for entry in datas
        if not any(Path(entry[0]).parts[: len(p)] == p for p in prefixes)
    ]


def verify(binaries):
    """Fail the build if a bundled DLL imports one that is nowhere to be found"""
    system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    bundled = {_name(entry) for entry in binaries}
    missing = {}

    for entry in binaries:
        if not entry[1].lower().endswith((".dll", ".pyd")):
            continue
        for dep in _imports(entry[1]):
            if dep in bundled or dep.startswith(("api-ms-win-", "ext-ms-")):
                continue
            if (system / dep).exists():
                continue
            missing.setdefault(_name(entry), []).append(dep)

    if missing:
        details = "\n".join(f"  {k}: {', '.join(v)}" for k, v in missing.items())
        raise SystemExit(f"Bundled binaries have unresolved imports:\n{details}")
