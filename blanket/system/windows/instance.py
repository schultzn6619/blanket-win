# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Single instance handling

On Linux GApplication makes sure only one Blanket runs, through D-Bus. There
is no session bus on Windows, so a named mutex tells whether Blanket already
runs, and its tray window is asked to show the app instead.
"""

import ctypes
import time
from ctypes import wintypes

from blanket.define import APP_ID
from blanket.system.windows import win32
from blanket.system.windows.tray import WINDOW_CLASS, WM_ACTIVATE_INSTANCE

# Held for the whole life of the process, Windows releases it on exit
_mutex = None


def acquire() -> bool:
    """Claim the instance, False if another Blanket already holds it"""
    global _mutex

    # Only an existing mutex sets the error, make sure no stale one remains
    ctypes.set_last_error(0)
    _mutex = win32.CreateMutexW(None, False, f"Local\\{APP_ID}")
    already_running = ctypes.get_last_error() == win32.ERROR_ALREADY_EXISTS

    if not _mutex:
        return True  # Could not tell, better run twice than not at all

    return not already_running


def activate_running_instance(timeout: float = 5.0) -> bool:
    """
    Ask the running instance to show its window

    It may still be starting up and not have its tray window yet, so this
    keeps looking for a little while.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = win32.FindWindowW(WINDOW_CLASS, None)
        if hwnd:
            # We were launched by the user, so we may hand them the focus
            pid = wintypes.DWORD()
            win32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            win32.AllowSetForegroundWindow(pid.value or win32.ASFW_ANY)

            return bool(win32.PostMessageW(hwnd, WM_ACTIVATE_INSTANCE, 0, 0))
        time.sleep(0.1)

    return False
