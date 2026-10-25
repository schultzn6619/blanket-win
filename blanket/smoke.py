# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Self test of a built Blanket, run by CI against the Windows executable

Enabled with BLANKET_SMOKE_TEST=<report.json>. Once the window is up, it
checks the bundled GStreamer plugins, plays a few sounds through the real
pipeline, opens the dialogs, writes what it found to the report and quits.
A bundle missing a plugin or a resource fails here instead of on a user's
machine.

BLANKET_SMOKE_TEST_HOLD pauses that many seconds at two points, so CI can
take screenshots: <report.json>.main is created while the main window plays,
<report.json>.dialogs once the dialogs are open.
"""

import json
import math
import os
import struct
import tempfile
import traceback
import wave
from gettext import gettext as _
from pathlib import Path

from gi.repository import Gio, GLib, Gst, Gtk

from blanket.main_player import MainPlayer
from blanket.sound import Sound
from blanket.system import IS_WINDOWS

# Needed for the bundled sounds and noises to play at all
REQUIRED_ELEMENTS = [
    "audiomixer",
    "audioconvert",
    "audioresample",
    "volume",
    "capsfilter",
    "autoaudiosink",
    "uridecodebin",
    "audiotestsrc",
    "typefind",
    "oggdemux",
    "vorbisdec",
]
# Needed for custom sounds in the formats the file dialog offers, any of each
CUSTOM_FORMAT_ELEMENTS = {
    "flac": ["flacdec"],
    "wav": ["wavparse"],
    "mp3": ["mpg123audiodec", "mfmp3dec", "avdec_mp3"],
    "aac": ["mfaacdec", "avdec_aac", "faad", "fdkaacdec"],
    "opus": ["opusdec"],
}
SOUNDS_TO_PLAY = ["rain", "waves", "white-noise"]
PLAY_SECONDS = 4
CUSTOM_SOUND = "smoke-test-tone"

# A translatable string as GTK sees it in the UI templates
TRANSLATION_PROBE = """
<interface>
  <object class="GtkLabel" id="label">
    <property name="label" translatable="yes">Preferences</property>
  </object>
</interface>
"""


def enabled() -> bool:
    return bool(os.environ.get("BLANKET_SMOKE_TEST"))


class SmokeTest:
    def __init__(self, app):
        self.app = app
        self.report: dict = {"ok": False, "checks": {}, "errors": []}
        self.report_path = os.environ["BLANKET_SMOKE_TEST"]
        self.hold = int(os.environ.get("BLANKET_SMOKE_TEST_HOLD", "0"))

    def start(self):
        # Give the window time to map and the pipeline to settle
        GLib.timeout_add_seconds(2, self._step_play)

    def _check(self, name: str, passed: bool, detail=None):
        self.report["checks"][name] = {"passed": bool(passed), "detail": detail}

    def _guard(self, step):
        try:
            step()
        except Exception:
            self.report["errors"].append(traceback.format_exc())
            self._finish()
            return False
        return True

    def _step_play(self):
        def step():
            self._check_elements()
            self._check_window()
            self._record_translations()
            self._add_custom_sound()

            player = MainPlayer.get()
            for sound in player:
                if isinstance(sound, Sound) and sound.name in SOUNDS_TO_PLAY:
                    sound.playing = True
                    sound.saved_volume = 0.5
            player.playing = True

            GLib.timeout_add_seconds(PLAY_SECONDS, self._step_check_playback)

        self._guard(step)
        return GLib.SOURCE_REMOVE

    def _step_check_playback(self):
        def step():
            player = MainPlayer.get()
            _ret, state, _pending = player.pipeline.get_state(Gst.SECOND)
            self._check(
                "pipeline-playing",
                state == Gst.State.PLAYING,
                Gst.Element.state_get_name(state),
            )

            running = player.mixer.get_current_running_time()
            self._check(
                "mixer-advancing",
                running != Gst.CLOCK_TIME_NONE and running > Gst.SECOND,
                running,
            )

            failed = [s.name for s in player if isinstance(s, Sound) and s.failed]
            self._check("no-failed-sounds", not failed, failed)

            custom, _index = player.get_by_name(CUSTOM_SOUND)
            self._check(
                "custom-sound-playing",
                isinstance(custom, Sound) and custom._player is not None,
                None if custom is None else custom.uri,
            )

            if IS_WINDOWS:
                tray = self.app.tray
                self._check("tray-icon", tray is not None and bool(tray._hwnd), None)

            self._mark("main")
            GLib.timeout_add_seconds(max(self.hold, 1), self._step_dialogs)

        self._guard(step)
        return GLib.SOURCE_REMOVE

    def _step_dialogs(self):
        def step():
            # Dialogs build from the bundled UI files
            for action in ("about", "preferences"):
                self.app.activate_action(action, None)
            self._check("dialogs-opened", True)

            self._mark("dialogs")
            GLib.timeout_add_seconds(max(self.hold, 1), self._step_finish)

        self._guard(step)
        return GLib.SOURCE_REMOVE

    def _mark(self, stage: str):
        with open(f"{self.report_path}.{stage}", "w", encoding="utf-8"):
            pass

    def _step_finish(self):
        self._finish()
        return GLib.SOURCE_REMOVE

    def _check_elements(self):
        missing = [e for e in REQUIRED_ELEMENTS if Gst.ElementFactory.find(e) is None]
        self._check("gstreamer-elements", not missing, {"missing": missing})

        source = Gst.Element.make_from_uri(
            Gst.URIType.SRC, "resource:///com/rafaelmardojai/Blanket/sounds/rain.ogg"
        )
        self._check("resource-uri-source", source is not None)

        decoders = {}
        for name, elements in CUSTOM_FORMAT_ELEMENTS.items():
            found = [e for e in elements if Gst.ElementFactory.find(e) is not None]
            decoders[name] = found[0] if found else None
        self._check("custom-format-decoders", all(decoders.values()), decoders)

        sink = Gst.ElementFactory.make("autoaudiosink", None)
        self.report["audio-sinks"] = [
            f.get_name()
            for f in Gst.Registry.get().get_feature_list(Gst.ElementFactory)
            if "Sink/Audio" in (f.get_metadata("klass") or "")
        ]
        self._check("autoaudiosink", sink is not None)

    def _record_translations(self):
        """What a couple of strings translate to, CI compares per language"""
        builder = Gtk.Builder.new_from_string(TRANSLATION_PROBE, -1)
        label: Gtk.Label = builder.get_object("label")  # type: ignore
        self.report["translations"] = {
            "language": os.environ.get("LANGUAGE"),
            "python": _("Rain"),
            "gtk": label.get_label(),
        }

    def _add_custom_sound(self):
        """
        Play a generated WAV file the way a custom sound is played

        It goes through a file:// URI like the ones the file dialog gives,
        which on Windows carry a drive letter.
        """
        path = Path(tempfile.gettempdir()) / f"{CUSTOM_SOUND}.wav"
        rate = 22050  # Not the mixer rate, so it is resampled too
        with wave.open(str(path), "wb") as tone:
            tone.setnchannels(1)
            tone.setsampwidth(2)
            tone.setframerate(rate)
            tone.writeframes(
                b"".join(
                    struct.pack("<h", int(4000 * math.sin(2 * math.pi * 440 * i / rate)))
                    for i in range(rate * 2)
                )
            )

        uri = Gio.File.new_for_path(str(path)).get_uri()
        resolved = Gio.File.new_for_uri(uri).get_path()
        self._check(
            "custom-sound-path",
            resolved is not None and os.path.exists(resolved),
            [uri, resolved],
        )

        sound = Sound(CUSTOM_SOUND, uri=uri, custom=True)
        MainPlayer.get().append(sound)
        sound.playing = True
        sound.saved_volume = 0.3

    def _check_window(self):
        window = self.app.window
        self._check(
            "window-mapped",
            window is not None and window.get_mapped(),
            None if window is None else [window.get_width(), window.get_height()],
        )
        self._check(
            "sounds-loaded",
            MainPlayer.get().get_n_items() >= 14,
            MainPlayer.get().get_n_items(),
        )

    def _finish(self):
        checks = self.report["checks"]
        self.report["ok"] = (
            not self.report["errors"]
            and bool(checks)
            and all(c["passed"] for c in checks.values())
        )
        with open(self.report_path, "w", encoding="utf-8") as report:
            json.dump(self.report, report, indent=2, default=str)

        print(f"Smoke test {'passed' if self.report['ok'] else 'FAILED'}")
        self.app.quit()
