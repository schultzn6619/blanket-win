# Copyright 2026 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Notification area (system tray) icon

GTK 4 has no tray support, and on Windows a hidden window is otherwise
unreachable: there is no shell to bring it back like on GNOME. The icon
owns a hidden Win32 window running its own message loop on a separate
thread; whatever the user picks is handed to the GTK main loop.

The hidden window also lets a second Blanket instance find this one and ask
it to show itself, see blanket.system.windows.instance.
"""

import ctypes
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable

from gi.repository import GLib

from blanket.system.windows import win32

WINDOW_CLASS = "BlanketTrayWindow"

# Sent by the icon on mouse events
WM_TRAY_CALLBACK = win32.WM_APP + 1
# Sent by a second instance, asks this one to show its window
WM_ACTIVATE_INSTANCE = win32.WM_APP + 2

TRAY_ICON_ID = 1


@dataclass
class TrayMenuItem:
    label: str
    callback: Callable[[], None] | None = None  # None makes a separator
    default: bool = False  # Shown in bold, what a left click does
    enabled: bool = True


class TrayIcon:
    def __init__(
        self,
        icon_path: str,
        tooltip: str,
        on_activate: Callable[[], None],
        build_menu: Callable[[], list[TrayMenuItem]],
    ):
        """
        on_activate is called when the icon is clicked or another instance
        asks to be shown. build_menu returns the context menu entries. Both
        run on the GTK main loop.
        """
        self._icon_path = icon_path
        self._tooltip = tooltip
        self._on_activate = on_activate
        self._build_menu = build_menu

        # The menu is built on the GTK thread and read by the tray thread
        self._menu_items: list[TrayMenuItem] = []
        self._menu_ready = threading.Event()

        self._hwnd = None
        self._hicon = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._taskbar_created = 0

        # Keep the callback alive as long as the window class is registered
        self._wndproc = win32.WNDPROC(self._window_proc)

    def start(self):
        self._thread = threading.Thread(
            target=self._run, name="blanket-tray", daemon=True
        )
        self._thread.start()
        self._started.wait(timeout=5)

    def stop(self):
        if self._hwnd:
            win32.PostMessageW(self._hwnd, win32.WM_CLOSE, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def set_tooltip(self, tooltip: str):
        self._tooltip = tooltip
        if self._hwnd:
            data = self._notify_data(win32.NIF_TIP | win32.NIF_SHOWTIP)
            win32.Shell_NotifyIconW(win32.NIM_MODIFY, ctypes.byref(data))

    """
    Tray thread
    """

    def _run(self):
        try:
            self._create_window()
            self._add_icon()
        except OSError as error:
            print(f"Error: could not create the tray icon: {error}")
            return
        finally:
            self._started.set()

        msg = wintypes.MSG()
        while win32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            win32.TranslateMessage(ctypes.byref(msg))
            win32.DispatchMessageW(ctypes.byref(msg))

        self._cleanup()

    def _create_window(self):
        hinstance = win32.GetModuleHandleW(None)

        wndclass = win32.WNDCLASSEXW()
        wndclass.cbSize = ctypes.sizeof(win32.WNDCLASSEXW)
        wndclass.lpfnWndProc = self._wndproc
        wndclass.hInstance = hinstance
        wndclass.lpszClassName = WINDOW_CLASS

        if not win32.RegisterClassExW(ctypes.byref(wndclass)):
            raise ctypes.WinError(ctypes.get_last_error())

        # A plain hidden top-level window: message-only windows cannot take
        # the foreground, which the context menu needs to close properly
        self._hwnd = win32.CreateWindowExW(
            0,
            WINDOW_CLASS,
            "Blanket",
            win32.WS_OVERLAPPED,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )
        if not self._hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        # Explorer broadcasts this when it restarts, the icon has to be re-added
        self._taskbar_created = win32.RegisterWindowMessageW("TaskbarCreated")

    def _load_icon(self):
        if self._hicon:
            return self._hicon

        self._hicon = win32.LoadImageW(
            None,
            self._icon_path,
            win32.IMAGE_ICON,
            win32.GetSystemMetrics(win32.SM_CXSMICON),
            win32.GetSystemMetrics(win32.SM_CYSMICON),
            win32.LR_LOADFROMFILE,
        )
        if not self._hicon:
            print(f"Error: could not load the tray icon from {self._icon_path}")
            self._hicon = win32.LoadIconW(None, win32.IDI_APPLICATION)

        return self._hicon

    def _notify_data(self, flags: int) -> win32.NOTIFYICONDATAW:
        data = win32.NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(win32.NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = TRAY_ICON_ID
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAY_CALLBACK
        data.hIcon = self._load_icon()
        data.szTip = self._tooltip[:127]
        return data

    def _add_icon(self):
        data = self._notify_data(
            win32.NIF_MESSAGE | win32.NIF_ICON | win32.NIF_TIP | win32.NIF_SHOWTIP
        )
        if not win32.Shell_NotifyIconW(win32.NIM_ADD, ctypes.byref(data)):
            # Explorer may not be up yet at logon, TaskbarCreated will retry
            print("Warning: the tray icon could not be added yet")

    def _cleanup(self):
        if self._hicon:
            win32.DestroyIcon(self._hicon)
            self._hicon = None
        win32.UnregisterClassW(WINDOW_CLASS, win32.GetModuleHandleW(None))

    def _window_proc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAY_CALLBACK:
                event = lparam & 0xFFFF
                if event == win32.WM_LBUTTONUP:
                    GLib.idle_add(self._activate)
                elif event in (win32.WM_RBUTTONUP, win32.WM_CONTEXTMENU):
                    self._show_menu(hwnd)
                return 0

            if msg == WM_ACTIVATE_INSTANCE:
                GLib.idle_add(self._activate)
                return 0

            if msg == self._taskbar_created and self._taskbar_created:
                self._add_icon()
                return 0

            if msg == win32.WM_CLOSE:
                data = self._notify_data(0)
                win32.Shell_NotifyIconW(win32.NIM_DELETE, ctypes.byref(data))
                win32.DestroyWindow(hwnd)
                return 0

            if msg == win32.WM_DESTROY:
                self._hwnd = None
                win32.PostQuitMessage(0)
                return 0
        except Exception as error:  # Never let an exception cross into Win32
            print(f"Error in the tray icon: {error}")

        return win32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self, hwnd):
        # The entries depend on app state, which lives on the GTK thread
        self._menu_ready.clear()
        GLib.idle_add(self._prepare_menu)
        if not self._menu_ready.wait(timeout=1):
            return

        items = self._menu_items
        menu = win32.CreatePopupMenu()
        try:
            for command, item in enumerate(items, start=1):
                if item.callback is None:
                    win32.AppendMenuW(menu, win32.MF_SEPARATOR, 0, None)
                    continue

                flags = win32.MF_STRING
                if not item.enabled:
                    flags |= win32.MF_GRAYED
                win32.AppendMenuW(menu, flags, command, item.label)
                if item.default:
                    win32.SetMenuDefaultItem(menu, command, 0)

            point = wintypes.POINT()
            win32.GetCursorPos(ctypes.byref(point))

            # Without this the menu would not close when clicking elsewhere
            win32.SetForegroundWindow(hwnd)
            command = win32.TrackPopupMenu(
                menu,
                win32.TPM_RIGHTBUTTON
                | win32.TPM_RETURNCMD
                | win32.TPM_NONOTIFY
                | win32.TPM_BOTTOMALIGN,
                point.x,
                point.y,
                0,
                hwnd,
                None,
            )
            win32.PostMessageW(hwnd, win32.WM_NULL, 0, 0)
        finally:
            win32.DestroyMenu(menu)

        if 0 < command <= len(items):
            callback = items[command - 1].callback
            if callback is not None:
                GLib.idle_add(self._call, callback)

    """
    GTK thread
    """

    def _prepare_menu(self):
        try:
            self._menu_items = self._build_menu()
        finally:
            self._menu_ready.set()
        return GLib.SOURCE_REMOVE

    def _activate(self):
        self._on_activate()
        return GLib.SOURCE_REMOVE

    def _call(self, callback: Callable[[], None]):
        callback()
        return GLib.SOURCE_REMOVE
