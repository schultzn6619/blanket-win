# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Windows only integration, only import it when running on Windows
"""

import os
import sys
from pathlib import Path


def log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    return Path(base) / "Blanket"


def redirect_output_to_log():
    """
    The bundled executable has no console, so output would be lost

    Keep it in %LOCALAPPDATA%\\Blanket\\blanket.log, overwritten on each run,
    which is what users can attach to bug reports.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return  # Started from a console, keep printing there

    try:
        directory = log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        log = open(directory / "blanket.log", "w", encoding="utf-8", buffering=1)
    except OSError:
        return

    sys.stdout = log
    sys.stderr = log
