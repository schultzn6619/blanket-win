# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Keeping the computer awake while playing, and noticing power saving mode
"""

from gi.repository import Gio, GLib, GObject, Gtk

from blanket.system import IS_WINDOWS

# Windows does not notify about battery saver, so it is checked this often
BATTERY_SAVER_POLL_SECONDS = 15


class SuspendInhibitor:
    """Prevents the system from suspending while held"""

    def __init__(self):
        self._cookie = 0
        self._held = False

    @property
    def held(self) -> bool:
        return self._held

    def inhibit(self, reason: str):
        if self._held:
            return

        if IS_WINDOWS:
            from blanket.system.windows import win32

            self._held = win32.keep_system_awake(True)
            return

        app: Gtk.Application | None = Gtk.Application.get_default()  # type: ignore
        if app is None:
            return

        self._cookie = app.inhibit(None, Gtk.ApplicationInhibitFlags.SUSPEND, reason)
        self._held = self._cookie != 0

    def uninhibit(self):
        if not self._held:
            return

        if IS_WINDOWS:
            from blanket.system.windows import win32

            win32.keep_system_awake(False)
        else:
            app: Gtk.Application | None = Gtk.Application.get_default()  # type: ignore
            if app is not None:
                app.uninhibit(self._cookie)
            self._cookie = 0

        self._held = False


class PowerSaverMonitor(GObject.Object):
    """
    Tells whether the system is in power saving mode

    That is the power profile on Linux, battery saver on Windows.
    """

    __gtype_name__ = "BlanketPowerSaverMonitor"

    power_saver_enabled: bool = GObject.Property(type=bool, default=False)  # type: ignore

    def __init__(self):
        super().__init__()

        if IS_WINDOWS:
            self._poll()
            GLib.timeout_add_seconds(BATTERY_SAVER_POLL_SECONDS, self._poll)
            return

        # There may be no implementation, the property then stays false
        self._monitor = Gio.PowerProfileMonitor.dup_default()
        if self._monitor is not None:
            self._monitor.bind_property(
                "power-saver-enabled",
                self,
                "power-saver-enabled",
                GObject.BindingFlags.SYNC_CREATE,
            )

    def _poll(self):
        from blanket.system.windows import win32

        enabled = win32.battery_saver_enabled()
        if enabled != self.power_saver_enabled:
            self.power_saver_enabled = enabled

        return GLib.SOURCE_CONTINUE
