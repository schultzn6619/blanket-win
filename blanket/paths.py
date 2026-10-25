# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Where Blanket finds the files it needs at runtime

They are produced by tools/build.py and live in a single data directory:

    blanket.gresource   UI, icons and bundled sounds
    schemas/            compiled GSettings schema
    locale/             compiled translations

Running from a checkout it is build/data, in the Windows bundle it sits next
to the bundled interpreter, and BLANKET_DATA_DIR overrides both.
"""

import os
import sys
from pathlib import Path

# Name of the gettext translation domain
GETTEXT_PACKAGE = "blanket"


def is_frozen() -> bool:
    """Whether Blanket runs from the bundled Windows executable"""
    return bool(getattr(sys, "frozen", False))


def data_dir() -> Path:
    if override := os.environ.get("BLANKET_DATA_DIR"):
        return Path(override)

    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")) / "blanket-data"

    return Path(__file__).resolve().parent.parent / "build" / "data"


def resource_file() -> Path:
    return data_dir() / "blanket.gresource"


def schemas_dir() -> Path:
    return data_dir() / "schemas"


def locale_dir() -> Path:
    return data_dir() / "locale"
