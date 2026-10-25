# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Starting Blanket in the background when the user logs in

Windows: a value in the current user's Run registry key, which is also what
Task Manager's Startup apps page lists.
Linux: the background portal, through libportal.
"""

import sys
from enum import Enum
from gettext import gettext as _
from typing import TYPE_CHECKING, Callable

from blanket import paths
from blanket.system import IS_WINDOWS

if TYPE_CHECKING:
    from gi.repository import Gtk

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Blanket"


class Result(Enum):
    DONE = 0
    DENIED = 1  # The user or the system refused
    FAILED = 2


def supported() -> bool:
    if IS_WINDOWS:
        # From a checkout there is no stable command to register
        return paths.is_frozen()

    try:
        import gi

        gi.require_version("Xdp", "1.0")
        return True
    except (ImportError, ValueError):
        return False


def is_enabled() -> bool | None:
    """
    Whether autostart is on, as far as the system says

    None when only the saved setting can tell (the portal does not say).
    """
    if not IS_WINDOWS:
        return None

    return windows_command() is not None


def request(
    enabled: bool, parent: "Gtk.Window | None", callback: Callable[[Result], None]
):
    """Turn autostart on or off, callback gets the outcome"""
    if IS_WINDOWS:
        try:
            set_windows_command(launch_command() if enabled else None)
            callback(Result.DONE)
        except OSError as error:
            print(f"Error: could not change autostart: {error}")
            callback(Result.FAILED)
        return

    _request_portal(enabled, parent, callback)


"""
Windows
"""


def launch_command() -> str:
    return f'"{sys.executable}" --hidden'


def windows_command() -> str | None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _type = winreg.QueryValueEx(key, RUN_VALUE)
            return str(value)
    except FileNotFoundError:
        return None


def set_windows_command(command: str | None):
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if command is not None:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, command)
            return

        try:
            winreg.DeleteValue(key, RUN_VALUE)
        except FileNotFoundError:
            pass


"""
Linux
"""


def _request_portal(
    enabled: bool, parent: "Gtk.Window | None", callback: Callable[[Result], None]
):
    from gi.repository import Xdp

    def finish(portal: Xdp.Portal, result) -> None:
        try:
            success = portal.request_background_finish(result)
            callback(Result.DONE if success or not enabled else Result.DENIED)
        except Exception:
            callback(Result.FAILED)

    flags = Xdp.BackgroundFlags.AUTOSTART if enabled else Xdp.BackgroundFlags(0)
    portal = Xdp.Portal()
    # The parent is left out: XdpGtk4.parent_new_gtk() trips a
    # g_variant_unref assertion
    portal.request_background(
        None,
        _("Autostart Blanket in background."),
        ["blanket", "--hidden"],
        flags,
        None,
        finish,
    )
