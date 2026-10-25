# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gettext import gettext as _
from typing import TYPE_CHECKING

from gi.repository import Adw, Gio, Gtk

from blanket.define import RES_PATH
from blanket.settings import Settings
from blanket.system import autostart

if TYPE_CHECKING:
    from blanket.window import BlanketWindow


@Gtk.Template(resource_path=f"{RES_PATH}/preferences.ui")
class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"

    dark_group: Adw.PreferencesGroup = Gtk.Template.Child()
    dark: Adw.SwitchRow = Gtk.Template.Child()
    autostart: Adw.SwitchRow = Gtk.Template.Child()
    start_paused: Adw.SwitchRow = Gtk.Template.Child()
    inhibition: Adw.SwitchRow = Gtk.Template.Child()

    def __init__(self, window: "BlanketWindow", **kwargs):
        super().__init__(**kwargs)

        self.window = window

        # Show dark theme preference if system does not support color schemes
        self.dark_group.props.visible = (
            not Adw.StyleManager.get_default().props.system_supports_color_schemes
        )
        # Dark theme
        Settings.get().bind(
            "dark-mode", self.dark, "active", Gio.SettingsBindFlags.DEFAULT
        )
        self.dark.connect("notify::active", self._toggle_dark)

        # Autostart
        self.autostart.props.visible = autostart.supported()
        if (enabled := autostart.is_enabled()) is not None:
            # The system knows better, it may have been changed outside Blanket
            Settings.get().autostart = enabled
        self.autostart_saved = Settings.get().autostart
        self.autostart.props.active = self.autostart_saved
        self.autostart.connect("notify::active", self._toggle_autostart)

        # Start paused
        Settings.get().bind(
            "start-paused", self.start_paused, "active", Gio.SettingsBindFlags.DEFAULT
        )

        # Inhibition
        Settings.get().bind(
            "inhibit-suspension",
            self.inhibition,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

    def _toggle_dark(self, switch: Adw.SwitchRow, _pspec):
        style_manager = Adw.StyleManager.get_default()
        if switch.props.active:
            style_manager.props.color_scheme = Adw.ColorScheme.FORCE_DARK
        else:
            style_manager.props.color_scheme = Adw.ColorScheme.PREFER_LIGHT

    def _toggle_autostart(self, switch: Adw.SwitchRow, _pspec):
        self._request_autostart(switch.props.active)

    def _request_autostart(self, active: bool):
        autostart.request(active, self.window, self._on_autostart_result)

    def _on_autostart_result(self, result: autostart.Result):
        active = self.autostart.get_active()

        if result is autostart.Result.DONE:
            Settings.get().autostart = active
            self.autostart_saved = active
            return

        if result is autostart.Result.DENIED:
            # Only the Linux portal can refuse
            error_dialog = Adw.AlertDialog.new(
                _("Authorization failed"),
                _(
                    "Make sure Blanket has permission to run in the background in Settings → Applications → Blanket and try again."
                ),
            )
            error_dialog.add_response("ok", _("Ok"))
            error_dialog.present(self.window)
        else:
            error_toast = Adw.Toast(title=_("The autostart request failed."))
            self.add_toast(error_toast)

        # Revert the switch without asking again
        self.autostart.handler_block_by_func(self._toggle_autostart)
        self.autostart.props.active = self.autostart_saved
        self.autostart.handler_unblock_by_func(self._toggle_autostart)
