# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from gettext import gettext as _

import gi

try:
    gi.require_version("Adw", "1")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Gst", "1.0")
    gi.require_version("GstAudio", "1.0")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Adw, Gio, GLib, Gst, Gtk

    # Init GStreamer
    Gst.init(None)
except (ImportError, ValueError) as exc:
    print("Error: Dependencies not met.", exc)
    exit()

from blanket.define import (
    APP_ID,
    ARTISTS,
    AUTHORS,
    RES_PATH,
    SOUND_ARTISTS,
    SOUND_EDITORS,
    VERSION,
)
from blanket import paths
from blanket.main_player import MainPlayer
from blanket.preferences import PreferencesDialog
from blanket.settings import Settings
from blanket.sound import Sound
from blanket.system import IS_WINDOWS
from blanket.system.power import PowerSaverMonitor
from blanket.widgets import PresetDialog
from blanket.widgets.sound_rename_dialog import SoundRenameDialog
from blanket.window import BlanketWindow

PLAYPAUSE_ACCELS = ["<Ctl>m"]


class Application(Adw.Application):
    def __init__(self):
        flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        if IS_WINDOWS:
            # Uniqueness needs a D-Bus session bus, Windows has none.
            # blanket.system.windows.instance takes care of it instead.
            flags |= Gio.ApplicationFlags.NON_UNIQUE

        super().__init__(
            application_id=APP_ID,
            resource_base_path=RES_PATH,
            flags=flags,
        )
        GLib.set_application_name(_("Blanket"))
        if not IS_WINDOWS:
            GLib.setenv(
                "PULSE_PROP_application.icon_name",
                "com.rafaelmardojai.Blanket-symbolic",
                True,
            )
        # Connect app shutdown signal
        self.connect("shutdown", self._on_shutdown)

        # Track power status
        self.power_monitor = PowerSaverMonitor()
        self.power_monitor.connect(
            "notify::power-saver-enabled", self._on_notify_power_saver_enabled
        )

        # Add --hidden command line option
        self.add_main_option(
            "hidden",
            ord("h"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Start window hidden",
            None,
        )
        # App window
        self.window: BlanketWindow | None = None
        self.window_hidden = False
        # Media controls (MPRIS) on Linux, notification area icon on Windows
        self.mpris = None
        self.tray = None
        # App version
        self.version = VERSION

    def do_startup(self):
        # Startup application
        Adw.Application.do_startup(self)

        style_manager = Adw.StyleManager.get_default()
        # if the system doesn't support libadwaita color schemes,
        # fall back to our setting
        if (
            Settings.get().dark_mode
            and not style_manager.props.system_supports_color_schemes
        ):
            style_manager.props.color_scheme = Adw.ColorScheme.FORCE_DARK

        if IS_WINDOWS:
            self._start_tray()
        else:
            self._start_mpris()

        self.setup_actions()

    def _start_mpris(self):
        try:
            from blanket.mpris import MPRIS

            self.mpris = MPRIS(self)
        except GLib.Error as error:
            print(f"Error: could not start MPRIS: {error.message}")

    def _start_tray(self):
        from blanket.system.windows.tray import TrayIcon

        icon = paths.data_dir() / "blanket.ico"
        self.tray = TrayIcon(
            str(icon), _("Blanket"), self._on_tray_activate, self._tray_menu
        )
        self.tray.start()

    def setup_actions(self):
        # Quit application
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        # Show about dialog
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        # Show preferences dialog
        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.on_preferences)
        self.add_action(action)

        # Toggle background-playback setting
        action = Gio.SimpleAction.new_stateful(
            "background-playback", None, Settings.get().get_value("background-playback")
        )
        action.connect("change-state", self.on_background)
        self.add_action(action)

        # Toggle playback
        action = Gio.SimpleAction.new("playpause", None)
        action.connect("activate", self.on_playpause)
        self.add_action(action)

        action = Gio.SimpleAction.new("play", None)
        action.connect("activate", self.on_play)
        self.add_action(action)

        # Create new preset from active
        action = Gio.SimpleAction.new("add-preset", None)
        action.connect("activate", self.on_add_preset)
        self.add_action(action)

        # Reset active preset volumes
        action = Gio.SimpleAction.new("reset-volumes", None)
        action.connect("activate", self.on_reset_volumes)
        self.add_action(action)

        # Add sound file
        action = Gio.SimpleAction.new("open", None)
        action.connect("activate", self.on_open)
        self.add_action(action)

        # Remove sound file
        action = Gio.SimpleAction.new("remove-sound", GLib.VariantType("u"))
        action.connect("activate", self.on_remove_sound)
        self.add_action(action)

        # Rename sound file
        action = Gio.SimpleAction.new("rename-sound", GLib.VariantType("u"))
        action.connect("activate", self.on_rename_sound)
        self.add_action(action)

        # Setup accelerator
        self.set_accels_for_action("app.quit", ["<Ctl>q"])
        self.set_accels_for_action("app.preferences", ["<Ctl>comma"])
        self.set_accels_for_action("app.playpause", PLAYPAUSE_ACCELS + ["space"])
        self.set_accels_for_action("app.open", ["<Ctl>o"])
        self.set_accels_for_action("win.close", ["<Ctl>w"])
        self.set_accels_for_action("win.hide-inactive", ["<Ctl>h"])

    def do_activate(self):
        if self.window is None:
            self.window = BlanketWindow(application=self)

            # Connect window close-request signal to _on_window_close_request
            self.window.connect("close-request", self._on_window_close_request)

            # Load saved props, only once: activating again (from another
            # launch or the tray) must not undo what happened meanwhile
            MainPlayer.get().volume = Settings.get().volume
            MainPlayer.get().playing = (
                Settings.get().playing and not Settings.get().start_paused
            )

            from blanket import smoke

            if smoke.enabled():
                smoke.SmokeTest(self).start()

        self.window.props.hide_on_close = Settings.get().background

        if self.window_hidden:
            self.window.hide()
            self.window_hidden = False
        else:
            self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if "hidden" in options and self.window is None:
            self.window_hidden = True

        self.activate()
        return 0

    def on_open(self, _action, _param):
        if self.window:
            self.window.open_audio()

    def on_playpause(self, _action=None, _param=None):
        MainPlayer.get().playing = not MainPlayer.get().playing
        if self.window:
            self.window.hide_power_toast()

    def on_play(self, _action=None, _param=None):
        MainPlayer.get().playing = True
        if self.window:
            self.window.hide_power_toast()

    def on_pause(self, _action=None, _param=None):
        MainPlayer.get().playing = False
        if self.window:
            self.window.hide_power_toast()

    def on_next(self, _action=None, _param=None):
        MainPlayer.get().next_preset()

    def on_prev(self, _action=None, _param=None):
        MainPlayer.get().prev_preset()

    def on_reset_volumes(self, _action, _param):
        MainPlayer.get().reset_volumes()

    def on_add_preset(self, _action, _param):
        dialog = PresetDialog()
        dialog.present(self.window)

    def on_remove_sound(self, _action, index_variant: GLib.Variant):
        index = index_variant.get_uint32()
        sound = MainPlayer.get().get_by_index(index)

        if isinstance(sound, Sound) and sound and index:
            sound.remove()
            MainPlayer.get().remove(index)

    def on_rename_sound(self, _action, index_variant: GLib.Variant):
        # Open edit dialog
        index = index_variant.get_uint32()
        sound = MainPlayer.get().get_by_index(index)
        if isinstance(sound, Sound) and sound and index:
            dialog = SoundRenameDialog(sound, index)
            dialog.present(self.window)

    def on_background(self, action, value):
        action.set_state(value)
        Settings.get().background = value
        if self.window:
            self.window.props.hide_on_close = value

    def on_preferences(self, _action, _param):
        if self.window:
            prefs = PreferencesDialog(self.window)
            prefs.present(self.window)

    def on_about(self, _action, _param):
        builder = Gtk.Builder.new_from_resource(f"{RES_PATH}/about.ui")
        about: Adw.AboutDialog = builder.get_object("about")  # type: ignore

        artists = self.__get_credits_list(ARTISTS)
        sound_artists = self.__get_credits_list(SOUND_ARTISTS)
        sound_editors = self.__get_credits_list(SOUND_EDITORS)

        about.set_version(self.version)
        about.set_application_icon(APP_ID)
        about.set_developers(AUTHORS)
        about.set_designers(artists)
        about.add_link(_("Source Code"), "https://github.com/rafaelmardojai/blanket")
        about.add_credit_section(_("Sounds by"), sound_artists)
        about.add_credit_section(_("Sounds edited by"), sound_editors)

        about.present(self.window)

    def set_space_accel(self, _action):
        self.set_accels_for_action("app.playpause", PLAYPAUSE_ACCELS + ["space"])

    def unset_space_accel(self, _action):
        self.set_accels_for_action("app.playpause", PLAYPAUSE_ACCELS)

    def on_quit(self, _action, _param):
        self.quit()

    def _on_notify_power_saver_enabled(self, obj, pspec):
        if self.power_monitor.power_saver_enabled and MainPlayer.get().playing:
            # Pause playback if the system enters power saver mode, as audio
            # playback uses quite a lot of power. Don’t re-enable it when
            # exiting power saver mode, as that would be jarring for the user.
            MainPlayer.get().playing = False
            if self.window:
                self.window.show_power_toast()

    def _save_settings(self):
        # Save mainplayer volume
        Settings.get().volume = MainPlayer.get().volume
        # Save mainplayer playing state
        Settings.get().playing = MainPlayer.get().playing
        # Save presets settings
        Settings.get().save_presets()

    def _on_window_close_request(self, window):
        if Settings.get().background:
            self._save_settings()  # Save settings
            window.hide()
        else:
            self.quit_from_window = True
            window.save_window_state()
            self.quit()

    def _on_shutdown(self, _app):
        self._save_settings()
        MainPlayer.get().stop()
        if self.tray is not None:
            self.tray.stop()

    def _on_tray_activate(self):
        self.activate()

    def _tray_menu(self):
        from blanket.system.windows.tray import TrayMenuItem

        playing = MainPlayer.get().playing
        return [
            TrayMenuItem(_("Show Blanket"), self.activate, default=True),
            TrayMenuItem(_("Pause") if playing else _("Play"), self.on_playpause),
            TrayMenuItem(""),
            TrayMenuItem(_("Quit"), self.quit),
        ]

    def __get_credits_list(self, dict_):
        credits_list = []
        for k, vs in dict_.items():
            s = k + ": " + ", ".join(vs)
            credits_list.append(s)
        return credits_list


def main() -> int:
    app = Application()
    return app.run(sys.argv)
