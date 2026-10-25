# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Tests for the Windows integration, against the real Win32 API

Run with: python -m unittest discover -s tests -v
"""

import ctypes
import sys
import time
import unittest
from unittest import mock

from blanket import paths

if sys.platform != "win32":
    raise unittest.SkipTest("Windows only")

from gi.repository import GLib  # noqa: E402

from blanket.system import autostart  # noqa: E402
from blanket.system.windows import instance, win32  # noqa: E402
from blanket.system.windows.tray import (  # noqa: E402
    WINDOW_CLASS,
    WM_ACTIVATE_INSTANCE,
    TrayIcon,
    TrayMenuItem,
)


def iterate_main_loop(until, timeout=5.0):
    context = GLib.MainContext.default()
    deadline = time.monotonic() + timeout
    while not until() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.01)
    return until()


class Win32Tests(unittest.TestCase):
    def test_ui_language(self):
        language = win32.user_ui_language()
        self.assertIsNotNone(language)
        self.assertNotIn("-", language)

    def test_battery_saver_is_bool(self):
        self.assertIsInstance(win32.battery_saver_enabled(), bool)

    def test_keep_system_awake(self):
        self.assertTrue(win32.keep_system_awake(True))
        self.assertTrue(win32.keep_system_awake(False))

    def test_app_user_model_id(self):
        win32.set_app_user_model_id("com.rafaelmardojai.Blanket.Tests")


class AutostartTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(autostart, "RUN_VALUE", "BlanketTests")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(autostart.set_windows_command, None)

    def test_roundtrip(self):
        self.assertIsNone(autostart.windows_command())

        autostart.set_windows_command(r'"C:\Blanket\Blanket.exe" --hidden')
        self.assertEqual(
            autostart.windows_command(), r'"C:\Blanket\Blanket.exe" --hidden'
        )
        self.assertTrue(autostart.is_enabled())

        autostart.set_windows_command(None)
        self.assertIsNone(autostart.windows_command())
        self.assertFalse(autostart.is_enabled())

        # Removing twice is fine
        autostart.set_windows_command(None)

    def test_request_reports_result(self):
        results = []
        with mock.patch.object(autostart, "launch_command", return_value="x"):
            autostart.request(True, None, results.append)  # type: ignore
            self.assertEqual(autostart.windows_command(), "x")
            autostart.request(False, None, results.append)  # type: ignore
        self.assertEqual(results, [autostart.Result.DONE] * 2)
        self.assertIsNone(autostart.windows_command())

    def test_launch_command_quotes_executable(self):
        command = autostart.launch_command()
        self.assertTrue(command.startswith(f'"{sys.executable}"'))
        self.assertTrue(command.endswith("--hidden"))


class InstanceTests(unittest.TestCase):
    def test_second_acquire_sees_first(self):
        with mock.patch.object(instance, "APP_ID", "com.rafaelmardojai.Blanket.Tests"):
            first = instance._mutex
            try:
                self.assertTrue(instance.acquire())
                held = instance._mutex
                # Opening the same name again reports it already exists
                self.assertFalse(instance.acquire())
                win32.CloseHandle(instance._mutex)
                win32.CloseHandle(held)
            finally:
                instance._mutex = first

    def test_no_running_instance(self):
        self.assertIsNone(win32.FindWindowW(WINDOW_CLASS, None))
        self.assertFalse(instance.activate_running_instance(timeout=0.3))


class TrayTests(unittest.TestCase):
    def test_lifecycle_and_activation(self):
        icon = paths.data_dir() / "blanket.ico"
        activated = []
        tray = TrayIcon(
            str(icon),
            "Blanket tests",
            lambda: activated.append(True),
            lambda: [TrayMenuItem("Quit", lambda: None)],
            lambda: None,
        )
        tray.start()
        try:
            self.assertTrue(tray._hwnd, "tray window was not created")
            self.assertTrue(tray._hicon, "tray icon was not loaded")

            # What a second instance does
            self.assertTrue(instance.activate_running_instance(timeout=2))
            self.assertTrue(iterate_main_loop(lambda: bool(activated)))

            tray.set_tooltip("Blanket tests, again")
        finally:
            tray.stop()

        self.assertIsNone(tray._hwnd)
        self.assertFalse(win32.FindWindowW(WINDOW_CLASS, None))

    def test_activate_message_value(self):
        self.assertEqual(WM_ACTIVATE_INSTANCE, 0x8002)
        self.assertEqual(ctypes.sizeof(win32.NOTIFYICONDATAW), 976)


if __name__ == "__main__":
    unittest.main()
